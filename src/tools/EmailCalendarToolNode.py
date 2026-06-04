from langgraph.prebuilt import ToolNode

from .EmailCalendarTools import (
    check_calendar_availability_tool,
    create_calendar_event_tool,
    draft_email_reply_tool,
    find_unanswered_emails_tool,
    read_calendar_events_tool,
    read_unread_emails_tool,
    search_emails_tool,
)


email_calendar_tools = [
    read_unread_emails_tool,
    search_emails_tool,
    draft_email_reply_tool,
    read_calendar_events_tool,
    check_calendar_availability_tool,
    create_calendar_event_tool,
    find_unanswered_emails_tool,
]
email_calendar_tool_node = ToolNode(email_calendar_tools)
