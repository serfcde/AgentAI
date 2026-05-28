from my_crew.tasks.factory import create_task_from_config


def create_execution_task(agent, topic, context=""):
    return create_task_from_config("execution_task", agent, topic, context)
