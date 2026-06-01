from langgraph.graph import END
from .State import State

MANAGER_ROUTES = {
    "job_application_intake_node": "job_application_intake_node",
    "stock_analysis_intake_node": "stock_analysis_intake_node",
    "research_finder_intake_node": "research_finder_intake_node",
    "email_calendar_intake_node": "email_calendar_intake_node",
}

JOB_APPLICATION_INTAKE_ROUTES = {
    "job_application_node": "job_application_node"
}

STOCK_ANALYSIS_INTAKE_ROUTES = {
    "stock_analysis_node": "stock_analysis_node"
}

RESEARCH_FINDER_INTAKE_ROUTES = {
    "research_finder_node": "research_finder_node"
}

EMAIL_CALENDAR_INTAKE_ROUTES = {
    "email_calendar_node": "email_calendar_node"
}


def manager_router(state: State) -> str:
    if state.user_input_needed or not state.route:
        return END

    node_to_route = state.node_to_route
    return MANAGER_ROUTES.get(node_to_route, END)


def job_application_intake_router(state: State) -> str:
    if state.user_input_needed or not state.route:
        return END

    return JOB_APPLICATION_INTAKE_ROUTES.get(state.node_to_route, END)


def stock_analysis_intake_router(state: State) -> str:
    if state.user_input_needed or not state.route:
        return END

    return STOCK_ANALYSIS_INTAKE_ROUTES.get(state.node_to_route, END)


def research_finder_intake_router(state: State) -> str:
    if state.user_input_needed or not state.route:
        return END

    return RESEARCH_FINDER_INTAKE_ROUTES.get(state.node_to_route, END)


def email_calendar_intake_router(state: State) -> str:
    if state.user_input_needed or not state.route:
        return END

    return EMAIL_CALENDAR_INTAKE_ROUTES.get(state.node_to_route, END)
