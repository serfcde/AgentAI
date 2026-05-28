from my_crew.tasks.factory import create_task_from_config


def create_research_task(agent, topic):
    return create_task_from_config("research_task", agent, topic)
