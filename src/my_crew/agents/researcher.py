from crewai import Agent
from my_crew.config.llm import llm


def create_research_agent():
    return Agent(
        role="Research Agent",

        goal="""
        Research AI topics, gather insights,
        analyze trends, and provide accurate findings.
        """,

        backstory="""
        You are an expert AI researcher specializing in:
        - AI agents
        - Multi-agent systems
        - AI orchestration
        - Local LLMs
        - Agentic workflows

        You provide highly structured and accurate research.
        """,

        verbose=True,

        allow_delegation=False,

        llm=llm
    )