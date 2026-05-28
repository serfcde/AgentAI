from crewai import Agent

from my_crew.config.llm import llm

from my_crew.tools.calculator_tool import calculator_tool
from my_crew.tools.memory_tool import memory_tool
from my_crew.tools.notification_tool import notification_tool
from my_crew.tools.logger_tool import logger_tool


def create_executor_agent():

    return Agent(
        role="Execution Agent",

        goal="""
        Execute assigned tasks efficiently
        and generate actionable outputs.
        """,

        backstory="""
        You are an expert execution specialist.

        You specialize in:
        - task execution
        - workflow completion
        - implementation
        - operational efficiency
        - action-oriented problem solving

        You execute tasks using workflow context,
        memory systems, and orchestration tools.
        """,

        verbose=True,

        allow_delegation=False,

        tools=[
            calculator_tool,
            memory_tool,
            notification_tool,
            logger_tool
        ],

        llm=llm
    )