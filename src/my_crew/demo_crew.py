"""Manual demo: run all five agents as a single sequential crew.

Requires a running Ollama instance. Run with:
    PYTHONPATH=src python -m my_crew.demo_crew
"""

from crewai import Task, Crew

from my_crew.agents.researcher import create_research_agent
from my_crew.agents.planner import create_planner_agent
from my_crew.agents.executor import create_executor_agent
from my_crew.agents.validator import create_validator_agent
from my_crew.agents.supervisor import create_supervisor_agent


def build_demo_crew() -> Crew:
    research_agent = create_research_agent()
    planner_agent = create_planner_agent()
    executor_agent = create_executor_agent()
    validator_agent = create_validator_agent()
    supervisor_agent = create_supervisor_agent()

    research_task = Task(
        description="Research the benefits of multi-agent AI systems.",
        expected_output="A structured summary of multi-agent AI systems.",
        agent=research_agent,
    )

    planning_task = Task(
        description="Create an execution plan based on the research findings.",
        expected_output="A step-by-step workflow plan.",
        agent=planner_agent,
    )

    execution_task = Task(
        description="Execute the proposed workflow plan.",
        expected_output="Execution summary and operational steps.",
        agent=executor_agent,
    )

    validation_task = Task(
        description="Validate the execution results and identify issues.",
        expected_output="Validation report with improvements.",
        agent=validator_agent,
    )

    return Crew(
        agents=[
            supervisor_agent,
            research_agent,
            planner_agent,
            executor_agent,
            validator_agent,
        ],
        tasks=[
            research_task,
            planning_task,
            execution_task,
            validation_task,
        ],
        verbose=True,
    )


def main() -> None:
    result = build_demo_crew().kickoff()
    print("\nFINAL RESULT:\n")
    print(result)


if __name__ == "__main__":
    main()
