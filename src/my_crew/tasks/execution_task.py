from crewai import Task


def create_execution_task(agent, topic, context=""):
    return Task(
        description=f"""
        Execute the implementation strategy for:

        Topic:
        {topic}

        Planning Context:
        {context}

        Produce actionable execution details
        and implementation guidance.
        """,

        expected_output="""
        Actionable implementation steps and execution details.
        """,

        agent=agent
    )