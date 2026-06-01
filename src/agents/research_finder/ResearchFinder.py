from typing import Optional

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ...State import ResearchFinderState, State
from ...tools.ResearchFinderToolNode import research_finder_tools


class ResearchFinderIntakeOutput(BaseModel):
    message: str = Field(description="The message that the research finder intake node will output.")
    user_input_needed: bool = Field(default=False, description="Whether more user input is needed before continuing.")
    route: bool = Field(default=False, description="Whether the state should be routed to the research finder node.")
    node_to_route: Optional[str] = Field(default=None, description="If route is true, the node to route to.")
    topics: Optional[str] = Field(default=None, description="The research topics the user wants papers about.")
    field: Optional[str] = Field(default=None, description="The research field or area, if provided.")


RESEARCH_FINDER_INTAKE_PROMPT = """
You are the intake node for a research finder agent.

Your job is to identify the research topic the user wants to read papers about. Do not search for papers or recommend
papers yourself.

Required information:
- topics: the research topic, question, method, or area the user wants papers about.

If topics is missing:
- Set user_input_needed=true.
- Set route=false.
- Set node_to_route=null.
- Ask the user what research topic they want papers about.

If topics is available:
- Set user_input_needed=false.
- Set route=true.
- Set node_to_route="research_finder_node".
- Copy the topic into topics.
- Set field when the user provided or strongly implied a field such as machine learning, NLP, computer vision, systems,
  security, databases, HCI, robotics, theory, or economics.
- Write a brief handoff message.
""".strip()


RESEARCH_FINDER_PROMPT = """
You are a research finder assistant.

You help the user find relevant academic papers for their topic, with a preference for papers from top-tier
conferences. Use academic_paper_search_tool to search for candidate papers. Read the abstracts in the tool results and
judge relevance from the abstracts, not just from titles.

Workflow:
- Search for papers using the user's topic.
- Prefer top-tier conference venues when available.
- If the first search does not surface enough strong top-tier results, try one or two refined search queries.
- Select a concise list of the most relevant papers.
- Explain why each paper is relevant based on its abstract.
- Mention venue, year, link, and whether the venue appears top-tier.
- If relevant top-tier conference papers are sparse, say that clearly and include the best available alternatives.

Do not invent papers, abstracts, venues, links, or publication details.
""".strip()


def research_finder_intake_node(old_state: State) -> State:
    """
    Extract research finder inputs into research finder state.
    """
    llm = ChatOpenAI(model="gpt-4o-mini")
    intake = llm.with_structured_output(ResearchFinderIntakeOutput)
    current_research_state = old_state.research_finder_state
    response = intake.invoke(
        [
            SystemMessage(content=RESEARCH_FINDER_INTAKE_PROMPT),
            SystemMessage(
                content=(
                    f"Existing research topics: {current_research_state.topics}\n"
                    f"Existing research field: {current_research_state.field}"
                )
            ),
            *old_state.messages,
        ]
    )
    research_finder_state = ResearchFinderState(
        topics=response.topics or current_research_state.topics,
        field=response.field or current_research_state.field,
    )

    return State(
        messages=[AIMessage(content=response.message)],
        user_input_needed=response.user_input_needed,
        route=response.route,
        node_to_route=response.node_to_route,
        job_application_state=old_state.job_application_state,
        stock_analysis_state=old_state.stock_analysis_state,
        research_finder_state=research_finder_state,
    )


def research_finder_node(old_state: State) -> State:
    """
    This is the research finder agent node.
    """
    llm = ChatOpenAI(model="gpt-4o-mini").bind_tools(research_finder_tools)
    topics = old_state.research_finder_state.topics
    field = old_state.research_finder_state.field
    response = llm.invoke(
        [
            SystemMessage(content=RESEARCH_FINDER_PROMPT),
            SystemMessage(content=f"Research topics: {topics}"),
            SystemMessage(content=f"Research field: {field}"),
            *old_state.messages,
        ]
    )

    return State(
        messages=[response],
        job_application_state=old_state.job_application_state,
        stock_analysis_state=old_state.stock_analysis_state,
        research_finder_state=old_state.research_finder_state,
    )
