from crewai import Crew, Process

from my_crew.a2a.communication import CommunicationBus
from my_crew.a2a.message import AgentCapability, AgentCard, MessageType, TaskStatus

from my_crew.agents.llm_judge import get_default_llm_caller
from my_crew.agents.researcher import create_research_agent
from my_crew.agents.planner import create_planner_agent
from my_crew.agents.executor import create_executor_agent
from my_crew.agents.supervisor_controller import (
    SupervisorAction,
    SupervisorController,
)
from my_crew.agents.validator import create_validator_agent

from my_crew.tasks.research_task import create_research_task
from my_crew.tasks.planning_task import create_planning_task
from my_crew.tasks.execution_task import create_execution_task
from my_crew.tasks.validation_task import create_validation_task


def build_agent_cards():
    return [
        AgentCard(
            agent_id="Supervisor Agent",
            name="Supervisor Agent",
            description="Coordinates workflow routing, lifecycle, and delegation.",
            endpoint="local://agents/supervisor",
            capabilities=[
                AgentCapability(
                    name="supervision",
                    description="Coordinate agents and monitor workflow status.",
                )
            ],
        ),
        AgentCard(
            agent_id="Research Agent",
            name="Research Agent",
            description="Researches topics and prepares structured findings.",
            endpoint="local://agents/research",
            capabilities=[
                AgentCapability(
                    name="research",
                    description="Gather and summarize research context.",
                    streaming=True,
                )
            ],
        ),
        AgentCard(
            agent_id="Planning Agent",
            name="Planning Agent",
            description="Turns research into phased execution plans.",
            endpoint="local://agents/planning",
            capabilities=[
                AgentCapability(
                    name="planning",
                    description="Create execution plans with dependencies.",
                )
            ],
        ),
        AgentCard(
            agent_id="Execution Agent",
            name="Execution Agent",
            description="Produces implementation guidance and action steps.",
            endpoint="local://agents/execution",
            capabilities=[
                AgentCapability(
                    name="execution",
                    description="Execute plans and produce operational output.",
                )
            ],
        ),
        AgentCard(
            agent_id="Validation Agent",
            name="Validation Agent",
            description="Reviews workflow output for quality and completeness.",
            endpoint="local://agents/validation",
            capabilities=[
                AgentCapability(
                    name="validation",
                    description="Validate outputs and recommend improvements.",
                )
            ],
        ),
    ]


def create_network_bus(topic: str):
    bus = CommunicationBus()
    for card in build_agent_cards():
        bus.register_agent(card)

    workflow_task = bus.create_task(
        title=f"Network workflow: {topic}",
        owner="Supervisor Agent",
        metadata={"workflow": "network", "topic": topic},
    )
    bus.broadcast(
        sender="Supervisor Agent",
        content=f"Network workflow started for topic: {topic}",
        task_id=workflow_task.task_id,
    )
    return bus, workflow_task


def inbox_context(bus: CommunicationBus, agent_id: str) -> str:
    messages = bus.receive_messages(agent_id)
    return "\n\n".join(
        message.content
        for message in messages
        if message.message_type == MessageType.TASK_RESPONSE
    )


def execute_agent(agent, task):

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True
    )

    result = crew.kickoff()

    return result


def run_network_flow(topic):
    bus, workflow_task = create_network_bus(topic)
    supervisor = SupervisorController(
        bus=bus,
        task_id=workflow_task.task_id,
        max_retries_per_phase=1,
        topic=topic,
        llm_judge=get_default_llm_caller("MY_CREW_LLM_SUPERVISOR"),
    )

    agents = {
        "research": create_research_agent(),
        "planning": create_planner_agent(),
        "execution": create_executor_agent(),
        "validation": create_validator_agent(),
    }

    phase_order = {
        "research": {
            "agent_id": "Research Agent",
            "next_phase": "planning",
            "next_agent": "Planning Agent",
        },
        "planning": {
            "agent_id": "Planning Agent",
            "next_phase": "execution",
            "next_agent": "Execution Agent",
        },
        "execution": {
            "agent_id": "Execution Agent",
            "next_phase": "validation",
            "next_agent": "Validation Agent",
        },
        "validation": {
            "agent_id": "Validation Agent",
            "next_phase": None,
            "next_agent": None,
        },
    }

    results = {
        "research": "",
        "planning": "",
        "execution": "",
        "validation": "",
    }
    supervisor_feedback = ""
    current_phase = "research"

    while current_phase:
        phase_config = phase_order[current_phase]
        agent_id = phase_config["agent_id"]
        supervisor.start_phase(current_phase, agent_id)

        result = execute_workflow_phase(
            phase=current_phase,
            agent=agents[current_phase],
            topic=topic,
            bus=bus,
            supervisor_feedback=supervisor_feedback,
        )
        results[current_phase] = str(result)

        bus.send_message(
            agent_id,
            "Supervisor Agent",
            str(result),
            message_type=MessageType.TASK_RESPONSE,
            task_id=workflow_task.task_id,
            status=TaskStatus.WORKING,
            metadata={"phase": current_phase, "handoff": "supervisor_review"},
        )

        decision = supervisor.evaluate_phase_output(
            phase=current_phase,
            output=str(result),
            default_next_phase=phase_config["next_phase"],
            target_agent=phase_config["next_agent"],
        )
        supervisor.record_decision(decision)

        if decision.action == SupervisorAction.COMPLETE:
            bus.update_task_status(
                workflow_task.task_id,
                TaskStatus.COMPLETED,
                sender="Supervisor Agent",
                content="Network workflow completed.",
            )
            break

        if decision.action == SupervisorAction.FAIL:
            bus.update_task_status(
                workflow_task.task_id,
                TaskStatus.FAILED,
                sender="Supervisor Agent",
                content=decision.reason,
            )
            break

        if decision.action == SupervisorAction.CONTINUE:
            bus.send_message(
                agent_id,
                decision.target_agent,
                str(result),
                message_type=MessageType.TASK_RESPONSE,
                task_id=workflow_task.task_id,
                status=TaskStatus.WORKING,
                metadata={"phase": current_phase, "handoff": "approved"},
            )
            supervisor_feedback = ""
            current_phase = decision.next_phase
            continue

        if decision.action in {
            SupervisorAction.RETRY,
            SupervisorAction.REASSIGN,
        }:
            supervisor_feedback = (
                f"Supervisor decision: {decision.action.value}. "
                f"Reason: {decision.reason}\n\n"
                f"Previous {current_phase} output:\n{truncate_context(str(result))}"
            )
            current_phase = decision.next_phase
            continue

    final_result = f"""

==============================
RESEARCH RESULT
==============================

{results["research"]}


==============================
PLANNING RESULT
==============================

{results["planning"]}


==============================
EXECUTION RESULT
==============================

{results["execution"]}


==============================
VALIDATION RESULT
==============================

{results["validation"]}


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


def execute_workflow_phase(
    phase: str,
    agent,
    topic: str,
    bus: CommunicationBus,
    supervisor_feedback: str = "",
):
    if phase == "research":
        research_topic = topic
        if supervisor_feedback:
            research_topic = f"{topic}\n\n{supervisor_feedback}"
        return execute_agent(agent, create_research_task(agent, research_topic))

    if phase == "planning":
        context = join_context(
            inbox_context(bus, "Planning Agent"),
            supervisor_feedback,
        )
        return execute_agent(
            agent,
            create_planning_task(agent, topic, context=context),
        )

    if phase == "execution":
        context = join_context(
            inbox_context(bus, "Execution Agent"),
            supervisor_feedback,
        )
        return execute_agent(
            agent,
            create_execution_task(agent, topic, context=context),
        )

    if phase == "validation":
        context = join_context(
            inbox_context(bus, "Validation Agent"),
            supervisor_feedback,
        )
        return execute_agent(
            agent,
            create_validation_task(agent, topic, context=context),
        )

    raise ValueError(f"Unsupported workflow phase: {phase}")


def join_context(*parts: str) -> str:
    return "\n\n".join(part for part in parts if part)


def truncate_context(content: str, limit: int = 2000) -> str:
    if len(content) <= limit:
        return content
    return f"{content[:limit]}\n\n[truncated by supervisor]"
