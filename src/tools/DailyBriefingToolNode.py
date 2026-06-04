from langgraph.prebuilt import ToolNode

from .EmailCalendarTools import find_unanswered_emails_tool, read_calendar_events_tool, read_unread_emails_tool
from .ResearchFinderTools import academic_paper_search_tool
from .StockAnalysisTools import stock_news_search_tool, stock_price_trend_tool


daily_briefing_tools = [
    read_calendar_events_tool,
    read_unread_emails_tool,
    find_unanswered_emails_tool,
    stock_price_trend_tool,
    stock_news_search_tool,
    academic_paper_search_tool,
]
daily_briefing_tool_node = ToolNode(daily_briefing_tools)
