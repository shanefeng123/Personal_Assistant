from langgraph.prebuilt import ToolNode

from .ResearchFinderTools import academic_paper_search_tool


research_finder_tools = [academic_paper_search_tool]
research_finder_tool_node = ToolNode(research_finder_tools)
