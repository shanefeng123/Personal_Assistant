from typing import Optional

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ...State import EmailCalendarState, State
from ...tools.EmailCalendarToolNode import email_calendar_tools


class EmailCalendarIntakeOutput(BaseModel):
    message: str = Field(description="The message that the email/calendar intake node will output.")
    user_input_needed: bool = Field(default=False, description="Whether more user input is needed before continuing.")
    route: bool = Field(default=False, description="Whether the state should be routed to the email/calendar node.")
    node_to_route: Optional[str] = Field(default=None, description="If route is true, the node to route to.")
    email_client: Optional[str] = Field(default=None, description="The email client the user wants to use.")
    calendar_client: Optional[str] = Field(default=None, description="The calendar client the user wants to use.")
    follow_up_days: Optional[int] = Field(default=None, description="The number of days after which to follow up.")


EMAIL_CALENDAR_INTAKE_PROMPT = """
You are the intake node for an email and calendar assistant.

Your job is to extract lightweight routing information. Do not read emails, summarize emails, draft replies, check
availability, or create calendar events yourself.

Supported local clients:
- email_client="macos" for Apple Mail.
- calendar_client="macos" for Apple Calendar.

Gmail and Outlook/Microsoft 365 can be supported later by swapping in their provider tools. If the user does not name a
client, default to macos because this project currently uses Apple Mail and Apple Calendar.

Extract:
- email_client: the email client to use for email tasks.
- calendar_client: the calendar client to use for calendar tasks.
- follow_up_days: the number of days for unanswered-email follow-up requests, when provided.

If the user asks to follow up on unanswered emails but does not provide how many days to wait:
- Set user_input_needed=true.
- Set route=false.
- Set node_to_route=null.
- Ask how many days old the unanswered emails should be.

If the request can proceed:
- Set user_input_needed=false.
- Set route=true.
- Set node_to_route="email_calendar_node".
- Write a brief handoff message.

Always format message as valid Markdown.
""".strip()


EMAIL_CALENDAR_PROMPT = """
You are an email and calendar assistant.

You help the user manage email and calendar tasks.

Capabilities:
- Read unread emails and summarize important unread emails.
- Search/read emails by sender, subject, or body text.
- Detect action items from email content.
- Draft email replies after explicit user confirmation, but never send email.
- Check calendar availability before scheduling.
- Create calendar events from email or user-provided context after explicit user confirmation.
- Find potential unanswered sent emails after a specified number of days and draft follow-up replies when useful.

Workflow guidance:
- Use read_unread_emails_tool before summarizing unread emails or extracting action items from unread emails.
- Use search_emails_tool when the user refers to a specific sender, subject, thread, or email context.
- Use read_calendar_events_tool when the user asks what is on their calendar for a date.
- Before creating an email draft, show the recipient, subject, and brief body summary, then ask the user to confirm.
- Use draft_email_reply_tool with confirmed=True only after the user explicitly confirms the draft details.
- Do not claim an email was sent.
- Use check_calendar_availability_tool before calling create_calendar_event_tool.
- Before creating a calendar event, show the title, date, start time, end time, and location when available, then ask
  the user to confirm.
- Use create_calendar_event_tool with confirmed=True only after the user explicitly confirms the event details.
- Use create_calendar_event_tool only when the event has enough information: title, start time, end time or duration,
  and date.
- Use find_unanswered_emails_tool for unanswered-email follow-up requests. If the number of days is missing, ask for it.
- For date-times passed to calendar tools, prefer ISO 8601 with timezone, such as 2026-06-01T09:00:00+10:00.
- Do not invent inbox content, calendar events, recipients, dates, or availability. Use tools or ask the user.

All final responses to the user must be valid Markdown. Use headings, bullets, and concise action-item lists.
""".strip()


def email_calendar_intake_node(old_state: State) -> State:
    """
    Extract email/calendar client and follow-up inputs into email/calendar state.
    """
    llm = ChatOpenAI(model="gpt-4o-mini")
    intake = llm.with_structured_output(EmailCalendarIntakeOutput)
    current_email_calendar_state = old_state.email_calendar_state
    response = intake.invoke(
        [
            SystemMessage(content=EMAIL_CALENDAR_INTAKE_PROMPT),
            SystemMessage(
                content=(
                    f"Existing email client: {current_email_calendar_state.email_client}\n"
                    f"Existing calendar client: {current_email_calendar_state.calendar_client}\n"
                    f"Existing follow-up days: {current_email_calendar_state.follow_up_days}"
                )
            ),
            *old_state.messages,
        ]
    )

    email_calendar_state = EmailCalendarState(
        email_client=response.email_client or current_email_calendar_state.email_client or "macos",
        calendar_client=response.calendar_client or current_email_calendar_state.calendar_client or "macos",
        follow_up_days=response.follow_up_days or current_email_calendar_state.follow_up_days,
    )

    return State(
        messages=[AIMessage(content=response.message)],
        user_input_needed=response.user_input_needed,
        route=response.route,
        node_to_route=response.node_to_route,
        job_application_state=old_state.job_application_state,
        stock_analysis_state=old_state.stock_analysis_state,
        research_finder_state=old_state.research_finder_state,
        email_calendar_state=email_calendar_state,
        daily_briefing_state=old_state.daily_briefing_state,
    )


def email_calendar_node(old_state: State) -> State:
    """
    This is the email/calendar agent node.
    """
    llm = ChatOpenAI(model="gpt-4o-mini").bind_tools(email_calendar_tools)
    email_client = old_state.email_calendar_state.email_client or "macos"
    calendar_client = old_state.email_calendar_state.calendar_client or "macos"
    follow_up_days = old_state.email_calendar_state.follow_up_days
    response = llm.invoke(
        [
            SystemMessage(content=EMAIL_CALENDAR_PROMPT),
            SystemMessage(content=f"Email client: {email_client}"),
            SystemMessage(content=f"Calendar client: {calendar_client}"),
            SystemMessage(content=f"Follow-up days: {follow_up_days}"),
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
