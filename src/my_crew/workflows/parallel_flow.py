from concurrent.futures import ThreadPoolExecutor

from crewai import Crew, Process

from my_crew.a2a.message import MessageKind, TaskState
from my_crew.agents.executor import create_executor_agent
from my_crew.agents.llm_judge import get_default_llm_caller
from my_crew.agents.planner import create_planner_agent
from my_crew.agents.researcher import create_research_agent
from my_crew.agents.supervisor_controller import (
    SupervisorAction,
    SupervisorController,
)
from my_crew.tasks.execution_task import create_execution_task
from my_crew.tasks.planning_task import create_planning_task
from my_crew.tasks.research_task import create_research_task
from my_crew.workflows.network_flow import create_network_bus, inbox_context


def run_research_flow(topic):
    agent = create_research_agent()
    task = create_research_task(agent, topic)

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    return crew.kickoff()


def run_planning_flow(topic):
    agent = create_planner_agent()
    task = create_planning_task(agent, topic)

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    return crew.kickoff()


def run_execution_flow(topic):
    agent = create_executor_agent()
    task = create_execution_task(agent, topic)

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    return crew.kickoff()


def review_parallel_phase(
    supervisor: SupervisorController,
    phase: str,
    result,
    runner,
    topic: str,
):
    """Supervisor-review a parallel phase output, retrying once on rejection."""
    decision = supervisor.evaluate_phase_output(
        phase=phase,
        output=str(result),
        default_next_phase="execution",
        target_agent="Execution Agent",
    )
    supervisor.record_decision(decision)

    if decision.action in {SupervisorAction.RETRY, SupervisorAction.REASSIGN}:
        retry_topic = (
            f"{topic}\n\n"
            f"Supervisor feedback on the previous {phase} attempt: "
            f"{decision.reason}"
        )
        result = runner(retry_topic)
        retry_decision = supervisor.evaluate_phase_output(
            phase=phase,
            output=str(result),
            default_next_phase="execution",
            target_agent="Execution Agent",
        )
        supervisor.record_decision(retry_decision)

    return result


def run_parallel_flow(topic, phase_runners=None):
    runners = phase_runners or {
        "research": run_research_flow,
        "planning": run_planning_flow,
        "execution": run_execution_flow,
    }

    bus, workflow_task = create_network_bus(topic)
    supervisor = SupervisorController(
        bus=bus,
        task_id=workflow_task.id,
        max_retries_per_phase=1,
        topic=topic,
        llm_judge=get_default_llm_caller("MY_CREW_LLM_SUPERVISOR"),
    )
    bus.update_task_status(
        workflow_task.id,
        TaskState.TASK_STATE_WORKING,
        sender="Supervisor Agent",
        content="Parallel workflow started.",
    )

    with ThreadPoolExecutor() as executor:
        research_future = executor.submit(runners["research"], topic)
        planning_future = executor.submit(runners["planning"], topic)

        research_result = research_future.result()
        planning_result = planning_future.result()

    research_result = review_parallel_phase(
        supervisor, "research", research_result, runners["research"], topic
    )
    bus.send_message(
        "Research Agent",
        "Execution Agent",
        str(research_result),
        kind=MessageKind.TASK_RESPONSE,
        task_id=workflow_task.id,
        metadata={"phase": "parallel_research"},
    )

    planning_result = review_parallel_phase(
        supervisor, "planning", planning_result, runners["planning"], topic
    )
    bus.send_message(
        "Planning Agent",
        "Execution Agent",
        str(planning_result),
        kind=MessageKind.TASK_RESPONSE,
        task_id=workflow_task.id,
        metadata={"phase": "parallel_planning"},
    )

    execution_result = runners["execution"](
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
SUPERVISOR DECISIONS
==============================

{supervisor.decision_snapshot()}


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
