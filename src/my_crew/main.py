import argparse
import re
from datetime import datetime
from pathlib import Path

from my_crew.agents.supervisor import decide_workflow
from my_crew.utils.logger import get_logger
from my_crew.workflows.workflow_router import WORKFLOW_RUNNERS

logger = get_logger("my_crew.main")


def slugify(text: str, max_length: int = 60) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_length] or "topic"


def save_report(topic: str, workflow: str, result: str) -> Path:
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = reports_dir / f"{slugify(topic)}-{timestamp}.md"

    report_path.write_text(
        f"# Workflow Report: {topic}\n\n"
        f"- **Workflow:** {workflow}\n"
        f"- **Generated:** {datetime.now().isoformat(timespec='seconds')}\n\n"
        f"{result}\n",
        encoding="utf-8",
    )
    return report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="my-crew",
        description="Run a multi-agent workflow for a topic.",
    )
    parser.add_argument(
        "--topic",
        help="Topic to run the workflow on (prompts interactively if omitted).",
    )
    parser.add_argument(
        "--workflow",
        choices=["auto", *WORKFLOW_RUNNERS],
        default="auto",
        help="Workflow pattern to use (default: auto-routed from the topic).",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip writing the result to reports/.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    topic = args.topic or input("Enter Topic: ")
    if not topic.strip():
        raise SystemExit("Topic cannot be empty.")

    if args.workflow == "auto":
        workflow_name = decide_workflow(topic)
        logger.info("Routed topic to the %s workflow.", workflow_name)
    else:
        workflow_name = args.workflow
        logger.info("Using %s workflow (forced via --workflow).", workflow_name)

    result = WORKFLOW_RUNNERS[workflow_name](topic)

    print(result)

    if not args.no_report:
        report_path = save_report(topic, workflow_name, str(result))
        logger.info("Report saved to %s", report_path)


if __name__ == "__main__":
    main()
