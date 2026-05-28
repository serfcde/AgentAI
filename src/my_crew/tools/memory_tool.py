from crewai.tools import tool


memory_store = {}


@tool("Memory Tool")
def memory_tool(action: str, key: str, value: str = "") -> str:
    """
    Store and retrieve workflow memory/context.
    
    Actions:
    - save
    - get
    - delete
    """

    try:

        if action == "save":

            memory_store[key] = value

            return f"Memory saved for key: {key}"

        elif action == "get":

            return memory_store.get(
                key,
                "No memory found."
            )

        elif action == "delete":

            if key in memory_store:

                del memory_store[key]

                return f"Memory deleted for key: {key}"

            return "Key not found."

        else:

            return "Invalid action."

    except Exception as error:

        return f"Memory Tool Error: {str(error)}"