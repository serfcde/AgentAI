from crewai import Task


def create_validation_task(agent, topic):
    return Task(
        description=f"""
        Validate all outputs generated for:

        Topic:
        {topic}

        Check for:
        - correctness
        - consistency
        - logical flow
        - completeness
        - reliability

        Suggest improvements if needed.
        """,

        expected_output="""
        Validation report including:
        - detected issues
        - quality assessment
        - improvement suggestions
        - final evaluation
        """,

        agent=agent
    )