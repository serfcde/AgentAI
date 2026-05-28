from my_crew.agents.factory import create_agent_from_config


def create_planner_agent():
    return create_agent_from_config("planning_agent")
