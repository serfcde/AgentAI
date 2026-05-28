from crewai import Agent

from my_crew.config.llm import llm
from my_crew.config.loader import load_agent_config
from my_crew.tools.registry import resolve_tools


def create_agent_from_config(agent_key: str, *, is_manager: bool = False) -> Agent:
    config = load_agent_config(agent_key)

    tool_names = [] if is_manager else config.get("tools", [])

    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=config["backstory"],
        verbose=config.get("verbose", True),
        allow_delegation=config.get("allow_delegation", False),
        tools=resolve_tools(tool_names),
        llm=llm,
    )
