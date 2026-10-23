import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from qdrant_client import QdrantClient

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_FILE)

EMBEDDING_MODEL = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "gemini-embedding-2",
)
EMBEDDING_DIMENSIONS = int(
    os.getenv("EMBEDDING_DIMENSIONS", "768")
)
QDRANT_URL = os.getenv(
    "QDRANT_URL",
    "http://127.0.0.1:6333",
)
QDRANT_COLLECTION = os.getenv(
    "QDRANT_COLLECTION",
    "portfolio_knowledge",
)


def embed_query(
    client: genai.Client,
    question: str,
) -> list[float]:
    """Convert the user's question into a retrieval embedding."""

    formatted_question = (
        f"task: search result | query: {question.strip()}"
    )

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=formatted_question,
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIMENSIONS,
        ),
    )

    embeddings = response.embeddings or []

    if len(embeddings) != 1 or embeddings[0].values is None:
        raise RuntimeError(
            "Gemini did not return one valid query embedding."
        )

    vector = [float(value) for value in embeddings[0].values]

    if len(vector) != EMBEDDING_DIMENSIONS:
        raise RuntimeError(
            f"Expected {EMBEDDING_DIMENSIONS} dimensions, "
            f"received {len(vector)}."
        )

    return vector


def retrieve(question: str, limit: int = 5) -> list:
    """Return the most similar text chunks from Qdrant."""

    if not question.strip():
        raise ValueError("The question cannot be empty.")

    if limit < 1:
        raise ValueError("The result limit must be at least 1.")

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            f"GEMINI_API_KEY was not found in {ENV_FILE}."
        )

    gemini_client = None
    qdrant_client = None

    try:
        gemini_client = genai.Client(api_key=api_key)
        qdrant_client = QdrantClient(url=QDRANT_URL)

        if not qdrant_client.collection_exists(QDRANT_COLLECTION):
            raise RuntimeError(
                f"Collection '{QDRANT_COLLECTION}' does not exist. "
                "Run the ingestion synchronization first."
            )

        # First, embed the question.
        query_vector = embed_query(gemini_client, question)

        # Then, search the existing document vectors.
        response = qdrant_client.query_points(
            collection_name=QDRANT_COLLECTION,
            query=query_vector,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        return response.points

    finally:
        try:
            if qdrant_client is not None:
                qdrant_client.close()
        finally:
            if gemini_client is not None:
                gemini_client.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search portfolio knowledge in Qdrant."
    )

    parser.add_argument(
        "question",
        nargs="?",
        default="Which model did Gaurab use for his AMR project?",
        help="Question to search for.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of chunks to retrieve.",
    )

    args = parser.parse_args()

    results = retrieve(args.question, limit=args.limit)

    print(f"\nQuestion: {args.question}")
    print(f"Retrieved {len(results)} chunk(s).\n")

    for rank, point in enumerate(results, start=1):
        payload = point.payload or {}

        print("=" * 72)
        print(f"Result {rank} | Similarity score: {point.score:.4f}")
        print(f"Source: {payload.get('source', 'unknown')}")
        print(f"Title: {payload.get('title', 'unknown')}")
        print(f"Chunk index: {payload.get('chunk_index', 'unknown')}")
        print("\nText:")
        print(payload.get("text", ""))

    if not results:
        print("No matching chunks were found.")


if __name__ == "__main__":
    main()
