# Personal Assistant

Personal Assistant is a LangGraph-based agent workflow for routing user requests to specialized agents. It currently
runs as a terminal chat app and uses a manager node to decide which specialist workflow should handle each request.

The graph uses:

- LangGraph for node orchestration, routing, tool execution, and in-memory checkpoints.
- LangChain and OpenAI chat models for LLM reasoning and structured output.
- Tool nodes for web extraction, file reading/writing, stock data, web search, and academic paper search.
- Rich terminal rendering so Markdown responses are easier to read.

## Setup

This project uses `uv` and includes `pyproject.toml` plus `uv.lock`, so dependencies can be installed with:

```bash
uv sync
```

Create a `.env` file with the environment variables needed by the app:

```bash
OPENAI_API_KEY=your_openai_api_key
USER_AGENT=personal-assistant/0.1
```

`USER_AGENT` is used by web-loading tools.

Run the assistant with:

```bash
uv run python main.py
```

## Agents

### Manager Agent

The manager is the entry point of the graph. It does not complete user tasks directly. Instead, it reads the latest
request and routes it to the right specialist intake node.

It can currently route to:

- Job application workflow
- Stock analysis workflow
- Research finder workflow

### Job Application Agent

The job application workflow helps tailor application materials for a specific role.

It can:

- Extract the user's resume file path and job description URL during intake.
- Read resume files in PDF, DOCX, Markdown, and plain text formats.
- Extract text from a job description URL.
- Generate a tailored resume in Markdown.
- Generate a tailored cover letter in Markdown.
- Write the generated resume and cover letter to Markdown files.

Default generated files are written under:

```text
outputs/job_applications/
```

### Stock Analysis Agent

The stock analysis workflow helps analyze a public company or ticker.

It can:

- Extract a stock ticker and company name during intake.
- Fetch current and recent stock price trend data with `yfinance`.
- Search for recent company or stock-related news.
- Summarize recent price movement and likely news drivers.
- Provide a non-personal buy, hold, or sell recommendation with reasoning.

The analysis is informational only and should not be treated as personalized financial advice.

### Research Finder Agent

The research finder workflow helps find academic papers for a user-provided topic.

It can:

- Extract research topics and fields during intake.
- Search Semantic Scholar for related papers.
- Read returned paper abstracts and judge relevance.
- Prefer papers from top-tier conferences when available.
- Return paper titles, authors, venues, years, links, citation counts, and relevance notes.

## Project Structure

```text
src/
  State.py
  agents/
    Manager.py
    job_application/
      JobApplication.py
    stock_analysis/
      StockAnalysis.py
    research_finder/
      ResearchFinder.py
  tools/
    CommonTools.py
    JobApplicationTools.py
    StockAnalysisTools.py
    ResearchFinderTools.py
  routers.py
main.py
```

## Memory

The graph uses LangGraph's `MemorySaver` checkpointing with a default thread id, so a running CLI session can preserve
conversation history and structured state between turns.
