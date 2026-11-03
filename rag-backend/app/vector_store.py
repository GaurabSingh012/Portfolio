
import argparse
import hashlib
import os
import uuid
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from qdrant_client import QdrantClient, models

from app.chunking import chunk_text, normalize_text
from app.ingestion import ROOT_DIR, discover_documents, load_documents


# ---------------------------------------------------------
# 1. Configuration
# ---------------------------------------------------------

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"

# Load the backend environment file explicitly.
# override=True ensures the values in this file are used
# even if conflicting environment variables already exist.
load_dotenv(ENV_FILE, override=True)

EMBEDDING_MODEL = os.getenv(
    "GEMINI_EMBEDDING_MODEL", "gemini-embedding-2"
)
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))

QDRANT_URL = os.getenv(
    "QDRANT_URL", "http://127.0.0.1:6333"
)
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

QDRANT_COLLECTION = os.getenv(
    "QDRANT_COLLECTION", "portfolio_knowledge"
)

PIPELINE_VERSION = "chunker-v3"
EMBEDDING_BATCH_SIZE = 8


# ---------------------------------------------------------
# 2. Helper functions
# ---------------------------------------------------------

def document_embedding_input(title: str, text: str) -> str:
    """Add the document title to a chunk before embedding it."""
    return f"title: {title or 'none'} | text: {text}"


def content_hash(text: str) -> str:
    """Create a fingerprint of normalized document text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_point_id(
    source: str,
    fingerprint: str,
    chunk_index: int,
) -> str:
    """Create a stable ID for a particular document chunk."""
    identifier = (
        f"{source}|{fingerprint}|{PIPELINE_VERSION}|{chunk_index}"
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, identifier))


# ---------------------------------------------------------
# 3. Dry run
# ---------------------------------------------------------

def preview_ingestion() -> None:
    """Preview the documents and chunks without API calls or writes."""
    paths = discover_documents()
    documents = load_documents(paths)

    print(f"Repository: {ROOT_DIR}")
    print(f"Discovered {len(paths)} supported file(s).")
    print(f"Successfully loaded {len(documents)} document(s).\n")

    total_chunks = 0

    for document in documents:
        normalized = normalize_text(document.text)
        chunks = chunk_text(normalized)

        print(
            f"- {document.source}: "
            f"{len(normalized)} characters, "
            f"{len(chunks)} chunk(s)"
        )

        total_chunks += len(chunks)

    print(f"\nTotal chunks prepared: {total_chunks}")
    print("Dry run only: no embeddings generated, Qdrant unchanged.")


# ---------------------------------------------------------
# 4. Qdrant collection
# ---------------------------------------------------------

def ensure_collection(client: QdrantClient) -> None:
    """Create the collection if necessary and validate its vector size."""

    if not client.collection_exists(QDRANT_COLLECTION):
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=models.VectorParams(
                size=EMBEDDING_DIMENSIONS,
                distance=models.Distance.COSINE,
            ),
        )

        print(
            f"Created collection '{QDRANT_COLLECTION}' "
            f"with {EMBEDDING_DIMENSIONS}-dimensional vectors."
        )
        return

    info = client.get_collection(QDRANT_COLLECTION)
    vector_config = info.config.params.vectors
    actual_size = getattr(vector_config, "size", None)

    if actual_size is None:
        raise RuntimeError(
            "The existing collection does not appear to use a single "
            "unnamed vector. Use a separate collection for this pipeline."
        )

    if actual_size != EMBEDDING_DIMENSIONS:
        raise RuntimeError(
            f"Collection has {actual_size}-dimensional vectors, but "
            f"the configured size is {EMBEDDING_DIMENSIONS}. "
            "Use a separate collection or rebuild the existing one."
        )

    print(f"Using existing collection '{QDRANT_COLLECTION}'.")


def load_existing_points(
    client: QdrantClient,
) -> dict[str, list]:
    """Retrieve existing points and group them by source file."""

    points_by_source: dict[str, list] = defaultdict(list)
    offset = None

    while True:
        points, next_offset = client.scroll(
            collection_name=QDRANT_COLLECTION,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )

        for point in points:
            source = (point.payload or {}).get("source")

            if source:
                points_by_source[source].append(point)

        if next_offset is None:
            break

        offset = next_offset

    return points_by_source


def delete_point_ids(
    client: QdrantClient,
    point_ids: set[str],
) -> None:
    """Delete specified points; do nothing if the set is empty."""

    if not point_ids:
        return

    client.delete(
        collection_name=QDRANT_COLLECTION,
        points_selector=models.PointIdsList(points=sorted(point_ids)),
        wait=True,
    )


# ---------------------------------------------------------
# 5. Gemini embeddings
# ---------------------------------------------------------

def embed_chunks(
    client: genai.Client,
    title: str,
    chunks: list[str],
) -> list[list[float]]:
    """Generate one 768-dimensional embedding per text chunk."""

    vectors: list[list[float]] = []

    for start in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        batch = chunks[start : start + EMBEDDING_BATCH_SIZE]

        # Keep each chunk in its own Content object so that each
        # chunk receives its own embedding.
        contents = [
            types.Content(
                parts=[
                    types.Part.from_text(
                        text=document_embedding_input(title, chunk)
                    )
                ]
            )
            for chunk in batch
        ]

        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=contents,
            config=types.EmbedContentConfig(
                output_dimensionality=EMBEDDING_DIMENSIONS
            ),
        )

        embeddings = response.embeddings or []

        if len(embeddings) != len(batch):
            raise RuntimeError(
                f"Expected {len(batch)} embeddings, "
                f"but Gemini returned {len(embeddings)}."
            )

        for embedding in embeddings:
            values = embedding.values

            if (
                values is None
                or len(values) != EMBEDDING_DIMENSIONS
            ):
                raise RuntimeError(
                    "Gemini returned an embedding with unexpected dimensions."
                )

            vectors.append([float(value) for value in values])

        print(
            f"Embedded "
            f"{min(start + len(batch), len(chunks))}/{len(chunks)} "
            f"chunks for '{title}'."
        )

    return vectors


# ---------------------------------------------------------
# 6. Synchronize documents with Qdrant
# ---------------------------------------------------------

def sync_to_qdrant() -> None:
    """Index new or changed documents and remove obsolete points."""

    gemini_api_key = os.getenv("GEMINI_API_KEY")

    if not gemini_api_key:
        raise RuntimeError(
            f"GEMINI_API_KEY was not found. Check {ENV_FILE}."
        )

    # Qdrant Cloud requires an API key.
    # Local Qdrant can still be used without one.
    if QDRANT_URL.startswith("https://") and not QDRANT_API_KEY:
        raise RuntimeError(
            f"QDRANT_API_KEY was not found. Check {ENV_FILE}."
        )

    paths = discover_documents()
    documents = load_documents(paths)

    # Track existing paths even if a file temporarily yields no text.
    discovered_sources = {
        path.relative_to(ROOT_DIR).as_posix()
        for path in paths
    }

    # Do not use 'with QdrantClient(...)': this installed version
    # requires explicit .close() calls.
    gemini_client = None
    qdrant_client = None

    try:
        gemini_client = genai.Client(api_key=gemini_api_key)

        # IMPORTANT:
        # Pass the Qdrant API key when connecting to Qdrant Cloud.
        qdrant_client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=15,
        )

        ensure_collection(qdrant_client)
        existing_by_source = load_existing_points(qdrant_client)

        indexed_count = 0
        skipped_count = 0

        for document in documents:
            normalized = normalize_text(document.text)
            chunks = chunk_text(normalized)

            if not chunks:
                print(f"Skipping empty document: {document.source}")
                continue

            fingerprint = content_hash(normalized)
            old_points = existing_by_source.get(document.source, [])
            old_payloads = [
                point.payload or {} for point in old_points
            ]

            old_indices = {
                payload.get("chunk_index")
                for payload in old_payloads
            }

            unchanged = (
                len(old_points) == len(chunks)
                and old_indices == set(range(len(chunks)))
                and all(
                    payload.get("content_hash") == fingerprint
                    and payload.get("pipeline_version") == PIPELINE_VERSION
                    and payload.get("embedding_model") == EMBEDDING_MODEL
                    and payload.get("embedding_dimensions")
                    == EMBEDDING_DIMENSIONS
                    for payload in old_payloads
                )
            )

            if unchanged:
                print(f"Unchanged, skipping: {document.source}")
                skipped_count += 1
                continue

            print(
                f"Indexing {document.source} "
                f"({len(chunks)} chunks)..."
            )

            # Generate all embeddings for this document before touching
            # its existing points.
            vectors = embed_chunks(
                gemini_client,
                document.title,
                chunks,
            )

            new_points = []

            for index, (chunk, vector) in enumerate(
                zip(chunks, vectors, strict=True)
            ):
                new_points.append(
                    models.PointStruct(
                        id=make_point_id(
                            document.source,
                            fingerprint,
                            index,
                        ),
                        vector=vector,
                        payload={
                            "source": document.source,
                            "title": document.title,
                            "text": chunk,
                            "chunk_index": index,
                            "content_hash": fingerprint,
                            "pipeline_version": PIPELINE_VERSION,
                            "embedding_model": EMBEDDING_MODEL,
                            "embedding_dimensions": EMBEDDING_DIMENSIONS,
                        },
                    )
                )

            # Save the new points before removing the previous version.
            qdrant_client.upsert(
                collection_name=QDRANT_COLLECTION,
                points=new_points,
                wait=True,
            )

            new_ids = {str(point.id) for point in new_points}
            old_ids = {str(point.id) for point in old_points}

            delete_point_ids(qdrant_client, old_ids - new_ids)

            indexed_count += len(new_points)
            print(f"Indexed {document.source} successfully.")

        # Delete points for source files that no longer exist.
        deleted_ids = set()

        for source, points in existing_by_source.items():
            if source not in discovered_sources:
                deleted_ids.update(str(point.id) for point in points)
                print(f"Removing deleted source: {source}")

        delete_point_ids(qdrant_client, deleted_ids)

        print("\nQdrant synchronization finished.")
        print(f"New or refreshed chunks: {indexed_count}")
        print(f"Unchanged documents skipped: {skipped_count}")
        print(f"Old points removed for deleted sources: {len(deleted_ids)}")
        print(f"Collection: {QDRANT_COLLECTION}")

    finally:
        # Close whichever clients were successfully created.
        try:
            if qdrant_client is not None:
                qdrant_client.close()
        finally:
            if gemini_client is not None:
                gemini_client.close()


# ---------------------------------------------------------
# 7. Command-line entry point
# ---------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare portfolio knowledge for Qdrant."
    )

    parser.add_argument(
        "--sync",
        action="store_true",
        help="Generate embeddings and write changes to Qdrant.",
    )

    args = parser.parse_args()

    if args.sync:
        sync_to_qdrant()
    else:
        preview_ingestion()


if __name__ == "__main__":
    main()
