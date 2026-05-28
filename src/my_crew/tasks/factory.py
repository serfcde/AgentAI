from crewai import Task

from my_crew.config.loader import load_task_config


def create_task_from_config(
    task_key: str,
    agent,
    topic: str,
    context: str = "",
) -> Task:
    config = load_task_config(task_key)
    values = {
        "topic": topic,
        "context": context,
    }

    return Task(
        description=config["description"].format(**values),
        expected_output=config["expected_output"].format(**values),
        agent=agent,
    )
