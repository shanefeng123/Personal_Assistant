from urllib.parse import urlparse

from langchain_community.document_loaders import WebBaseLoader
from langchain_core.tools import tool


@tool
def url_text_extractor_tool(url: str) -> str:
    """Read a web page URL and return its extracted text."""
    parsed_url = urlparse(url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        return f"Cannot read URL because it is not a valid http or https URL: {url}"

    loader = WebBaseLoader(
        web_path=url,
        requests_kwargs={"timeout": 20},
        raise_for_status=True,
    )
    documents = loader.load()
    pages = [document.page_content.strip() for document in documents]
    return "\n\n".join(page for page in pages if page)
