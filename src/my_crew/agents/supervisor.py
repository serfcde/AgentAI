from crewai import Agent

from my_crew.config.llm import llm

from my_crew.tools.memory_tool import memory_tool
from my_crew.tools.notification_tool import notification_tool
from my_crew.tools.logger_tool import logger_tool


def create_supervisor_agent():

    return Agent(
        role="Supervisor Agent",

        goal="""
        Coordinate agent workflows,
        manage delegation,
        monitor communication,
        and ensure successful
        task completion.
        """,

        backstory="""
        You are a senior AI orchestration supervisor.

        You specialize in:
        - multi-agent coordination
        - workflow supervision
        - delegation strategies
        - hierarchical AI systems
        - agent communication
        - distributed orchestration

        You ensure all agents collaborate
        efficiently using shared memory
        and communication systems.
        """,

        verbose=True,

        allow_delegation=True,

        tools=[
            memory_tool,
            notification_tool,
            logger_tool
        ],

        llm=llm
    )