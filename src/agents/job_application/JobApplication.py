from typing import Optional

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ...State import JobApplicationState, State
from ...tools.JobApplicationToolNode import job_application_tools


class JobApplicationIntakeOutput(BaseModel):
    message: str = Field(description="The message that the job application intake node will output.")
    user_input_needed: bool = Field(default=False, description="Whether more user input is needed before continuing.")
    route: bool = Field(default=False, description="Whether the state should be routed to the job application node.")
    node_to_route: Optional[str] = Field(default=None, description="If route is true, the node to route to.")
    resume_file_path: Optional[str] = Field(default=None, description="The resume file path user provided.")
    job_description_url: Optional[str] = Field(default=None, description="The job description URL user provided.")


JOB_APPLICATION_INTAKE_PROMPT = """
You are the intake node for a job application agent.

Your job is to extract the information the job application agent needs. Do not read files, open URLs, tailor resumes,
or complete the user's task.

Required information:
- resume_file_path: the path to the user's resume file.
- job_description_url: the URL for the job description.

If the user provided a resume file path, copy it exactly into resume_file_path. Otherwise set resume_file_path=null.
If the user provided a job description URL, copy it exactly into job_description_url. Otherwise set job_description_url=null.

If either required value is missing:
- Set user_input_needed=true.
- Set route=false.
- Set node_to_route=null.
- Ask the user for the missing information.

If both required values are available:
- Set user_input_needed=false.
- Set route=true.
- Set node_to_route="job_application_node".
- Write a brief handoff message.

Always format message as valid Markdown.
""".strip()


JOB_APPLICATION_PROMPT = """
You are a job application assistant.

You help the user with job application tasks.

Workflow:
- Read the user's resume with resume_reader_tool.
- Read the job description with url_text_extractor_tool.
- Tailor the resume to the job description without inventing experience, credentials, dates, employers, or metrics.
- Write the tailored resume to a Markdown file with tailored_resume_writer_tool.
- Write a tailored cover letter to a Markdown file with cover_letter_writer_tool.
- After both files are written, tell the user the file paths returned by the writer tools.

If the user's resume file path is available and you need to read the resume, call resume_reader_tool with that exact
file path. Do not invent a file path. If the resume file path is missing, ask the user to provide it.

If the user's job description URL is available and you need to read the job description, call url_text_extractor_tool
with that exact URL. Do not invent a URL. If the job description URL is missing, ask the user to provide it.

Tailored resume Markdown requirements:
- Start with a level-one heading containing the user's name if available, otherwise "Tailored Resume".
- Include clear sections with Markdown headings, such as Summary, Skills, Experience, Projects, Education, and Certifications when relevant.
- Use concise, role-aligned bullet points.
- Preserve truthful facts from the original resume.

Cover letter Markdown requirements:
- Start with "# Cover Letter".
- Include a short greeting, opening paragraph, role-aligned body paragraphs, closing paragraph, and sign-off.
- Keep it professional, specific to the role, and grounded in the user's real experience.

All final responses to the user must be valid Markdown. Use headings, bullets, links, and code-style file paths where useful.
""".strip()


def job_application_intake_node(old_state: State) -> State:
    """
    Extract job application inputs into job application state.
    """
    llm = ChatOpenAI(model="gpt-4o-mini")
    intake = llm.with_structured_output(JobApplicationIntakeOutput)
    current_job_application_state = old_state.job_application_state
    response = intake.invoke(
        [
            SystemMessage(content=JOB_APPLICATION_INTAKE_PROMPT),
            SystemMessage(
                content=(
                    f"Existing resume file path: {current_job_application_state.resume_file_path}\n"
                    f"Existing job description URL: {current_job_application_state.job_description_url}"
                )
            ),
            *old_state.messages,
        ]
    )
    job_application_state = JobApplicationState(
        resume_file_path=response.resume_file_path or current_job_application_state.resume_file_path,
        job_description_url=response.job_description_url or current_job_application_state.job_description_url,
    )

    return State(
        messages=[AIMessage(content=response.message)],
        user_input_needed=response.user_input_needed,
        route=response.route,
        node_to_route=response.node_to_route,
        job_application_state=job_application_state,
        stock_analysis_state=old_state.stock_analysis_state,
        research_finder_state=old_state.research_finder_state,
        email_calendar_state=old_state.email_calendar_state,
        daily_briefing_state=old_state.daily_briefing_state,
    )


def job_application_node(old_state: State) -> State:
    """
    This is the job application agent node.
    """
    llm = ChatOpenAI(model="gpt-4o-mini").bind_tools(job_application_tools)
    resume_file_path = old_state.job_application_state.resume_file_path
    job_description_url = old_state.job_application_state.job_description_url
    response = llm.invoke(
        [
            SystemMessage(content=JOB_APPLICATION_PROMPT),
            SystemMessage(content=f"Resume file path: {resume_file_path}"),
            SystemMessage(content=f"Job description URL: {job_description_url}"),
            *old_state.messages,
        ]
    )
    return State(
        messages=[response],
        job_application_state=old_state.job_application_state,
        stock_analysis_state=old_state.stock_analysis_state,
        research_finder_state=old_state.research_finder_state,
        email_calendar_state=old_state.email_calendar_state,
        daily_briefing_state=old_state.daily_briefing_state,
    )
