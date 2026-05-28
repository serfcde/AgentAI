from crewai import Agent

from my_crew.config.llm import llm

from my_crew.tools.memory_tool import memory_tool
from my_crew.tools.logger_tool import logger_tool


def create_planner_agent():

    return Agent(
        role="Planning Agent",

        goal="""
        Break large objectives into structured,
        executable workflows and coordinate
        task planning across agents.
        """,

        backstory="""
        You are an expert strategic planner.

        You specialize in:
        - workflow orchestration
        - task decomposition
        - multi-agent coordination
        - scalable AI systems
        - execution planning

        You create optimized execution plans
        using shared workflow memory.
        """,

        verbose=True,

        allow_delegation=True,

        tools=[
            memory_tool,
            logger_tool
        ],

        llm=llm
    )