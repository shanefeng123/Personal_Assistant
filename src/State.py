from typing import Annotated, Optional

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class JobApplicationState(BaseModel):
    resume_file_path: Optional[str] = Field(default=None, description="The resume file path user provided.")
    job_description_url: Optional[str] = Field(default=None, description="The job description URL user provided.")


class State(BaseModel):
    messages: Annotated[list, add_messages] = Field(default_factory=list)
    user_input_needed: bool = Field(default=False, description="Whether the state requires user input before proceeding.")
    route: bool = Field(default=False, description="Whether the state should be routed to the next node or not.")
    node_to_route: Optional[str] = Field(default=None, description="If route is True, the name of the node to route to.")
    job_application_state: JobApplicationState = Field(default_factory=JobApplicationState)
