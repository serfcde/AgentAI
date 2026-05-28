from crewai.tools import tool

@tool("Calculator Tool")
def calculator_tool(expression: str) -> str:
    """
    Evaluate a mathematical expression.
    """

    try:
        result = eval(expression)

        return f"Result: {result}"

    except Exception as e:
        return f"Error: {str(e)}"