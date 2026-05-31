from dotenv import load_dotenv

load_dotenv(override=True)

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import tools_condition

from src.State import State
from src.agents.Manager import manager_node
from src.agents.job_application.JobApplication import job_application_intake_node, job_application_node
from src.routers import job_application_intake_router, manager_router
from src.tools.JobApplicationToolNode import job_application_tool_node

graph_builder = StateGraph(State)
graph_builder.add_node("manager_node", manager_node)
graph_builder.add_node("job_application_intake_node", job_application_intake_node)
graph_builder.add_node("job_application_node", job_application_node)
graph_builder.add_node("job_application_tools", job_application_tool_node)
graph_builder.add_edge(START, "manager_node")
graph_builder.add_conditional_edges("manager_node", manager_router,
                                    {"job_application_intake_node": "job_application_intake_node", END: END})
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
graph = graph_builder.compile()
# save the graph to a file
graph_image = graph.get_graph().draw_mermaid_png()
with open("graph.png", "wb") as f:
    f.write(graph_image)

def chat(user_input: str):
    init_message = {"role": "user", "content": user_input}
    init_state = State(messages=[init_message])
    result = graph.invoke(init_state)
    return result["messages"][-1].content


def main():
    print("Agent: Hi there! I'm your personal assistant. How can I help you today?")
    while True:
        user_input = input("User: ")
        response = chat(user_input)
        print(f"Agent: {response}")


if __name__ == "__main__":
    main()
