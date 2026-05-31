from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.tools import tool


@tool
def resume_reader_tool(file_path: str) -> str:
    """Read a PDF resume file and return its extracted text."""
    path = Path(file_path).expanduser()
    if not path.is_file():
        return f"Could not find PDF file: {file_path}"

    loader = PyPDFLoader(str(path))
    documents = loader.load()
    pages = [document.page_content.strip() for document in documents]
    return "\n\n".join(page for page in pages if page)
