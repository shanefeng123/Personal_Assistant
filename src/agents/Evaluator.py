from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ..State import State


class EvaluatorOutput(BaseModel):
    approved: bool = Field(description="Whether the latest assistant response is safe and ready for the user.")
    user_input_needed: bool = Field(default=False, description="Whether the corrected response asks the user for input.")
    message: str = Field(description="The final Markdown response to show the user when the answer is not approved.")


EVALUATOR_PROMPT = """
You are the final evaluator and guardrail node for an AI personal assistant.

Evaluate only the latest assistant response. Do not redo the user's task from scratch.

If the latest assistant response is safe and ready:
- Set approved=true.
- Set user_input_needed=false.
- The message field can be empty because the system will preserve the original response.

If the latest assistant response has a problem:
- Set approved=false.
- Return a corrected Markdown message or a concise Markdown question for missing information.
- Set user_input_needed=true only when the user must provide more information before continuing.

Global checks:
- The response must be valid Markdown.
- The response must not invent facts, tool results, files, prices, papers, emails, calendar events, or availability.
- If the response claims a tool action happened, that action must be supported by prior tool output.
- If required information is missing, the response should ask for it instead of guessing.
- Do not expose unnecessary sensitive email content.

Job application checks:
- Do not fabricate experience, employers, degrees, dates, credentials, metrics, or achievements.
- Resume tailoring may rephrase or emphasize existing facts, but not invent new ones.

Stock analysis checks:
- Any buy, hold, or sell recommendation must be framed as informational, not personalized financial advice.
- Do not guarantee returns.
- Do not state current prices, recent trends, or recent news unless supported by tool output.

Research finder checks:
- Do not invent papers, authors, venues, years, abstracts, citation counts, or links.
- Only cite papers that were returned by the paper search tool.

Email/calendar checks:
- Never claim an email was sent. Drafting is allowed; sending is not.
- Do not claim an event was created unless the calendar tool confirmed it.
- Do not create or confirm scheduling when the date, time, duration, or title is ambiguous.
- Calendar event creation should be preceded by an availability check or protected by a tool-side conflict check.

Always format message as valid Markdown.
""".strip()


def evaluator_node(old_state: State) -> State:
    """
    Review the final assistant response before it is returned to the user.
    """
    latest_response = _latest_message_text(old_state)
    latest_message_id = getattr(old_state.messages[-1], "id", None) if old_state.messages else None
    if not latest_response:
        return State(
            messages=[AIMessage(content="I need a bit more information before I can help.")],
            user_input_needed=True,
            job_application_state=old_state.job_application_state,
            stock_analysis_state=old_state.stock_analysis_state,
            research_finder_state=old_state.research_finder_state,
            email_calendar_state=old_state.email_calendar_state,
        )

    llm = ChatOpenAI(model="gpt-4o-mini")
    evaluator = llm.with_structured_output(EvaluatorOutput)
    response = evaluator.invoke(
        [
            SystemMessage(content=EVALUATOR_PROMPT),
            SystemMessage(content=f"Latest assistant response:\n\n{latest_response}"),
            SystemMessage(
                content=(
                    "Current structured state:\n"
                    f"- Job application state: {old_state.job_application_state.model_dump()}\n"
                    f"- Stock analysis state: {old_state.stock_analysis_state.model_dump()}\n"
                    f"- Research finder state: {old_state.research_finder_state.model_dump()}\n"
                    f"- Email/calendar state: {old_state.email_calendar_state.model_dump()}"
                )
            ),
            *old_state.messages,
        ]
    )

    final_message = latest_response if response.approved else response.message
    return State(
        messages=[AIMessage(content=final_message, id=latest_message_id)],
        user_input_needed=response.user_input_needed,
        route=False,
        node_to_route=None,
        job_application_state=old_state.job_application_state,
        stock_analysis_state=old_state.stock_analysis_state,
        research_finder_state=old_state.research_finder_state,
        email_calendar_state=old_state.email_calendar_state,
    )


def _latest_message_text(state: State) -> str:
    if not state.messages:
        return ""

    content = state.messages[-1].content
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts).strip()

    return str(content).strip()
