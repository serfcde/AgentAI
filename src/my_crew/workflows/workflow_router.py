from my_crew.agents.supervisor import decide_workflow
from my_crew.utils.logger import get_logger
from my_crew.workflows.hierarchical_flow import run_hierarchical_flow
from my_crew.workflows.network_flow import run_network_flow
from my_crew.workflows.parallel_flow import run_parallel_flow


logger = get_logger("my_crew.router")

WORKFLOW_RUNNERS = {
    "network": run_network_flow,
    "hierarchical": run_hierarchical_flow,
    "parallel": run_parallel_flow,
}


def choose_workflow(topic: str):
    workflow = decide_workflow(topic)
    logger.info("Routed topic to the %s workflow.", workflow)
    return WORKFLOW_RUNNERS[workflow](topic)
