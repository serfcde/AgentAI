from my_crew.agents.factory import create_agent_from_config


def create_validator_agent():
    return create_agent_from_config("validation_agent")
