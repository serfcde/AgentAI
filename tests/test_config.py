import pytest

from my_crew.config.loader import (
    load_agent_config,
    load_task_config,
    load_yaml_config,
)
from my_crew.tools.registry import TOOL_REGISTRY, resolve_tools


EXPECTED_AGENTS = {
    "research_agent",
    "planning_agent",
    "execution_agent",
    "validation_agent",
    "supervisor_agent",
}


class TestYamlConfig:
    def test_all_agents_defined(self):
        agents = load_yaml_config("agents.yaml")
        assert EXPECTED_AGENTS <= set(agents)

    def test_agent_configs_have_required_fields(self):
        agents = load_yaml_config("agents.yaml")
        for key, config in agents.items():
            assert config.get("role"), f"{key} is missing a role"
            assert config.get("goal"), f"{key} is missing a goal"
            assert config.get("backstory"), f"{key} is missing a backstory"

    def test_all_configured_tools_exist_in_registry(self):
        agents = load_yaml_config("agents.yaml")
        for key, config in agents.items():
            for tool_name in config.get("tools", []):
                assert tool_name in TOOL_REGISTRY, (
                    f"{key} references unknown tool: {tool_name}"
                )

    def test_unknown_agent_raises(self):
        with pytest.raises(KeyError):
            load_agent_config("nonexistent_agent")

    def test_unknown_task_raises(self):
        with pytest.raises(KeyError):
            load_task_config("nonexistent_task")


class TestToolRegistry:
    def test_resolve_known_tools(self):
        tools = resolve_tools(["memory_tool", "logger_tool"])
        assert len(tools) == 2

    def test_resolve_empty_returns_empty_list(self):
        assert resolve_tools(None) == []
        assert resolve_tools([]) == []

    def test_resolve_unknown_tool_raises(self):
        with pytest.raises(KeyError):
            resolve_tools(["warp_drive_tool"])
