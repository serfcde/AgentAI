from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


CONFIG_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=8)
def load_yaml_config(file_name: str) -> dict[str, Any]:
    path = CONFIG_DIR / file_name
    with path.open("r", encoding="utf-8") as config_file:
        data = yaml.safe_load(config_file) or {}

    if not isinstance(data, dict):
        raise ValueError(f"{file_name} must contain a top-level mapping.")

    return data


def load_agent_config(agent_key: str) -> dict[str, Any]:
    agents = load_yaml_config("agents.yaml")
    if agent_key not in agents:
        raise KeyError(f"Agent config not found: {agent_key}")
    return agents[agent_key]


def load_task_config(task_key: str) -> dict[str, Any]:
    tasks = load_yaml_config("tasks.yaml")
    if task_key not in tasks:
        raise KeyError(f"Task config not found: {task_key}")
    return tasks[task_key]
