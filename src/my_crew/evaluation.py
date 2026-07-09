"""Evaluation harness: run one topic through every workflow pattern and compare.

Collects duration, output size, and an optional LLM quality score (1-10) per
workflow, then renders a Markdown comparison report under ``reports/``.

Usage:
    my-crew-eval --topic "Future of AI Agents"
    my-crew-eval --topic "..." --workflows network parallel
"""

import argparse
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from my_crew.agents.llm_judge import (
    LLMCaller,
    extract_json,
    get_default_llm_caller,
)
from my_crew.utils.logger import get_logger

logger = get_logger("my_crew.evaluation")

QUALITY_PROMPT = """You are grading the final output of a multi-agent workflow.

Topic: {topic}

Workflow output:
---
{output}
---

Score the output for completeness, accuracy, and usefulness on the topic.

Respond with ONLY a JSON object, no other text:
{{"score": <integer 1-10>, "justification": "<one short sentence>"}}
"""


def score_output(
    topic: str,
    output: str,
    llm_caller: LLMCaller | None,
) -> dict[str, Any] | None:
    if llm_caller is None:
        return None

    try:
        raw = llm_caller(QUALITY_PROMPT.format(topic=topic, output=output[:6000]))
    except Exception as error:
        logger.warning("LLM scoring unavailable (%s); skipping scores.", error)
        return None

    data = extract_json(raw)
    if not data or not isinstance(data.get("score"), (int, float)):
        logger.warning("LLM scoring returned unparseable output; skipping scores.")
        return None

    return {
        "score": max(1, min(10, int(data["score"]))),
        "justification": str(data.get("justification", "")).strip(),
    }


def evaluate_workflows(
    topic: str,
    runners: dict[str, Any] | None = None,
    llm_caller: LLMCaller | None = None,
) -> list[dict[str, Any]]:
    if runners is None:
        from my_crew.workflows.workflow_router import WORKFLOW_RUNNERS

        runners = WORKFLOW_RUNNERS

    results = []
    for name, runner in runners.items():
        logger.info("Evaluating %s workflow...", name)
        started = time.perf_counter()
        try:
            output = str(runner(topic))
            error = None
        except Exception as exc:
            output = ""
            error = str(exc)
            logger.warning("%s workflow failed: %s", name, exc)

        entry: dict[str, Any] = {
            "workflow": name,
            "duration_s": round(time.perf_counter() - started, 2),
            "output_chars": len(output),
            "error": error,
            "score": None,
            "justification": None,
            "output": output,
        }

        if output:
            review = score_output(topic, output, llm_caller)
            if review:
                entry["score"] = review["score"]
                entry["justification"] = review["justification"]

        results.append(entry)

    return results


def render_report(topic: str, results: list[dict[str, Any]]) -> str:
    lines = [
        f"# Workflow Evaluation: {topic}",
        "",
        f"- **Generated:** {datetime.now().isoformat(timespec='seconds')}",
        f"- **Workflows compared:** {', '.join(r['workflow'] for r in results)}",
        "",
        "| Workflow | Duration (s) | Output (chars) | Score (1-10) | Status |",
        "|---|---|---|---|---|",
    ]

    for result in results:
        status = f"failed: {result['error']}" if result["error"] else "ok"
        score = result["score"] if result["score"] is not None else "-"
        lines.append(
            f"| {result['workflow']} | {result['duration_s']} "
            f"| {result['output_chars']} | {score} | {status} |"
        )

    scored = [r for r in results if r["score"] is not None]
    if scored:
        best = max(scored, key=lambda r: r["score"])
        lines += [
            "",
            f"**Best scored:** `{best['workflow']}` "
            f"({best['score']}/10) — {best['justification']}",
        ]

    for result in results:
        if result["output"]:
            lines += [
                "",
                f"## {result['workflow']} output",
                "",
                result["output"],
            ]

    return "\n".join(lines) + "\n"


def save_eval_report(topic: str, results: list[dict[str, Any]]) -> Path:
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = reports_dir / f"eval-{timestamp}.md"
    report_path.write_text(render_report(topic, results), encoding="utf-8")
    return report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="my-crew-eval",
        description="Run one topic through every workflow pattern and compare.",
    )
    parser.add_argument("--topic", required=True, help="Topic to evaluate.")
    parser.add_argument(
        "--workflows",
        nargs="+",
        choices=["network", "hierarchical", "parallel"],
        help="Subset of workflows to compare (default: all three).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    from my_crew.workflows.workflow_router import WORKFLOW_RUNNERS

    runners = {
        name: runner
        for name, runner in WORKFLOW_RUNNERS.items()
        if not args.workflows or name in args.workflows
    }

    results = evaluate_workflows(
        args.topic,
        runners=runners,
        llm_caller=get_default_llm_caller("MY_CREW_LLM_SCORING"),
    )

    report_path = save_eval_report(args.topic, results)

    for result in results:
        status = f"FAILED ({result['error']})" if result["error"] else "ok"
        score = f"{result['score']}/10" if result["score"] is not None else "unscored"
        print(
            f"{result['workflow']:>13}: {status:>6} | "
            f"{result['duration_s']}s | {result['output_chars']} chars | {score}"
        )
    print(f"\nFull report: {report_path}")


if __name__ == "__main__":
    main()
