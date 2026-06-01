from typing import Optional

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ...State import State, StockAnalysisState
from ...tools.StockAnalysisToolNode import stock_analysis_tools


class StockAnalysisIntakeOutput(BaseModel):
    message: str = Field(description="The message that the stock analysis intake node will output.")
    user_input_needed: bool = Field(default=False, description="Whether more user input is needed before continuing.")
    route: bool = Field(default=False, description="Whether the state should be routed to the stock analysis node.")
    node_to_route: Optional[str] = Field(default=None, description="If route is true, the node to route to.")
    ticker: Optional[str] = Field(default=None, description="The stock ticker the user wants analyzed.")
    company_name: Optional[str] = Field(default=None, description="The company name the user wants analyzed.")


STOCK_ANALYSIS_INTAKE_PROMPT = """
You are the intake node for a stock analysis agent.

Your job is to identify the stock the user wants analyzed. Do not research the company, fetch prices, or provide
investment analysis.

Required information:
- ticker: the public stock ticker symbol.
- company_name: the company name, if provided or obvious.

If the user provided a ticker, copy it exactly into ticker.
If the user provided only a company name, infer the ticker only when it is very obvious. Otherwise ask the user for the
ticker.

If ticker is missing:
- Set user_input_needed=true.
- Set route=false.
- Set node_to_route=null.
- Ask the user which ticker they want analyzed.

If ticker is available:
- Set user_input_needed=false.
- Set route=true.
- Set node_to_route="stock_analysis_node".
- Write a brief handoff message.
""".strip()


STOCK_ANALYSIS_PROMPT = """
You are a stock analysis assistant.

You help the user understand recent stock trends using current market data and recent company information.

Workflow:
- Use stock_price_trend_tool for the ticker's current price data and recent price trend.
- Use stock_news_search_tool to search for recent and relevant company or stock news.
- After using the tools, summarize the recent price trend, key news drivers, risks, and uncertainty.
- End with a clear non-personal buy, hold, or sell recommendation and explain the reasoning.

Important:
- This is informational analysis, not personalized financial advice.
- Do not guarantee returns.
- Do not invent current prices, news, or facts. Use the tools for current data.
- If the ticker is missing, ask the user for it.
""".strip()


def stock_analysis_intake_node(old_state: State) -> State:
    """
    Extract stock analysis inputs into stock analysis state.
    """
    llm = ChatOpenAI(model="gpt-4o-mini")
    intake = llm.with_structured_output(StockAnalysisIntakeOutput)
    current_stock_state = old_state.stock_analysis_state
    response = intake.invoke(
        [
            SystemMessage(content=STOCK_ANALYSIS_INTAKE_PROMPT),
            SystemMessage(
                content=(
                    f"Existing ticker: {current_stock_state.ticker}\n"
                    f"Existing company name: {current_stock_state.company_name}"
                )
            ),
            *old_state.messages,
        ]
    )
    stock_analysis_state = StockAnalysisState(
        ticker=response.ticker or current_stock_state.ticker,
        company_name=response.company_name or current_stock_state.company_name,
    )

    return State(
        messages=[AIMessage(content=response.message)],
        user_input_needed=response.user_input_needed,
        route=response.route,
        node_to_route=response.node_to_route,
        job_application_state=old_state.job_application_state,
        stock_analysis_state=stock_analysis_state,
        research_finder_state=old_state.research_finder_state,
    )


def stock_analysis_node(old_state: State) -> State:
    """
    This is the stock analysis agent node.
    """
    llm = ChatOpenAI(model="gpt-4o-mini").bind_tools(stock_analysis_tools)
    ticker = old_state.stock_analysis_state.ticker
    company_name = old_state.stock_analysis_state.company_name
    response = llm.invoke(
        [
            SystemMessage(content=STOCK_ANALYSIS_PROMPT),
            SystemMessage(content=f"Ticker: {ticker}"),
            SystemMessage(content=f"Company name: {company_name}"),
            *old_state.messages,
        ]
    )

    return State(
        messages=[response],
        job_application_state=old_state.job_application_state,
        stock_analysis_state=old_state.stock_analysis_state,
        research_finder_state=old_state.research_finder_state,
    )
