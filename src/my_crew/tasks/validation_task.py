from my_crew.tasks.factory import create_task_from_config


def create_validation_task(agent, topic, context=""):
    return create_task_from_config("validation_task", agent, topic, context)
