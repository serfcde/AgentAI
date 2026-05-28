from crewai import Task


def create_research_task(agent, topic):
    return Task(
        description=f"""
        Research the following topic thoroughly:

        Topic:
        {topic}

        Focus on:
        - latest trends
        - important technologies
        - real-world applications
        - challenges
        - future scope

        Use the available tools whenever necessary.
        
        Provide structured research findings.
        """,

        expected_output="""
        A detailed research report with:
        - overview
        - key insights
        - trends
        - applications
        - challenges
        - conclusion
        """,

        agent=agent
    )