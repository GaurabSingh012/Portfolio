
from pathlib import Path

import pytest

from app import ingestion


# ---------------------------------------------------------
# 1. Document Discovery
# ---------------------------------------------------------

def test_discover_documents_finds_supported_files(
    tmp_path,
    monkeypatch,
):
    """Find Markdown, TXT and PDF files inside knowledge/."""

    knowledge_dir = tmp_path / "knowledge"
    projects_dir = knowledge_dir / "projects"
    projects_dir.mkdir(parents=True)

    (knowledge_dir / "profile.md").write_text("Profile")
    (knowledge_dir / "notes.txt").write_text("Notes")
    (projects_dir / "project.pdf").write_bytes(b"PDF placeholder")
    (knowledge_dir / "data.csv").write_text("Unsupported")

    monkeypatch.setattr(ingestion, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(
        ingestion,
        "KNOWLEDGE_DIR",
        knowledge_dir,
    )

    result = ingestion.discover_documents()

    discovered = {
        path.relative_to(tmp_path).as_posix()
        for path in result
    }

    assert discovered == {
        "knowledge/profile.md",
        "knowledge/notes.txt",
        "knowledge/projects/project.pdf",
    }


def test_discover_documents_finds_readme_files(
    tmp_path,
    monkeypatch,
):
    """Find README.md files in the repository."""

    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()

    (tmp_path / "README.md").write_text("Main README")

    nested_dir = tmp_path / "projects" / "demo"
    nested_dir.mkdir(parents=True)
    (nested_dir / "README.md").write_text("Project README")

    monkeypatch.setattr(ingestion, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(
        ingestion,
        "KNOWLEDGE_DIR",
        knowledge_dir,
    )

    result = ingestion.discover_documents()

    discovered = {
        path.relative_to(tmp_path).as_posix()
        for path in result
    }

    assert "README.md" in discovered
    assert "projects/demo/README.md" in discovered


def test_discover_documents_excludes_unwanted_directories(
    tmp_path,
    monkeypatch,
):
    """README files in excluded directories must not be discovered."""

    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()

    excluded_dirs = [
        ".git",
        "node_modules",
        "public",
        "dist",
    ]

    for directory in excluded_dirs:
        excluded_path = tmp_path / directory
        excluded_path.mkdir()

        (excluded_path / "README.md").write_text(
            "Should be excluded"
        )

    (tmp_path / "README.md").write_text("Main README")

    monkeypatch.setattr(ingestion, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(
        ingestion,
        "KNOWLEDGE_DIR",
        knowledge_dir,
    )

    result = ingestion.discover_documents()

    discovered = {
        path.relative_to(tmp_path).as_posix()
        for path in result
    }

    assert discovered == {"README.md"}


# ---------------------------------------------------------
# 2. Text Extraction
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "extension",
    [".md", ".txt"],
)
def test_extract_text_reads_text_files(
    tmp_path,
    extension,
):
    """Markdown and TXT files should be read correctly."""

    file_path = tmp_path / f"document{extension}"
    file_path.write_text(
        "  Portfolio information  ",
        encoding="utf-8",
    )

    result = ingestion.extract_text(file_path)

    assert result == "Portfolio information"


def test_extract_text_reads_pdf_pages(
    tmp_path,
    monkeypatch,
):
    """PDF page text should be combined with page separation."""

    file_path = tmp_path / "resume.pdf"
    file_path.write_bytes(b"PDF placeholder")

    class FakePage:
        def __init__(self, text):
            self.text = text

        def extract_text(self):
            return self.text

    class FakePdfReader:
        def __init__(self, path):
            assert path == str(file_path)

            self.pages = [
                FakePage("First page"),
                FakePage("Second page"),
                FakePage(None),
            ]

    monkeypatch.setattr(
        ingestion,
        "PdfReader",
        FakePdfReader,
    )

    result = ingestion.extract_text(file_path)

    assert result == "First page\n\nSecond page"


def test_extract_text_rejects_unsupported_file():
    """Unsupported extensions must raise ValueError."""

    with pytest.raises(ValueError, match="Unsupported file type"):
        ingestion.extract_text(Path("document.csv"))


# ---------------------------------------------------------
# 3. Document Loading
# ---------------------------------------------------------

def test_load_documents_creates_metadata_and_skips_failures(
    tmp_path,
    monkeypatch,
):
    """Load readable documents and skip empty or unreadable ones."""

    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()

    profile = knowledge_dir / "profile.md"
    empty_file = knowledge_dir / "empty.txt"
    broken_file = knowledge_dir / "broken.pdf"

    profile.write_text("Gaurab's portfolio profile")
    empty_file.write_text("")
    broken_file.write_bytes(b"Invalid PDF")

    monkeypatch.setattr(ingestion, "ROOT_DIR", tmp_path)

    def fake_extract_text(path):
        if path == broken_file:
            raise ValueError("Invalid PDF")

        if path == empty_file:
            return ""

        return "Gaurab's portfolio profile"

    monkeypatch.setattr(
        ingestion,
        "extract_text",
        fake_extract_text,
    )

    documents = ingestion.load_documents(
        [profile, empty_file, broken_file]
    )

    assert len(documents) == 1

    document = documents[0]

    assert document.source == "knowledge/profile.md"
    assert document.title == "profile"
    assert document.text == "Gaurab's portfolio profile"
