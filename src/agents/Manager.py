from typing import Optional
from langchain_core.messages import SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from ..State import State

AGENT_TO_ROUTE = {
    "job_application_intake_node": "job_application_intake_node"
}


class ManagerOutput(BaseModel):
    message: str = Field(description="The message that the manager node will output.")
    user_input_needed: bool = Field(default=False,
                                    description="Whether the state requires user input before proceeding.")
    route: bool = Field(default=False, description="Whether the state should be routed to the next node or not.")
    node_to_route: Optional[str] = Field(default=None,
                                         description="If route is True, the name of the node to route to.")


MANAGER_PROMPT = f"""
You are the manager agent for an AI personal assistant.

Your job is to inspect the user's latest request and decide whether it can be routed to one of the available agent
nodes. Do not complete the user's task yourself.

Available agent nodes:
{", ".join(AGENT_TO_ROUTE)}

If the request clearly belongs to one of the available agent nodes:
- Set route=true.
- Set user_input_needed=false.
- Set node_to_route to the correct node name.
- Set message to a brief handoff message.

If the request does not contain enough information to choose a node or proceed:
- Set route=false.
- Set user_input_needed=true.
- Set node_to_route=null.
- Set message to a concise question asking the user for the missing information.
""".strip()


def manager_node(old_state: State) -> State:
    llm = ChatOpenAI(model="gpt-4o-mini")
    manager = llm.with_structured_output(ManagerOutput)
    response = manager.invoke([SystemMessage(content=MANAGER_PROMPT), *old_state.messages])

    new_state = State(
        messages=[AIMessage(content=response.message)],
        user_input_needed=response.user_input_needed,
        route=response.route,
        node_to_route=response.node_to_route,
        job_application_state=old_state.job_application_state,
    )
    return new_state
