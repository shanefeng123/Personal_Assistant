from typing import Annotated, Optional

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class JobApplicationState(BaseModel):
    resume_file_path: Optional[str] = Field(default=None, description="The resume file path user provided.")
    job_description_url: Optional[str] = Field(default=None, description="The job description URL user provided.")


class StockAnalysisState(BaseModel):
    ticker: Optional[str] = Field(default=None, description="The stock ticker the user wants analyzed.")
    company_name: Optional[str] = Field(default=None, description="The company name the user wants analyzed.")


class ResearchFinderState(BaseModel):
    topics: Optional[str] = Field(default=None, description="The research topics the user wants papers about.")
    field: Optional[str] = Field(default=None, description="The research field or area, if provided.")


class EmailCalendarState(BaseModel):
    email_client: Optional[str] = Field(default=None, description="The email client the user wants to use.")
    calendar_client: Optional[str] = Field(default=None, description="The calendar client the user wants to use.")
    follow_up_days: Optional[int] = Field(default=None, description="The number of days after which to follow up.")


class State(BaseModel):
    messages: Annotated[list, add_messages] = Field(default_factory=list)
    user_input_needed: bool = Field(default=False, description="Whether the state requires user input before proceeding.")
    route: bool = Field(default=False, description="Whether the state should be routed to the next node or not.")
    node_to_route: Optional[str] = Field(default=None, description="If route is True, the name of the node to route to.")
    job_application_state: JobApplicationState = Field(default_factory=JobApplicationState)
    stock_analysis_state: StockAnalysisState = Field(default_factory=StockAnalysisState)
    research_finder_state: ResearchFinderState = Field(default_factory=ResearchFinderState)
    email_calendar_state: EmailCalendarState = Field(default_factory=EmailCalendarState)
