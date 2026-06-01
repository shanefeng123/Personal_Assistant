import json
from typing import Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from langchain_core.tools import tool


TOP_TIER_VENUE_KEYWORDS = {
    "neurips",
    "nips",
    "icml",
    "iclr",
    "aistats",
    "colt",
    "mlsys",
    "cvpr",
    "iccv",
    "eccv",
    "acl",
    "emnlp",
    "naacl",
    "sigir",
    "kdd",
    "www",
    "the web conference",
    "sigmod",
    "vldb",
    "icde",
    "chi",
    "uist",
    "cscw",
    "aaai",
    "ijcai",
    "rss",
    "icra",
    "iros",
    "ccs",
    "usenix security",
    "ieee symposium on security and privacy",
    "ndss",
    "sosp",
    "osdi",
    "nsdi",
    "sigcomm",
    "asplos",
    "isca",
    "micro",
    "pldi",
    "popl",
    "oopsla",
    "focs",
    "stoc",
    "soda",
}


@tool
def academic_paper_search_tool(query: str, max_results: int = 8, year_from: Optional[int] = None) -> str:
    """Search Semantic Scholar for papers and return abstracts, venue details, years, and links."""
    result_limit = max(1, min(max_results, 20))
    params = {
        "query": query,
        "limit": result_limit,
        "fields": "title,abstract,year,venue,url,citationCount,authors,externalIds,publicationTypes,publicationVenue",
    }
    if year_from:
        params["year"] = f"{year_from}-"

    request = Request(
        f"https://api.semanticscholar.org/graph/v1/paper/search?{urlencode(params)}",
        headers={"User-Agent": "personal-assistant/0.1"},
    )

    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return f"Paper search failed for query '{query}': {exc}"

    papers = payload.get("data", [])
    if not papers:
        return f"No papers found for query: {query}"

    formatted_papers = []
    for index, paper in enumerate(papers, start=1):
        title = paper.get("title") or "Untitled"
        abstract = paper.get("abstract") or "No abstract available."
        year = paper.get("year") or "Unknown year"
        venue = _paper_venue(paper)
        authors = ", ".join(author.get("name", "Unknown") for author in paper.get("authors", [])[:4])
        if len(paper.get("authors", [])) > 4:
            authors += ", et al."
        url = _paper_url(paper)
        citation_count = paper.get("citationCount", 0)
        top_tier_hint = "yes" if _looks_top_tier(venue) else "unknown/no"

        formatted_papers.append(
            "\n".join(
                [
                    f"{index}. {title}",
                    f"Authors: {authors or 'Unknown'}",
                    f"Year: {year}",
                    f"Venue: {venue}",
                    f"Top-tier venue hint: {top_tier_hint}",
                    f"Citations: {citation_count}",
                    f"URL: {url}",
                    f"Abstract: {abstract}",
                ]
            )
        )

    return "\n\n".join(formatted_papers)


def _paper_venue(paper: dict) -> str:
    publication_venue = paper.get("publicationVenue") or {}
    venue_name = publication_venue.get("name")
    if venue_name:
        return venue_name

    return paper.get("venue") or "Unknown venue"


def _paper_url(paper: dict) -> str:
    external_ids = paper.get("externalIds") or {}
    if external_ids.get("DOI"):
        return f"https://doi.org/{external_ids['DOI']}"

    if external_ids.get("ArXiv"):
        return f"https://arxiv.org/abs/{external_ids['ArXiv']}"

    return paper.get("url") or "No URL available"


def _looks_top_tier(venue: str) -> bool:
    venue_lower = venue.lower()
    return any(keyword in venue_lower for keyword in TOP_TIER_VENUE_KEYWORDS)
