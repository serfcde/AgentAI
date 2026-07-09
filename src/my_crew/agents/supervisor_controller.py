from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from my_crew.a2a.communication import CommunicationBus
from my_crew.a2a.message import MessageKind, TaskState
from my_crew.agents.llm_judge import LLMCaller, review_phase_output


class SupervisorAction(str, Enum):
    CONTINUE = "continue"
    RETRY = "retry"
    REASSIGN = "reassign"
    COMPLETE = "complete"
    FAIL = "fail"


@dataclass(frozen=True)
class SupervisorDecision:
    action: SupervisorAction
    phase: str
    reason: str
    next_phase: str | None = None
    target_agent: str | None = None
    retry_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_message(self) -> str:
        return (
            f"action={self.action.value}; phase={self.phase}; "
            f"next_phase={self.next_phase}; target_agent={self.target_agent}; "
            f"retry_count={self.retry_count}; reason={self.reason}"
        )


class SupervisorController:
    """Deterministic orchestration controller for workflow supervision."""

    phase_agents = {
        "research": "Research Agent",
        "planning": "Planning Agent",
        "execution": "Execution Agent",
        "validation": "Validation Agent",
    }

    def __init__(
        self,
        bus: CommunicationBus,
        task_id: str,
        max_retries_per_phase: int = 1,
        min_output_chars: int = 120,
        topic: str = "",
        llm_judge: LLMCaller | None = None,
    ):
        self.bus = bus
        self.task_id = task_id
        self.max_retries_per_phase = max_retries_per_phase
        self.min_output_chars = min_output_chars
        self.topic = topic
        self.llm_judge = llm_judge
        self.retry_counts: dict[str, int] = {}
        self.decisions: list[SupervisorDecision] = []

    def start_phase(self, phase: str, agent_id: str) -> None:
        self.bus.update_task_status(
            self.task_id,
            TaskState.TASK_STATE_WORKING,
            sender="Supervisor Agent",
            content=f"Starting phase '{phase}' with {agent_id}.",
        )

    def evaluate_phase_output(
        self,
        phase: str,
        output: str,
        default_next_phase: str | None,
        target_agent: str | None,
    ) -> SupervisorDecision:
        if len(output.strip()) < self.min_output_chars:
            return self._retry_or_fail(
                phase=phase,
                reason="Output is too short to satisfy completion criteria.",
                target_agent=target_agent,
            )

        review = review_phase_output(phase, self.topic, output, self.llm_judge)
        if review is not None:
            return self._decision_from_review(
                review=review,
                phase=phase,
                default_next_phase=default_next_phase,
                target_agent=target_agent,
            )

        return self._heuristic_decision(
            phase=phase,
            output=output,
            default_next_phase=default_next_phase,
            target_agent=target_agent,
        )

    def _heuristic_decision(
        self,
        phase: str,
        output: str,
        default_next_phase: str | None,
        target_agent: str | None,
    ) -> SupervisorDecision:
        normalized = output.lower()

        if self._looks_failed(normalized):
            if phase == "execution":
                return self._reassign_or_fail(
                    phase=phase,
                    reason="Execution output failed; reassigning to planning for repair.",
                    next_phase="planning",
                    target_agent="Planning Agent",
                )

            return self._retry_or_fail(
                phase=phase,
                reason="Output contains an error/failure signal.",
                target_agent=target_agent,
            )

        if phase == "validation":
            return self._evaluate_validation(normalized)

        return SupervisorDecision(
            action=SupervisorAction.CONTINUE,
            phase=phase,
            reason="Output passed supervisor quality checks.",
            next_phase=default_next_phase,
            target_agent=target_agent,
            retry_count=self.retry_counts.get(phase, 0),
        )

    def _decision_from_review(
        self,
        review: dict[str, Any],
        phase: str,
        default_next_phase: str | None,
        target_agent: str | None,
    ) -> SupervisorDecision:
        feedback = review["feedback"] or "No feedback provided."

        if review["verdict"] == "fail":
            if phase == "execution":
                return self._reassign_or_fail(
                    phase=phase,
                    reason=f"LLM review failed execution output: {feedback}",
                    next_phase="planning",
                    target_agent="Planning Agent",
                )

            return self._retry_or_fail(
                phase=phase,
                reason=f"LLM review rejected the output: {feedback}",
                target_agent=target_agent,
            )

        if phase == "validation":
            if review["needs_improvement"]:
                return self._validation_improvement_decision(
                    f"LLM review requested improvements: {feedback}"
                )

            return SupervisorDecision(
                action=SupervisorAction.COMPLETE,
                phase=phase,
                reason=f"LLM review approved the final output: {feedback}",
                retry_count=self.retry_counts.get("validation_loop", 0),
                metadata={"review": "llm"},
            )

        if review["needs_improvement"]:
            return self._retry_or_fail(
                phase=phase,
                reason=f"LLM review requested improvements: {feedback}",
                target_agent=target_agent,
            )

        return SupervisorDecision(
            action=SupervisorAction.CONTINUE,
            phase=phase,
            reason=f"LLM review passed the output: {feedback}",
            next_phase=default_next_phase,
            target_agent=target_agent,
            retry_count=self.retry_counts.get(phase, 0),
            metadata={"review": "llm"},
        )

    def record_decision(self, decision: SupervisorDecision) -> None:
        self.decisions.append(decision)

        self.bus.send_message(
            sender="Supervisor Agent",
            receiver=decision.target_agent or CommunicationBus.BROADCAST,
            content=decision.to_message(),
            kind=MessageKind.STATUS_UPDATE,
            task_id=self.task_id,
            metadata={
                "phase": decision.phase,
                "action": decision.action.value,
                **decision.metadata,
            },
        )

    def should_continue(self, decision: SupervisorDecision) -> bool:
        return decision.action in {
            SupervisorAction.CONTINUE,
            SupervisorAction.RETRY,
            SupervisorAction.REASSIGN,
        }

    def decision_snapshot(self) -> list[dict[str, Any]]:
        return [
            {
                "action": decision.action.value,
                "phase": decision.phase,
                "reason": decision.reason,
                "next_phase": decision.next_phase,
                "target_agent": decision.target_agent,
                "retry_count": decision.retry_count,
                "metadata": decision.metadata,
            }
            for decision in self.decisions
        ]

    def _evaluate_validation(self, normalized_output: str) -> SupervisorDecision:
        if self._requests_improvement(normalized_output):
            return self._validation_improvement_decision(
                "Validator requested improvements; restarting from research."
            )

        return SupervisorDecision(
            action=SupervisorAction.COMPLETE,
            phase="validation",
            reason="Validation output indicates workflow completion.",
            retry_count=self.retry_counts.get("validation_loop", 0),
        )

    def _validation_improvement_decision(self, reason: str) -> SupervisorDecision:
        retry_count = self.retry_counts.get("validation_loop", 0)
        if retry_count < self.max_retries_per_phase:
            self.retry_counts["validation_loop"] = retry_count + 1
            return SupervisorDecision(
                action=SupervisorAction.RETRY,
                phase="validation",
                reason=reason,
                next_phase="research",
                target_agent="Research Agent",
                retry_count=retry_count + 1,
                metadata={"retry_scope": "full_network"},
            )

        return SupervisorDecision(
            action=SupervisorAction.FAIL,
            phase="validation",
            reason="Validator still requested improvements after retry limit.",
            retry_count=retry_count,
        )

    def _retry_or_fail(
        self,
        phase: str,
        reason: str,
        target_agent: str | None,
    ) -> SupervisorDecision:
        retry_count = self.retry_counts.get(phase, 0)
        if retry_count < self.max_retries_per_phase:
            self.retry_counts[phase] = retry_count + 1
            return SupervisorDecision(
                action=SupervisorAction.RETRY,
                phase=phase,
                reason=reason,
                next_phase=phase,
                target_agent=self.phase_agents.get(phase, target_agent),
                retry_count=retry_count + 1,
            )

        return SupervisorDecision(
            action=SupervisorAction.FAIL,
            phase=phase,
            reason=f"{reason} Retry limit reached.",
            retry_count=retry_count,
        )

    def _reassign_or_fail(
        self,
        phase: str,
        reason: str,
        next_phase: str,
        target_agent: str,
    ) -> SupervisorDecision:
        retry_key = f"{phase}_reassign"
        retry_count = self.retry_counts.get(retry_key, 0)
        if retry_count < self.max_retries_per_phase:
            self.retry_counts[retry_key] = retry_count + 1
            return SupervisorDecision(
                action=SupervisorAction.REASSIGN,
                phase=phase,
                reason=reason,
                next_phase=next_phase,
                target_agent=target_agent,
                retry_count=retry_count + 1,
                metadata={"reassigned_from": phase},
            )

        return SupervisorDecision(
            action=SupervisorAction.FAIL,
            phase=phase,
            reason=f"{reason} Reassignment limit reached.",
            retry_count=retry_count,
        )

    @staticmethod
    def _looks_failed(normalized_output: str) -> bool:
        failure_markers = [
            "traceback",
            "exception",
            "failed",
            "error:",
            "api tool error",
            "file not found",
        ]
        return any(marker in normalized_output for marker in failure_markers)

    @staticmethod
    def _requests_improvement(normalized_output: str) -> bool:
        improvement_markers = [
            "needs improvement",
            "requires improvement",
            "improvement needed",
            "not complete",
            "incomplete",
        ]
        return any(marker in normalized_output for marker in improvement_markers)
