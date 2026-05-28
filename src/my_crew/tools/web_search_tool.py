from crewai.tools import tool


@tool("Web Search Tool")
def web_search_tool(query: str) -> str:
    """
    Search for external information related
    to AI workflows, orchestration systems,
    and agent-based architectures.
    """

    simulated_results = f"""
    Web Search Results for: {query}

    1. AI orchestration systems improve workflow automation.
    2. Multi-agent architectures enable distributed execution.
    3. Supervisor patterns help coordinate AI agents efficiently.
    4. Parallel workflows improve execution performance.
    """

    return simulated_results