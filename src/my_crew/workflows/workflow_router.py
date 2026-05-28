from my_crew.agents.supervisor import decide_workflow
from my_crew.workflows.hierarchical_flow import run_hierarchical_flow
from my_crew.workflows.network_flow import run_network_flow
from my_crew.workflows.parallel_flow import run_parallel_flow


def choose_workflow(topic: str):
    workflow = decide_workflow(topic)

    if workflow == "hierarchical":
        print("\nUsing Hierarchical Workflow\n")
        return run_hierarchical_flow(topic)

    if workflow == "parallel":
        print("\nUsing Parallel Workflow\n")
        return run_parallel_flow(topic)

    print("\nUsing Network Workflow\n")
    return run_network_flow(topic)
