from crewai import Task


def create_planning_task(agent, topic, context =""):
    return Task(
        description=f"""
        Create a strategic execution plan for:

        Topic:
        {topic}

        Research Context:
        {context}

        Break the work into:
        - phases
        - milestones
        - execution steps
        - priorities
        - dependencies

        Produce a highly organized workflow plan.
        """,

        expected_output="""
        A structured execution roadmap including:
        - phases
        - task breakdown
        - priorities
        - dependencies
        - execution order
        """,

        agent=agent
    )