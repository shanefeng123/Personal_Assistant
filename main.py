from dotenv import load_dotenv

load_dotenv(override=True)

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import tools_condition
from rich.console import Console
from rich.markdown import Markdown

from src.State import JobApplicationState, ResearchFinderState, State, StockAnalysisState
from src.agents.Manager import manager_node
from src.agents.job_application.JobApplication import job_application_intake_node, job_application_node
from src.agents.research_finder.ResearchFinder import research_finder_intake_node, research_finder_node
from src.agents.stock_analysis.StockAnalysis import stock_analysis_intake_node, stock_analysis_node
from src.routers import (
    job_application_intake_router,
    manager_router,
    research_finder_intake_router,
    stock_analysis_intake_router,
)
from src.tools.JobApplicationToolNode import job_application_tool_node
from src.tools.ResearchFinderToolNode import research_finder_tool_node
from src.tools.StockAnalysisToolNode import stock_analysis_tool_node

DEFAULT_THREAD_ID = "default"
console = Console()

graph_builder = StateGraph(State)
graph_builder.add_node("manager_node", manager_node)
graph_builder.add_node("job_application_intake_node", job_application_intake_node)
graph_builder.add_node("job_application_node", job_application_node)
graph_builder.add_node("job_application_tools", job_application_tool_node)
graph_builder.add_node("stock_analysis_intake_node", stock_analysis_intake_node)
graph_builder.add_node("stock_analysis_node", stock_analysis_node)
graph_builder.add_node("stock_analysis_tools", stock_analysis_tool_node)
graph_builder.add_node("research_finder_intake_node", research_finder_intake_node)
graph_builder.add_node("research_finder_node", research_finder_node)
graph_builder.add_node("research_finder_tools", research_finder_tool_node)
graph_builder.add_edge(START, "manager_node")
graph_builder.add_conditional_edges("manager_node", manager_router,
                                    {
                                        "job_application_intake_node": "job_application_intake_node",
                                        "stock_analysis_intake_node": "stock_analysis_intake_node",
                                        "research_finder_intake_node": "research_finder_intake_node",
                                        END: END,
                                    })
graph_builder.add_conditional_edges(
    "job_application_intake_node",
    job_application_intake_router,
    {"job_application_node": "job_application_node", END: END},
)
graph_builder.add_conditional_edges(
    "job_application_node",
    tools_condition,
    {"tools": "job_application_tools", END: END},
)
graph_builder.add_edge("job_application_tools", "job_application_node")
graph_builder.add_conditional_edges(
    "stock_analysis_intake_node",
    stock_analysis_intake_router,
    {"stock_analysis_node": "stock_analysis_node", END: END},
)
graph_builder.add_conditional_edges(
    "stock_analysis_node",
    tools_condition,
    {"tools": "stock_analysis_tools", END: END},
)
graph_builder.add_edge("stock_analysis_tools", "stock_analysis_node")
graph_builder.add_conditional_edges(
    "research_finder_intake_node",
    research_finder_intake_router,
    {"research_finder_node": "research_finder_node", END: END},
)
graph_builder.add_conditional_edges(
    "research_finder_node",
    tools_condition,
    {"tools": "research_finder_tools", END: END},
)
graph_builder.add_edge("research_finder_tools", "research_finder_node")
serializer = JsonPlusSerializer().with_msgpack_allowlist(
    [JobApplicationState, StockAnalysisState, ResearchFinderState]
)
memory = MemorySaver(serde=serializer)
graph = graph_builder.compile(checkpointer=memory)
# save the graph to a file
graph_image = graph.get_graph().draw_mermaid_png()
with open("graph.png", "wb") as f:
    f.write(graph_image)

def chat(user_input: str, thread_id: str = DEFAULT_THREAD_ID):
    init_message = {"role": "user", "content": user_input}
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke({"messages": [init_message]}, config=config)
    return result["messages"][-1].content


def main():
    console.print(Markdown("**Agent:** Hi there! I'm your personal assistant. How can I help you today?"))
    while True:
        user_input = input("User: ")
        response = chat(user_input)
        console.print(Markdown(f"**Agent:**\n\n{response}"))


if __name__ == "__main__":
    main()
