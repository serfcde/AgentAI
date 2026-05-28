from crewai.tools import tool
from datetime import datetime


@tool("Notification Tool")
def notification_tool(message: str) -> str:
    """
    Send workflow notifications and alerts.
    """

    try:

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        notification = (
            f"[NOTIFICATION - {timestamp}] {message}"
        )

        print(notification)

        return notification

    except Exception as error:

        return (
            f"Notification Tool Error: {str(error)}"
        )