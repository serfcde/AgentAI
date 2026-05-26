from my_crew.agents.researcher import create_research_agent
from my_crew.agents.planner import create_planner_agent
from my_crew.agents.validator import create_validator_agent
from my_crew.agents.executor import create_executor_agent
from my_crew.agents.supervisor import create_supervisor_agent


research_agent = create_research_agent()
planner_agent = create_planner_agent()
validator_agent = create_validator_agent()
executor_agent = create_executor_agent()
supervisor_agent = create_supervisor_agent()


print(research_agent)
print()

print(planner_agent)
print()

print(validator_agent)
print()

print(executor_agent)
print()

print(supervisor_agent)