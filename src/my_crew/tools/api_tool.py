from crewai.tools import tool
import requests


@tool("API Tool")
def api_tool(endpoint: str) -> str:
    """
    Fetch data from an external API endpoint.
    Useful for retrieving external information
    during workflow execution.
    """

    try:

        response = requests.get(endpoint, timeout=10)

        if response.status_code == 200:
            return response.text

        return f"API request failed with status code: {response.status_code}"

    except Exception as error:

        return f"API Tool Error: {str(error)}"