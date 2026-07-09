import json

import pytest

from my_crew.a2a.communication import CommunicationBus
from my_crew.a2a.message import AgentCard, TaskStatus
from my_crew.agents.supervisor_controller import (
    SupervisorAction,
    SupervisorController,
)


AGENT_NAMES = [
    "Supervisor Agent",
    "Research Agent",
    "Planning Agent",
    "Execution Agent",
    "Validation Agent",
]

GOOD_OUTPUT = (
    "This is a thorough, well-structured phase output with plenty of detail "
    "about the topic, covering findings, sources, and clear recommendations "
    "for the downstream agents to act on."
)


def make_controller(**kwargs) -> SupervisorController:
    bus = CommunicationBus()
    for name in AGENT_NAMES:
        bus.register_agent(AgentCard(agent_id=name, name=name, description=name))
    task = bus.create_task("test workflow", "Supervisor Agent")
    return SupervisorController(
        bus=bus,
        task_id=task.task_id,
        max_retries_per_phase=1,
        **kwargs,
    )


def judge_returning(payload: dict):
    return lambda prompt: json.dumps(payload)


class TestHeuristicDecisions:
    def test_good_output_continues(self):
        controller = make_controller()
        decision = controller.evaluate_phase_output(
            "research", GOOD_OUTPUT, "planning", "Planning Agent"
        )
        assert decision.action == SupervisorAction.CONTINUE
        assert decision.next_phase == "planning"
        assert decision.target_agent == "Planning Agent"

    def test_short_output_retries_then_fails(self):
        controller = make_controller()
        first = controller.evaluate_phase_output(
            "research", "too short", "planning", "Planning Agent"
        )
        assert first.action == SupervisorAction.RETRY
        assert first.next_phase == "research"
        assert first.retry_count == 1

        second = controller.evaluate_phase_output(
            "research", "too short", "planning", "Planning Agent"
        )
        assert second.action == SupervisorAction.FAIL

    def test_failure_marker_triggers_retry(self):
        controller = make_controller()
        output = "Error: something went wrong while researching. " * 5
        decision = controller.evaluate_phase_output(
            "research", output, "planning", "Planning Agent"
        )
        assert decision.action == SupervisorAction.RETRY

    def test_failed_execution_reassigns_to_planning(self):
        controller = make_controller()
        output = "Traceback (most recent call last): execution blew up. " * 5
        decision = controller.evaluate_phase_output(
            "execution", output, "validation", "Validation Agent"
        )
        assert decision.action == SupervisorAction.REASSIGN
        assert decision.next_phase == "planning"
        assert decision.target_agent == "Planning Agent"

    def test_clean_validation_completes(self):
        controller = make_controller()
        decision = controller.evaluate_phase_output(
            "validation", GOOD_OUTPUT, None, None
        )
        assert decision.action == SupervisorAction.COMPLETE

    def test_validation_improvement_restarts_then_fails(self):
        controller = make_controller()
        output = "The result needs improvement in scope and completeness. " * 5

        first = controller.evaluate_phase_output("validation", output, None, None)
        assert first.action == SupervisorAction.RETRY
        assert first.next_phase == "research"

        second = controller.evaluate_phase_output("validation", output, None, None)
        assert second.action == SupervisorAction.FAIL


class TestLLMReview:
    def test_llm_pass_continues(self):
        controller = make_controller(
            llm_judge=judge_returning(
                {"verdict": "pass", "needs_improvement": False, "feedback": "Solid."}
            )
        )
        decision = controller.evaluate_phase_output(
            "research", GOOD_OUTPUT, "planning", "Planning Agent"
        )
        assert decision.action == SupervisorAction.CONTINUE
        assert decision.metadata["review"] == "llm"

    def test_llm_fail_retries(self):
        controller = make_controller(
            llm_judge=judge_returning(
                {"verdict": "fail", "needs_improvement": True, "feedback": "Off-topic."}
            )
        )
        decision = controller.evaluate_phase_output(
            "research", GOOD_OUTPUT, "planning", "Planning Agent"
        )
        assert decision.action == SupervisorAction.RETRY
        assert "Off-topic." in decision.reason

    def test_llm_fail_on_execution_reassigns(self):
        controller = make_controller(
            llm_judge=judge_returning(
                {"verdict": "fail", "needs_improvement": True, "feedback": "Broken."}
            )
        )
        decision = controller.evaluate_phase_output(
            "execution", GOOD_OUTPUT, "validation", "Validation Agent"
        )
        assert decision.action == SupervisorAction.REASSIGN
        assert decision.next_phase == "planning"

    def test_llm_improvement_request_retries(self):
        controller = make_controller(
            llm_judge=judge_returning(
                {"verdict": "pass", "needs_improvement": True, "feedback": "Add depth."}
            )
        )
        decision = controller.evaluate_phase_output(
            "planning", GOOD_OUTPUT, "execution", "Execution Agent"
        )
        assert decision.action == SupervisorAction.RETRY

    def test_llm_approves_validation_completes(self):
        controller = make_controller(
            llm_judge=judge_returning(
                {"verdict": "pass", "needs_improvement": False, "feedback": "Done."}
            )
        )
        decision = controller.evaluate_phase_output(
            "validation", GOOD_OUTPUT, None, None
        )
        assert decision.action == SupervisorAction.COMPLETE

    def test_unparseable_llm_output_falls_back_to_heuristics(self):
        controller = make_controller(llm_judge=lambda prompt: "not json at all")
        decision = controller.evaluate_phase_output(
            "research", GOOD_OUTPUT, "planning", "Planning Agent"
        )
        assert decision.action == SupervisorAction.CONTINUE
        assert "review" not in decision.metadata

    def test_llm_exception_falls_back_to_heuristics(self):
        def broken_judge(prompt: str) -> str:
            raise ConnectionError("Ollama is down")

        controller = make_controller(llm_judge=broken_judge)
        decision = controller.evaluate_phase_output(
            "research", GOOD_OUTPUT, "planning", "Planning Agent"
        )
        assert decision.action == SupervisorAction.CONTINUE


class TestDecisionRecording:
    def test_record_decision_updates_bus_and_snapshot(self):
        controller = make_controller()
        decision = controller.evaluate_phase_output(
            "research", GOOD_OUTPUT, "planning", "Planning Agent"
        )
        controller.record_decision(decision)

        snapshot = controller.decision_snapshot()
        assert len(snapshot) == 1
        assert snapshot[0]["action"] == "continue"
        assert snapshot[0]["phase"] == "research"

    def test_should_continue(self):
        controller = make_controller()
        decision = controller.evaluate_phase_output(
            "research", GOOD_OUTPUT, "planning", "Planning Agent"
        )
        assert controller.should_continue(decision)

    def test_start_phase_marks_task_working(self):
        controller = make_controller()
        controller.start_phase("research", "Research Agent")
        task = controller.bus.get_task(controller.task_id)
        assert task.status == TaskStatus.WORKING
