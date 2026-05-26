from crewai import Agent
from my_crew.config.llm import llm


def create_executor_agent():
    return Agent(
        role="Execution Agent",

        goal="""
        Execute assigned tasks efficiently
        and produce actionable outputs.
        """,

        backstory="""
        You are an expert execution specialist.

        You specialize in:
        - task execution
        - workflow completion
        - implementation
        - operational efficiency
        - action-oriented problem solving

        You focus on completing tasks accurately and efficiently.
        """,

        verbose=True,

        allow_delegation=False,

        llm=llm
    )