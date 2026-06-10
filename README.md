# Personal Assistant

Personal Assistant is a LangGraph-based agent workflow for routing user requests to specialized agents. It currently
runs as a terminal chat app and uses a manager node to decide which specialist workflow should handle each request.

The graph uses:

- LangGraph for node orchestration, routing, tool execution, and in-memory checkpoints.
- LangChain and OpenAI chat models for LLM reasoning and structured output.
- Tool nodes for web extraction, file reading/writing, stock data, web search, academic paper search, email, calendar,
  and daily briefing assembly.
- A shared evaluator node for final-response guardrails before responses are shown to the user.
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

For Apple Mail and Apple Calendar tools, macOS may ask you to allow your terminal or Python runner to control Mail and
Calendar the first time those tools run.

## Agents

### Manager Agent

The manager is the entry point of the graph. It does not complete user tasks directly. Instead, it reads the latest
request and routes it to the right specialist intake node.

It can currently route to:

- Job application workflow
- Stock analysis workflow
- Research finder workflow
- Email/calendar workflow
- Daily briefing workflow

### Evaluator Agent

The evaluator is a shared final-response guardrail. It reviews specialist agent responses before they are returned to
the user.

It checks for:

- Missing required information.
- Unsupported claims or invented facts.
- Unsafe side-effect claims, such as saying an email was sent when only drafting is allowed.
- Domain-specific rules for job applications, stock analysis, research paper discovery, and email/calendar tasks.
- Confirmation requirements for sensitive actions such as email draft creation and calendar event creation.

If a response passes, the original response is preserved exactly. If it fails, the evaluator returns a corrected
Markdown response or asks the user for the missing information.

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

### Email/Calendar Agent

The email/calendar workflow helps manage local email and scheduling tasks.

It can:

- Read unread emails from Apple Mail.
- Search emails by sender, subject, or body text.
- Summarize important unread emails.
- Detect action items from email content.
- Draft email replies only after explicit user confirmation, without sending them.
- Check Apple Calendar availability before scheduling.
- Create Apple Calendar events only after explicit user confirmation.
- Find potential unanswered sent emails older than a chosen number of days for follow-up.

The workflow stores client preferences in `EmailCalendarState`, so the agent can later support other providers without
changing the graph structure. LangChain has existing toolkit paths for Gmail and Office365/Microsoft 365, while the
current implementation uses local macOS automation for Apple Mail and Apple Calendar.

Sensitive email/calendar actions are guarded at the tool boundary. The draft-email and create-calendar-event tools
refuse to perform side effects unless they are called with `confirmed=True`, and the agent prompt instructs the model to
use that flag only after the user explicitly confirms the details.

### Daily Briefing Agent

The daily briefing workflow creates a concise briefing for today or another requested date.

It can:

- Extract briefing preferences during intake, such as date and which sections to include.
- Read Apple Calendar events for the requested date.
- Summarize important unread Apple Mail emails.
- Find potential unanswered sent emails for follow-up.
- Include stock updates when a saved ticker is available and the user asks for market information.
- Include research paper updates when saved research topics are available and the user asks for research information.
- Produce a structured Markdown briefing with agenda, email highlights, action items, and follow-ups.

The default briefing includes calendar, unread email, and follow-up sections. Stock and research sections are opt-in
because they require saved context such as a ticker or research topic.

## Security Considerations

The project is designed around controlled tool use and workflow-specific context isolation:

- The manager routes requests to specialist workflows instead of giving every agent every tool.
- Each workflow has its own nested state object so resume paths, tickers, research topics, email settings, and briefing
  preferences do not overwrite each other.
- Intake nodes use structured outputs to extract only the fields each workflow needs.
- Tool nodes are separated by workflow, limiting which tools each specialist agent can call.
- Sensitive actions require human confirmation before side effects happen.
- The evaluator reviews final responses for unsupported claims, invented tool results, unsafe side-effect claims, and
  domain-specific rules.
- Checkpoint serialization explicitly allowlists the custom state classes used by the graph.

## Project Structure

```text
src/
  State.py
  agents/
    Manager.py
    Evaluator.py
    job_application/
      JobApplication.py
    stock_analysis/
      StockAnalysis.py
    research_finder/
      ResearchFinder.py
    email_calendar/
      EmailCalendar.py
    daily_briefing/
      DailyBriefing.py
  tools/
    CommonTools.py
    JobApplicationTools.py
    StockAnalysisTools.py
    ResearchFinderTools.py
    EmailCalendarTools.py
    DailyBriefingToolNode.py
  routers.py
main.py
```

## Memory

The graph uses LangGraph's `MemorySaver` checkpointing with a default thread id, so a running CLI session can preserve
conversation history and structured state between turns.
