from langgraph.prebuilt import ToolNode

from .JobApplicationTools import resume_reader_tool
from .CommonTools import url_text_extractor_tool


job_application_tools = [resume_reader_tool, url_text_extractor_tool]
job_application_tool_node = ToolNode(job_application_tools)
