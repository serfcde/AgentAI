from crewai import Agent

from my_crew.config.llm import llm

from my_crew.tools.memory_tool import memory_tool
from my_crew.tools.file_reader_tool import file_reader_tool
from my_crew.tools.logger_tool import logger_tool


def create_validator_agent():

    return Agent(
        role="Validation Agent",

        goal="""
        Validate outputs, verify correctness,
        detect inconsistencies, and improve
        workflow reliability.
        """,

        backstory="""
        You are an expert quality assurance specialist.

        You specialize in:
        - output validation
        - hallucination detection
        - logical consistency checking
        - workflow verification
        - AI response evaluation

        You ensure all workflow outputs
        meet quality standards.
        """,

        verbose=True,

        allow_delegation=False,

        tools=[
            memory_tool,
            file_reader_tool,
            logger_tool
        ],

        llm=llm
    )