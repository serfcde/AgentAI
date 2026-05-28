from crewai import Agent

from my_crew.config.llm import llm

from my_crew.tools.web_search_tool import web_search_tool
from my_crew.tools.file_reader_tool import file_reader_tool
from my_crew.tools.memory_tool import memory_tool
from my_crew.tools.logger_tool import logger_tool


def create_research_agent():

    return Agent(
        role="Research Agent",

        goal="""
        Research AI topics, gather insights,
        analyze trends, and provide accurate findings
        for downstream agents.
        """,

        backstory="""
        You are an expert AI researcher specializing in:
        - AI agents
        - Multi-agent systems
        - AI orchestration
        - Local LLMs
        - Agentic workflows

        You collaborate with other agents
        using shared workflow memory and
        communication systems.
        """,

        verbose=True,

        allow_delegation=False,

        tools=[
            web_search_tool,
            file_reader_tool,
            memory_tool,
            logger_tool
        ],

        llm=llm
    )