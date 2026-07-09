import warnings

warnings.filterwarnings(
    "ignore",
    message="This package .* has been renamed to `ddgs`.*",
    category=RuntimeWarning,
)

from crewai.tools import tool  # noqa: E402
from duckduckgo_search import DDGS  # noqa: E402


@tool("Web Search Tool")
def web_search_tool(query: str) -> str:
    """
    Search the web for current information about any user-provided topic.
    """

    if not query or not query.strip():
        return "Web Search Tool Error: query cannot be empty."

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            with DDGS() as search_client:
                results = list(
                    search_client.text(
                        query.strip(),
                        max_results=5,
                    )
                )

        if not results:
            return f"No web search results found for: {query}"

        formatted_results = [f"Web Search Results for: {query.strip()}"]

        for index, result in enumerate(results, start=1):
            title = result.get("title", "Untitled result")
            url = result.get("href", "No URL provided")
            snippet = result.get("body", "No summary provided")
            formatted_results.append(
                f"{index}. {title}\n"
                f"   URL: {url}\n"
                f"   Summary: {snippet}"
            )

        return "\n\n".join(formatted_results)

    except Exception as error:
        return f"Web Search Tool Error: {str(error)}"
