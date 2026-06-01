from pathlib import Path
from typing import Optional

from docx import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.tools import tool


TEXT_FILE_SUFFIXES = {".md", ".markdown", ".txt", ".text", ".rst"}
DEFAULT_OUTPUT_DIR = Path("outputs/job_applications")


@tool
def resume_reader_tool(file_path: str) -> str:
    """Read a resume file and return its extracted text. Supports PDF, DOCX, Markdown, and plain text."""
    path = Path(file_path).expanduser()
    if not path.is_file():
        return f"Could not find resume file: {file_path}"

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        loader = PyPDFLoader(str(path))
        documents = loader.load()
        pages = [document.page_content.strip() for document in documents]
        return "\n\n".join(page for page in pages if page)

    if suffix == ".docx":
        document = Document(str(path))
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs]
        return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)

    if suffix in TEXT_FILE_SUFFIXES:
        return path.read_text(encoding="utf-8").strip()

    supported_formats = ", ".join(sorted({".pdf", ".docx", *TEXT_FILE_SUFFIXES}))
    return f"Unsupported resume file type: {suffix}. Supported formats: {supported_formats}."


@tool
def tailored_resume_writer_tool(markdown_content: str, output_file_path: Optional[str] = None) -> str:
    """Write a tailored resume to a Markdown file and return the file path."""
    path = _markdown_output_path(output_file_path, "tailored_resume.md")
    path.write_text(_clean_markdown(markdown_content, "# Tailored Resume"), encoding="utf-8")
    return f"Tailored resume written to {path}"


@tool
def cover_letter_writer_tool(markdown_content: str, output_file_path: Optional[str] = None) -> str:
    """Write a tailored cover letter to a Markdown file and return the file path."""
    path = _markdown_output_path(output_file_path, "tailored_cover_letter.md")
    path.write_text(_clean_markdown(markdown_content, "# Cover Letter"), encoding="utf-8")
    return f"Tailored cover letter written to {path}"


def _markdown_output_path(output_file_path: Optional[str], default_file_name: str) -> Path:
    path = Path(output_file_path).expanduser() if output_file_path else DEFAULT_OUTPUT_DIR / default_file_name
    if path.suffix.lower() != ".md":
        path = path.with_suffix(".md")

    if not path.is_absolute():
        path = Path.cwd() / path

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _clean_markdown(markdown_content: str, fallback_heading: str) -> str:
    content = markdown_content.strip()
    if not content.startswith("# "):
        content = f"{fallback_heading}\n\n{content}"

    return content + "\n"
