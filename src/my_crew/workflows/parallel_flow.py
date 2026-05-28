from concurrent.futures import ThreadPoolExecutor

from crewai import Crew, Process

from my_crew.agents.researcher import create_research_agent
from my_crew.agents.planner import create_planner_agent
from my_crew.agents.executor import create_executor_agent

from my_crew.tasks.research_task import create_research_task
from my_crew.tasks.planning_task import create_planning_task
from my_crew.tasks.execution_task import create_execution_task


def run_research_flow(topic):

    agent = create_research_agent()

    task = create_research_task(agent, topic)

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True
    )

    return crew.kickoff()


def run_planning_flow(topic):

    agent = create_planner_agent()

    task = create_planning_task(agent, topic)

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True
    )

    return crew.kickoff()


def run_execution_flow(topic):

    agent = create_executor_agent()

    task = create_execution_task(agent, topic)

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True
    )

    return crew.kickoff()


def run_parallel_flow(topic):

    with ThreadPoolExecutor() as executor:

        research_future = executor.submit(
            run_research_flow,
            topic
        )

        planning_future = executor.submit(
            run_planning_flow,
            topic
        )

        execution_future = executor.submit(
            run_execution_flow,
            topic
        )

        research_result = research_future.result()

        planning_result = planning_future.result()

        execution_result = execution_future.result()

    final_result = f"""

==============================
RESEARCH RESULT
==============================

{research_result}


==============================
PLANNING RESULT
==============================

{planning_result}


==============================
EXECUTION RESULT
==============================

{execution_result}

"""

    return final_result