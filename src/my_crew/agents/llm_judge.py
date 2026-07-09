"""LLM-backed structured judgments with graceful heuristic fallback.

Every function here returns ``None`` when the LLM is disabled, unreachable,
or returns unparseable output, so callers can always fall back to
deterministic heuristics.
"""

import json
import os
import re
from collections.abc import Callable
from typing import Any

from my_crew.utils.logger import get_logger

logger = get_logger("my_crew.llm_judge")

LLMCaller = Callable[[str], str]

OFF_VALUES = {"0", "false", "no", "off"}

WORKFLOW_NAMES = {"network", "hierarchical", "parallel"}

PHASE_REVIEW_PROMPT = """You are a strict quality supervisor for a multi-agent workflow.
Review the output of the '{phase}' phase for the topic below.

Topic: {topic}

Phase output:
---
{output}
---

Respond with ONLY a JSON object, no other text:
{{"verdict": "pass" or "fail", "needs_improvement": true or false, "feedback": "<one short sentence>"}}

Rules:
- "fail": the output is an error message, empty, off-topic, or unusable.
- "needs_improvement": true when the output is usable but has substantive gaps.
- "pass" with "needs_improvement": false means the output fully satisfies the phase.
"""

WORKFLOW_ROUTING_PROMPT = """Classify the best orchestration pattern for this topic.

Topic: {topic}

Patterns:
- network: default sequential research -> planning -> execution -> validation with supervisor review.
- hierarchical: a manager agent delegates dynamically; best for open-ended analysis or comparisons.
- parallel: research and planning run concurrently; best when the topic spans multiple independent subtopics.

Respond with ONLY a JSON object, no other text:
{{"workflow": "network" or "hierarchical" or "parallel"}}
"""


def flag_enabled(env_var: str) -> bool:
    return os.getenv(env_var, "1").strip().lower() not in OFF_VALUES


def get_default_llm_caller(env_var: str) -> LLMCaller | None:
    """Build a caller backed by the configured LLM unless disabled via env."""
    if not flag_enabled(env_var):
        return None

    def caller(prompt: str) -> str:
        from my_crew.config.llm import llm

        return str(llm.call(prompt))

    return caller


def extract_json(raw: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def review_phase_output(
    phase: str,
    topic: str,
    output: str,
    llm_caller: LLMCaller | None,
) -> dict[str, Any] | None:
    if llm_caller is None:
        return None

    prompt = PHASE_REVIEW_PROMPT.format(
        phase=phase,
        topic=topic,
        output=output[:4000],
    )
    try:
        raw = llm_caller(prompt)
    except Exception as error:
        logger.warning("LLM phase review unavailable (%s); using heuristics.", error)
        return None

    data = extract_json(raw)
    if not data or data.get("verdict") not in {"pass", "fail"}:
        logger.warning("LLM phase review was unparseable; using heuristics.")
        return None

    return {
        "verdict": data["verdict"],
        "needs_improvement": bool(data.get("needs_improvement", False)),
        "feedback": str(data.get("feedback", "")).strip(),
    }


def classify_workflow(topic: str, llm_caller: LLMCaller | None) -> str | None:
    if llm_caller is None:
        return None

    try:
        raw = llm_caller(WORKFLOW_ROUTING_PROMPT.format(topic=topic))
    except Exception as error:
        logger.warning("LLM routing unavailable (%s); using keyword routing.", error)
        return None

    data = extract_json(raw)
    workflow = (data or {}).get("workflow")
    if workflow in WORKFLOW_NAMES:
        return workflow

    logger.warning("LLM routing returned an invalid workflow; using keyword routing.")
    return None
