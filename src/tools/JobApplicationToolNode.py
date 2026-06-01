from langgraph.prebuilt import ToolNode

from .JobApplicationTools import cover_letter_writer_tool, resume_reader_tool, tailored_resume_writer_tool
from .CommonTools import url_text_extractor_tool


job_application_tools = [
    resume_reader_tool,
    url_text_extractor_tool,
    tailored_resume_writer_tool,
    cover_letter_writer_tool,
]
job_application_tool_node = ToolNode(job_application_tools)
