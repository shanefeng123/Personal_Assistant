from typing import Optional

import yfinance as yf
from ddgs import DDGS
from langchain_core.tools import tool


@tool
def stock_price_trend_tool(ticker: str, period: str = "3mo") -> str:
    """Fetch current stock price data and recent price trends for a ticker."""
    normalized_ticker = ticker.strip().upper()
    stock = yf.Ticker(normalized_ticker)
    history = stock.history(period=period, interval="1d")

    if history.empty or "Close" not in history:
        return f"No recent market data found for ticker {normalized_ticker}."

    closes = history["Close"].dropna()
    volumes = history["Volume"].dropna() if "Volume" in history else None
    if closes.empty:
        return f"No recent closing prices found for ticker {normalized_ticker}."

    latest_close = float(closes.iloc[-1])
    previous_close = float(closes.iloc[-2]) if len(closes) >= 2 else latest_close
    first_close = float(closes.iloc[0])

    one_day_change = _percent_change(latest_close, previous_close)
    period_change = _percent_change(latest_close, first_close)
    five_day_change = _window_change(closes, 5)
    one_month_change = _window_change(closes, 21)
    latest_volume = int(volumes.iloc[-1]) if volumes is not None and not volumes.empty else None

    lines = [
        f"Ticker: {normalized_ticker}",
        f"Latest close: {latest_close:,.2f}",
        f"1-day change: {one_day_change:+.2f}%",
        f"5-trading-day change: {_format_optional_percent(five_day_change)}",
        f"1-month change: {_format_optional_percent(one_month_change)}",
        f"{period} change: {period_change:+.2f}%",
        f"Recent high: {float(closes.max()):,.2f}",
        f"Recent low: {float(closes.min()):,.2f}",
    ]
    if latest_volume is not None:
        lines.append(f"Latest volume: {latest_volume:,}")

    return "\n".join(lines)


@tool
def stock_news_search_tool(query: str, max_results: int = 5) -> str:
    """Search the web for recent company or stock news and return titles, snippets, and links."""
    result_limit = max(1, min(max_results, 10))
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=result_limit, timelimit="m")

    if not results:
        return f"No recent search results found for query: {query}"

    formatted_results = []
    for index, result in enumerate(results, start=1):
        title = result.get("title", "Untitled")
        href = result.get("href") or result.get("url") or "No URL"
        body = result.get("body", "No summary available.")
        formatted_results.append(f"{index}. {title}\nURL: {href}\nSummary: {body}")

    return "\n\n".join(formatted_results)


def _percent_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0

    return ((current - previous) / previous) * 100


def _window_change(closes, window_size: int) -> Optional[float]:
    if len(closes) <= window_size:
        return None

    return _percent_change(float(closes.iloc[-1]), float(closes.iloc[-window_size - 1]))


def _format_optional_percent(value: Optional[float]) -> str:
    if value is None:
        return "not enough data"

    return f"{value:+.2f}%"
