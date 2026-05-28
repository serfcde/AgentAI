from my_crew.tools.api_tool import api_tool
from my_crew.tools.calculator_tool import calculator_tool
from my_crew.tools.file_reader_tool import file_reader_tool
from my_crew.tools.logger_tool import logger_tool
from my_crew.tools.memory_tool import memory_tool
from my_crew.tools.notification_tool import notification_tool
from my_crew.tools.web_search_tool import web_search_tool


TOOL_REGISTRY = {
    "api_tool": api_tool,
    "calculator_tool": calculator_tool,
    "file_reader_tool": file_reader_tool,
    "logger_tool": logger_tool,
    "memory_tool": memory_tool,
    "notification_tool": notification_tool,
    "web_search_tool": web_search_tool,
}


def resolve_tools(tool_names: list[str] | None):
    if not tool_names:
        return []

    missing = [name for name in tool_names if name not in TOOL_REGISTRY]
    if missing:
        raise KeyError(f"Unknown tools in config: {', '.join(missing)}")

    return [TOOL_REGISTRY[name] for name in tool_names]
