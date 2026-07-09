from crewai import Crew, Process

from my_crew.agents.executor import create_executor_agent
from my_crew.agents.planner import create_planner_agent
from my_crew.agents.researcher import create_research_agent
from my_crew.agents.supervisor import create_supervisor_agent
from my_crew.agents.validator import create_validator_agent
from my_crew.config.llm import llm
from my_crew.tasks.execution_task import create_execution_task
from my_crew.tasks.planning_task import create_planning_task
from my_crew.tasks.research_task import create_research_task
from my_crew.tasks.validation_task import create_validation_task


def create_ai_crew(topic: str):

    # -------------------------
    # Create Agents
    # -------------------------

    research_agent = create_research_agent()

    planner_agent = create_planner_agent()

    executor_agent = create_executor_agent()

    validator_agent = create_validator_agent()

    supervisor_agent = create_supervisor_agent()

    # -------------------------
    # Create Tasks
    # -------------------------

    research_task = create_research_task(
        research_agent,
        topic
    )

    planning_task = create_planning_task(
        planner_agent,
        topic
    )

    execution_task = create_execution_task(
        executor_agent,
        topic
    )

    validation_task = create_validation_task(
        validator_agent,
        topic
    )

    # -------------------------
    # Create Crew
    # -------------------------

    crew = Crew(
        agents=[
            research_agent,
            planner_agent,
            executor_agent,
            validator_agent,
        ],

        tasks=[
            research_task,
            planning_task,
            execution_task,
            validation_task
        ],

        process=Process.hierarchical,
        manager_llm=llm,
        manager_agent=supervisor_agent,

        verbose=True
    )

    return crew
