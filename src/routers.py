from langgraph.graph import END
from .State import State

MANAGER_ROUTES = {
    "job_application_intake_node": "job_application_intake_node"
}

JOB_APPLICATION_INTAKE_ROUTES = {
    "job_application_node": "job_application_node"
}


def manager_router(state: State) -> str:
    if state.user_input_needed or not state.route:
        return END

    node_to_route = state.node_to_route
    return MANAGER_ROUTES.get(node_to_route)


def job_application_intake_router(state: State) -> str:
    if state.user_input_needed or not state.route:
        return END

    return JOB_APPLICATION_INTAKE_ROUTES.get(state.node_to_route)
