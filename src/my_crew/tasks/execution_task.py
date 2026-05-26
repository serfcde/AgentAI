from crewai import Task


def create_execution_task(agent, topic):
    return Task(
        description=f"""
        Execute the implementation strategy for:

        Topic:
        {topic}

        Produce actionable execution details
        and implementation guidance.
        """,

        expected_output="""
        Actionable implementation steps and execution details.
        """,

        agent=agent
    )