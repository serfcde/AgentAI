from my_crew.agents.factory import create_agent_from_config

def decide_workflow(topic):

    topic = topic.lower()

    if "analysis" in topic:
        return "hierarchical"

    elif "multiple" in topic:
        return "parallel"

    return "network"


def create_supervisor_agent(is_manager: bool = False):
    return create_agent_from_config("supervisor_agent", is_manager=is_manager)
