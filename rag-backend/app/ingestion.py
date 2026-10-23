import os
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from app.chunking import chunk_text


# The project root is two directory levels above this file.
ROOT_DIR = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = ROOT_DIR / "knowledge"

SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf"}

EXCLUDED_DIRS = {
    ".git",
    ".next",
    ".venv",
    "venv",
    "node_modules",
    ".vercel",
    "public",
    "dist",
    "build",
    "coverage",
    "rag-backend",
}


@dataclass
class Document:
    """Text and metadata extracted from one source file."""

    source: str
    title: str
    text: str


def discover_documents() -> list[Path]:
    """Discover supported files inside knowledge/ and README.md files."""
    discovered: set[Path] = set()

    # Find Markdown, text, and PDF files inside knowledge/.
    if KNOWLEDGE_DIR.exists():
        for path in KNOWLEDGE_DIR.rglob("*"):
            if (
                path.is_file()
                and path.suffix.lower() in SUPPORTED_EXTENSIONS
            ):
                discovered.add(path.resolve())

    # Find README.md files elsewhere in the repository.
    # Exclude dependency and build directories.
    for current_dir, dirnames, filenames in os.walk(ROOT_DIR):
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in EXCLUDED_DIRS
        ]

        current_path = Path(current_dir)

        # README files inside knowledge/ were already discovered above.
        if (
            current_path == KNOWLEDGE_DIR
            or KNOWLEDGE_DIR in current_path.parents
        ):
            continue

        if "README.md" in filenames:
            discovered.add(
                (current_path / "README.md").resolve()
            )

    return sorted(discovered)


def extract_text(path: Path) -> str:
    """Extract readable text from Markdown, TXT, or PDF files."""

    extension = path.suffix.lower()

    if extension == ".pdf":
        reader = PdfReader(str(path))

        pages = [
            page.extract_text() or ""
            for page in reader.pages
        ]

        return "\n\n".join(pages).strip()

    if extension in {".md", ".txt"}:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        ).strip()

    raise ValueError(f"Unsupported file type: {extension}")


def load_documents(paths: list[Path]) -> list[Document]:
    """Extract text and attach metadata to each readable document."""

    documents: list[Document] = []

    for path in paths:
        try:
            content = extract_text(path)

            if not content:
                print(
                    f"WARNING: No extractable text in "
                    f"{path.relative_to(ROOT_DIR)}"
                )
                continue

            documents.append(
                Document(
                    source=path.relative_to(ROOT_DIR).as_posix(),
                    title=path.stem,
                    text=content,
                )
            )

        except Exception as error:
            print(
                f"ERROR: Could not read "
                f"{path.relative_to(ROOT_DIR)}: {error}"
            )

    return documents


def run_dry_run() -> None:
    """
    Discover documents, extract their text, and prepare chunks.

    This function does not generate embeddings or write to Qdrant.
    """

    paths = discover_documents()
    documents = load_documents(paths)

    print(f"Repository: {ROOT_DIR}")
    print(f"Discovered {len(paths)} supported file(s).")
    print(f"Successfully loaded {len(documents)} document(s).\n")

    total_chunks = 0

    for document in documents:
        chunks = chunk_text(document.text)

        print(
            f"- {document.source}: "
            f"{len(document.text)} characters, "
            f"{len(chunks)} chunk(s)"
        )

        total_chunks += len(chunks)

    print(f"\nTotal chunks prepared: {total_chunks}")
    print("Dry run complete. No embeddings or Qdrant writes occurred.")


if __name__ == "__main__":
    run_dry_run()