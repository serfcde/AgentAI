from crewai import Agent
from my_crew.config.llm import llm


def create_supervisor_agent():
    return Agent(
        role="Supervisor Agent",

        goal="""
        Coordinate multiple agents,
        manage workflows,
        delegate responsibilities,
        and ensure successful task completion.
        """,

        backstory="""
        You are a senior AI orchestration supervisor.

        You specialize in:
        - multi-agent coordination
        - workflow supervision
        - delegation strategies
        - hierarchical AI systems
        - agent communication

        You ensure all agents work together efficiently.
        """,

        verbose=True,

        allow_delegation=True,

        llm=llm
    )