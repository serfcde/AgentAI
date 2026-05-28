from crewai.tools import tool
from datetime import datetime


@tool("Logger Tool")
def logger_tool(message: str) -> str:
    """
    Log important execution events.
    """

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_message = f"[{timestamp}] {message}"

    print(log_message)

    return log_message