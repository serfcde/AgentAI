from my_crew.agents.factory import create_agent_from_config
from my_crew.agents.llm_judge import (
    LLMCaller,
    classify_workflow,
    get_default_llm_caller,
)


def decide_workflow_heuristic(topic: str) -> str:
    normalized = topic.lower()

    if "analysis" in normalized:
        return "hierarchical"

    if "multiple" in normalized:
        return "parallel"

    return "network"


def decide_workflow(topic: str, llm_caller: LLMCaller | None = None) -> str:
    caller = llm_caller or get_default_llm_caller("MY_CREW_LLM_ROUTING")
    choice = classify_workflow(topic, caller)
    return choice or decide_workflow_heuristic(topic)


def create_supervisor_agent(is_manager: bool = False):
    return create_agent_from_config("supervisor_agent", is_manager=is_manager)
