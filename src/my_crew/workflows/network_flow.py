from crewai import Crew, Process

from my_crew.a2a.communication import CommunicationBus

from my_crew.agents.researcher import create_research_agent
from my_crew.agents.planner import create_planner_agent
from my_crew.agents.executor import create_executor_agent
from my_crew.agents.validator import create_validator_agent

from my_crew.tasks.research_task import create_research_task
from my_crew.tasks.planning_task import create_planning_task
from my_crew.tasks.execution_task import create_execution_task
from my_crew.tasks.validation_task import create_validation_task


def execute_agent(agent, task):

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True
    )

    result = crew.kickoff()

    return result


def run_network_flow():

    topic = "Future of AI Agents"

    bus = CommunicationBus()

    # -------------------------
    # Research Phase
    # -------------------------

    research_agent = create_research_agent()

    research_task = create_research_task(
        research_agent,
        topic
    )

    research_result = execute_agent(
        research_agent,
        research_task
    )

    bus.send_message(
        "Research Agent",
        "Planning Agent",
        str(research_result)
    )

    # -------------------------
    # Planning Phase
    # -------------------------

    planning_agent = create_planner_agent()

    planning_task = create_planning_task(
        planning_agent,
        topic,
        context=str(research_result)
    )

    planning_result = execute_agent(
        planning_agent,
        planning_task
    )

    bus.send_message(
        "Planning Agent",
        "Execution Agent",
        str(planning_result)
    )

    # -------------------------
    # Execution Phase
    # -------------------------

    executor_agent = create_executor_agent()

    execution_task = create_execution_task(
        executor_agent,
        topic,
        context=str(planning_result)
    )

    execution_result = execute_agent(
        executor_agent,
        execution_task
    )

    bus.send_message(
        "Execution Agent",
        "Validation Agent",
        str(execution_result)
    )

    # -------------------------
    # Validation Phase
    # -------------------------

    validator_agent = create_validator_agent()

    validation_task = create_validation_task(
        validator_agent,
        topic,
        context=str(execution_result)
    )

    validation_result = execute_agent(
        validator_agent,
        validation_task
    )
    if "improvement" in str(validation_result).lower():
        print("\nValidation requested improvements. Re-running the network pipeline...\n")

        # 1. Re-run Research with Validator Feedback injected as context
        # (Assuming your task creator accepts a context string)
        revised_research_task = create_research_task(
            research_agent,
            f"{topic}\n\nFix these issues from the validator:\n{validation_result}"
        )
        research_result = execute_agent(research_agent, revised_research_task)
        bus.send_message("Research Agent", "Planning Agent", f"Revised Research:\n{research_result}")

        # 2. MUST RE-RUN PLANNER
        planning_task = create_planning_task(
            planning_agent,
            topic,
            context=str(research_result)
        )
        planning_result = execute_agent(planning_agent, planning_task)
        bus.send_message("Planning Agent", "Execution Agent", f"Revised Plan:\n{planning_result}")

        # 3. MUST RE-RUN EXECUTOR TO GENERATE THE NEW REPORT
        execution_task = create_execution_task(
            executor_agent,
            topic,
            context=str(planning_result)
        )
        execution_result = execute_agent(executor_agent, execution_task)
        bus.send_message("Execution Agent", "Validation Agent", f"Revised Execution:\n{execution_result}")

        # 4. MUST RE-RUN VALIDATOR FOR FINAL APPROVAL
        validation_task = create_validation_task(
            validator_agent,
            topic,
            context=str(execution_result)
        )
        validation_result = execute_agent(validator_agent, validation_task)


    bus.send_message(
        "Validation Agent",
        "Research Agent",
        str(validation_result)
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
VALIDATION RESULT
==============================

{validation_result}

"""

    return final_result