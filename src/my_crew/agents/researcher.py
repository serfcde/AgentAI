from my_crew.agents.factory import create_agent_from_config


def create_research_agent():
    return create_agent_from_config("research_agent")
