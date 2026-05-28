from my_crew.agents.factory import create_agent_from_config


def create_executor_agent():
    return create_agent_from_config("execution_agent")
