from langgraph.prebuilt import ToolNode

from .StockAnalysisTools import stock_news_search_tool, stock_price_trend_tool


stock_analysis_tools = [
    stock_price_trend_tool,
    stock_news_search_tool,
]
stock_analysis_tool_node = ToolNode(stock_analysis_tools)
