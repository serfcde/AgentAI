from my_crew.workflows.parallel_flow import run_parallel_flow

GOOD_RESEARCH = (
    "Comprehensive research findings about the topic with detailed analysis, "
    "sources, market trends, and clear takeaways for the planning phase. " * 2
)
GOOD_PLAN = (
    "A detailed step-by-step execution plan with phases, owners, dependencies, "
    "milestones, and risk mitigations derived from the research. " * 2
)
GOOD_EXECUTION = (
    "Execution summary covering completed actions, operational steps taken, "
    "and measurable outcomes aligned with the plan. " * 2
)


class CountingRunner:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def __call__(self, topic):
        self.calls.append(topic)
        return self.outputs.pop(0) if len(self.outputs) > 1 else self.outputs[0]


def test_happy_path_runs_each_phase_once(monkeypatch):
    monkeypatch.setenv("MY_CREW_LLM_SUPERVISOR", "0")
    research = CountingRunner([GOOD_RESEARCH])
    planning = CountingRunner([GOOD_PLAN])
    execution = CountingRunner([GOOD_EXECUTION])

    result = run_parallel_flow(
        "test topic",
        phase_runners={
            "research": research,
            "planning": planning,
            "execution": execution,
        },
    )

    assert len(research.calls) == 1
    assert len(planning.calls) == 1
    assert len(execution.calls) == 1
    assert "RESEARCH RESULT" in result
    assert "SUPERVISOR DECISIONS" in result
    assert "'action': 'continue'" in result


def test_bad_research_is_retried_with_feedback(monkeypatch):
    monkeypatch.setenv("MY_CREW_LLM_SUPERVISOR", "0")
    bad_output = "Error: research crashed before finishing. " * 5
    research = CountingRunner([bad_output, GOOD_RESEARCH])
    planning = CountingRunner([GOOD_PLAN])
    execution = CountingRunner([GOOD_EXECUTION])

    result = run_parallel_flow(
        "test topic",
        phase_runners={
            "research": research,
            "planning": planning,
            "execution": execution,
        },
    )

    assert len(research.calls) == 2
    assert "Supervisor feedback" in research.calls[1]
    assert GOOD_RESEARCH.strip() in result
    assert "'action': 'retry'" in result


def test_execution_receives_reviewed_context(monkeypatch):
    monkeypatch.setenv("MY_CREW_LLM_SUPERVISOR", "0")
    research = CountingRunner([GOOD_RESEARCH])
    planning = CountingRunner([GOOD_PLAN])
    execution = CountingRunner([GOOD_EXECUTION])

    run_parallel_flow(
        "test topic",
        phase_runners={
            "research": research,
            "planning": planning,
            "execution": execution,
        },
    )

    execution_input = execution.calls[0]
    assert GOOD_RESEARCH.strip() in execution_input
    assert GOOD_PLAN.strip() in execution_input
