from crewai import Agent
from my_crew.config.llm import llm


def create_planner_agent():
    return Agent(
        role="Planning Agent",

        goal="""
        Break large objectives into structured,
        executable step-by-step plans.
        """,

        backstory="""
        You are an expert strategic planner.

        You specialize in:
        - task decomposition
        - workflow orchestration
        - execution pipelines
        - multi-agent coordination
        - scalable AI systems

        You create highly optimized execution plans.
        """,

        verbose=True,

        allow_delegation=False,

        llm=llm
    )