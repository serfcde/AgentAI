from concurrent.futures import ThreadPoolExecutor

from crewai import Crew, Process

from my_crew.a2a.message import MessageKind, TaskState
from my_crew.agents.researcher import create_research_agent
from my_crew.agents.planner import create_planner_agent
from my_crew.agents.executor import create_executor_agent

from my_crew.tasks.research_task import create_research_task
from my_crew.tasks.planning_task import create_planning_task
from my_crew.tasks.execution_task import create_execution_task
from my_crew.workflows.network_flow import create_network_bus, inbox_context


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
    bus, workflow_task = create_network_bus(topic)
    bus.update_task_status(
        workflow_task.id,
        TaskState.TASK_STATE_WORKING,
        sender="Supervisor Agent",
        content="Parallel workflow started.",
    )

    with ThreadPoolExecutor() as executor:

        research_future = executor.submit(
            run_research_flow,
            topic
        )

        planning_future = executor.submit(
            run_planning_flow,
            topic
        )

        research_result = research_future.result()
        bus.send_message(
            "Research Agent",
            "Execution Agent",
            str(research_result),
            kind=MessageKind.TASK_RESPONSE,
            task_id=workflow_task.id,
            metadata={"phase": "parallel_research"},
        )

        planning_result = planning_future.result()
        bus.send_message(
            "Planning Agent",
            "Execution Agent",
            str(planning_result),
            kind=MessageKind.TASK_RESPONSE,
            task_id=workflow_task.id,
            metadata={"phase": "parallel_planning"},
        )

    execution_result = run_execution_flow(
        f"""
        Topic: {topic}

        A2A Context:
        {inbox_context(bus, "Execution Agent")}
        """
    )
    bus.send_message(
        "Execution Agent",
        "Supervisor Agent",
        str(execution_result),
        kind=MessageKind.TASK_RESPONSE,
        task_id=workflow_task.id,
        metadata={"phase": "parallel_execution"},
    )
    bus.update_task_status(
        workflow_task.id,
        TaskState.TASK_STATE_COMPLETED,
        sender="Supervisor Agent",
        content="Parallel workflow completed.",
    )

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


==============================
A2A TASK SNAPSHOT
==============================

{bus.task_snapshot()}


==============================
A2A MESSAGE COUNT
==============================

{len(bus.get_messages())}

"""

    return final_result
