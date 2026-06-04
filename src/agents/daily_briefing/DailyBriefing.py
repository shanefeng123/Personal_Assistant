from datetime import datetime
from typing import Optional

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ...State import DailyBriefingState, State
from ...tools.DailyBriefingToolNode import daily_briefing_tools


class DailyBriefingIntakeOutput(BaseModel):
    message: str = Field(description="The message that the daily briefing intake node will output.")
    user_input_needed: bool = Field(default=False, description="Whether more user input is needed before continuing.")
    route: bool = Field(default=False, description="Whether the state should be routed to the daily briefing node.")
    node_to_route: Optional[str] = Field(default=None, description="If route is true, the node to route to.")
    briefing_date: Optional[str] = Field(default=None, description="The briefing date in YYYY-MM-DD format.")
    include_email: Optional[bool] = Field(default=None, description="Whether unread emails should be included.")
    include_calendar: Optional[bool] = Field(default=None, description="Whether calendar events should be included.")
    include_followups: Optional[bool] = Field(default=None, description="Whether email follow-ups should be included.")
    include_stocks: Optional[bool] = Field(default=None, description="Whether stock updates should be included.")
    include_research: Optional[bool] = Field(default=None, description="Whether research paper updates should be included.")
    follow_up_days: Optional[int] = Field(default=None, description="The number of days after which to follow up.")


DAILY_BRIEFING_INTAKE_PROMPT = """
You are the intake node for a daily briefing agent.

Your job is to extract briefing preferences. Do not read email, calendar events, stock data, or research papers.

Default behavior:
- briefing_date: today's date, unless the user asks for another date.
- include_email=true unless the user excludes email.
- include_calendar=true unless the user excludes calendar.
- include_followups=true unless the user excludes follow-ups.
- include_stocks=false unless the user asks for stock or market updates.
- include_research=false unless the user asks for research or paper updates.
- follow_up_days=3 unless the user provides a different unanswered-email follow-up window.

If the request can proceed:
- Set user_input_needed=false.
- Set route=true.
- Set node_to_route="daily_briefing_node".
- Write a brief handoff message.

If the user asks for a briefing date that cannot be resolved:
- Set user_input_needed=true.
- Set route=false.
- Set node_to_route=null.
- Ask which date they want the briefing for.

Always format message as valid Markdown.
""".strip()


DAILY_BRIEFING_PROMPT = """
You are a daily briefing assistant.

Create a concise, useful Markdown briefing for the requested date.

Workflow:
- If include_calendar=true, call read_calendar_events_tool for the briefing date.
- If include_email=true, call read_unread_emails_tool and summarize important unread emails.
- If include_followups=true, call find_unanswered_emails_tool with the follow-up day window.
- If include_stocks=true and a ticker is available, call stock_price_trend_tool and stock_news_search_tool.
- If include_research=true and research topics are available, call academic_paper_search_tool.

Rules:
- Do not invent emails, calendar events, stock data, news, papers, or follow-up candidates.
- Summarize private email content. Do not dump full email bodies into the final response.
- Turn emails and calendar events into clear action items when supported by tool output.
- If a section is requested but the tool fails or the required saved context is missing, mark that section unavailable.
- Do not create calendar events, draft emails, or make side effects in a briefing.
- Stock updates are informational only, not personalized financial advice.

Use this Markdown structure:

# Daily Briefing

## Today At A Glance

## Calendar

## Important Unread Emails

## Action Items

## Follow-Ups

## Stock Watchlist

## Research Watch

Only include optional sections when requested or when there is useful information. Keep the briefing skimmable.
""".strip()


def daily_briefing_intake_node(old_state: State) -> State:
    """
    Extract daily briefing preferences into daily briefing state.
    """
    llm = ChatOpenAI(model="gpt-4o-mini")
    intake = llm.with_structured_output(DailyBriefingIntakeOutput)
    current_briefing_state = old_state.daily_briefing_state
    today = _today()
    response = intake.invoke(
        [
            SystemMessage(content=DAILY_BRIEFING_INTAKE_PROMPT),
            SystemMessage(content=f"Current local date: {today}"),
            SystemMessage(
                content=(
                    f"Existing briefing date: {current_briefing_state.briefing_date}\n"
                    f"Existing include_email: {current_briefing_state.include_email}\n"
                    f"Existing include_calendar: {current_briefing_state.include_calendar}\n"
                    f"Existing include_followups: {current_briefing_state.include_followups}\n"
                    f"Existing include_stocks: {current_briefing_state.include_stocks}\n"
                    f"Existing include_research: {current_briefing_state.include_research}\n"
                    f"Existing follow-up days: {current_briefing_state.follow_up_days}"
                )
            ),
            *old_state.messages,
        ]
    )

    daily_briefing_state = DailyBriefingState(
        briefing_date=response.briefing_date or current_briefing_state.briefing_date or today,
        include_email=_coalesce_bool(response.include_email, current_briefing_state.include_email),
        include_calendar=_coalesce_bool(response.include_calendar, current_briefing_state.include_calendar),
        include_followups=_coalesce_bool(response.include_followups, current_briefing_state.include_followups),
        include_stocks=_coalesce_bool(response.include_stocks, current_briefing_state.include_stocks),
        include_research=_coalesce_bool(response.include_research, current_briefing_state.include_research),
        follow_up_days=response.follow_up_days or current_briefing_state.follow_up_days or 3,
    )

    return State(
        messages=[AIMessage(content=response.message)],
        user_input_needed=response.user_input_needed,
        route=response.route,
        node_to_route=response.node_to_route,
        job_application_state=old_state.job_application_state,
        stock_analysis_state=old_state.stock_analysis_state,
        research_finder_state=old_state.research_finder_state,
        email_calendar_state=old_state.email_calendar_state,
        daily_briefing_state=daily_briefing_state,
    )


def daily_briefing_node(old_state: State) -> State:
    """
    This is the daily briefing agent node.
    """
    llm = ChatOpenAI(model="gpt-4o-mini").bind_tools(daily_briefing_tools)
    briefing_state = old_state.daily_briefing_state
    email_state = old_state.email_calendar_state
    stock_state = old_state.stock_analysis_state
    research_state = old_state.research_finder_state

    response = llm.invoke(
        [
            SystemMessage(content=DAILY_BRIEFING_PROMPT),
            SystemMessage(
                content=(
                    f"Briefing date: {briefing_state.briefing_date or _today()}\n"
                    f"Include email: {briefing_state.include_email}\n"
                    f"Include calendar: {briefing_state.include_calendar}\n"
                    f"Include follow-ups: {briefing_state.include_followups}\n"
                    f"Include stocks: {briefing_state.include_stocks}\n"
                    f"Include research: {briefing_state.include_research}\n"
                    f"Follow-up days: {briefing_state.follow_up_days or 3}\n"
                    f"Email client: {email_state.email_client or 'macos'}\n"
                    f"Calendar client: {email_state.calendar_client or 'macos'}\n"
                    f"Saved ticker: {stock_state.ticker}\n"
                    f"Saved company name: {stock_state.company_name}\n"
                    f"Saved research topics: {research_state.topics}\n"
                    f"Saved research field: {research_state.field}"
                )
            ),
            *old_state.messages,
        ]
    )

    return State(
        messages=[response],
        job_application_state=old_state.job_application_state,
        stock_analysis_state=old_state.stock_analysis_state,
        research_finder_state=old_state.research_finder_state,
        email_calendar_state=old_state.email_calendar_state,
        daily_briefing_state=old_state.daily_briefing_state,
    )


def _today() -> str:
    return datetime.now().astimezone().date().isoformat()


def _coalesce_bool(new_value: Optional[bool], old_value: bool) -> bool:
    return old_value if new_value is None else new_value
