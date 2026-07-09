"""Lightweight per-phase observability for workflow runs.

Collects wall-clock duration, output size, and (when the underlying CrewAI
result exposes ``token_usage``) token counts for every phase attempt.
"""

import time
from dataclasses import asdict, dataclass
from typing import Any

TOKEN_FIELDS = ("prompt_tokens", "completion_tokens", "total_tokens")


@dataclass(frozen=True)
class PhaseMetric:
    phase: str
    attempt: int
    duration_s: float
    output_chars: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_token_usage(result: Any) -> dict[str, int | None]:
    usage = getattr(result, "token_usage", None)
    if usage is None:
        return {}

    extracted = {}
    for field_name in TOKEN_FIELDS:
        value = getattr(usage, field_name, None)
        if isinstance(value, (int, float)):
            extracted[field_name] = int(value)
    return extracted


class MetricsCollector:
    def __init__(self):
        self.records: list[PhaseMetric] = []
        self._attempts: dict[str, int] = {}

    def start_timer(self) -> float:
        return time.perf_counter()

    def record_phase(self, phase: str, started: float, result: Any) -> PhaseMetric:
        attempt = self._attempts.get(phase, 0) + 1
        self._attempts[phase] = attempt

        metric = PhaseMetric(
            phase=phase,
            attempt=attempt,
            duration_s=round(time.perf_counter() - started, 2),
            output_chars=len(str(result)),
            **extract_token_usage(result),
        )
        self.records.append(metric)
        return metric

    def snapshot(self) -> list[dict[str, Any]]:
        return [metric.to_dict() for metric in self.records]

    def totals(self) -> dict[str, Any]:
        known_tokens = [
            metric.total_tokens
            for metric in self.records
            if metric.total_tokens is not None
        ]
        return {
            "phase_attempts": len(self.records),
            "total_duration_s": round(
                sum(metric.duration_s for metric in self.records), 2
            ),
            "total_output_chars": sum(
                metric.output_chars for metric in self.records
            ),
            "total_tokens": sum(known_tokens) if known_tokens else None,
        }
