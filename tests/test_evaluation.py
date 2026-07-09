import json

from my_crew.evaluation import (
    evaluate_workflows,
    render_report,
    save_eval_report,
    score_output,
)


def fake_runners():
    return {
        "network": lambda topic: f"Network result for {topic}. " * 10,
        "parallel": lambda topic: (_ for _ in ()).throw(RuntimeError("boom")),
    }


def scoring_caller(prompt: str) -> str:
    return json.dumps({"score": 8, "justification": "Detailed and on-topic."})


class TestEvaluateWorkflows:
    def test_collects_metrics_per_workflow(self):
        results = evaluate_workflows("test topic", runners=fake_runners())

        by_name = {r["workflow"]: r for r in results}
        assert by_name["network"]["error"] is None
        assert by_name["network"]["output_chars"] > 0
        assert by_name["network"]["duration_s"] >= 0

    def test_failed_workflow_is_recorded_not_raised(self):
        results = evaluate_workflows("test topic", runners=fake_runners())
        by_name = {r["workflow"]: r for r in results}
        assert by_name["parallel"]["error"] == "boom"
        assert by_name["parallel"]["output_chars"] == 0

    def test_llm_scoring_attached_when_caller_provided(self):
        results = evaluate_workflows(
            "test topic", runners=fake_runners(), llm_caller=scoring_caller
        )
        by_name = {r["workflow"]: r for r in results}
        assert by_name["network"]["score"] == 8
        assert by_name["parallel"]["score"] is None


class TestScoreOutput:
    def test_score_is_clamped_to_range(self):
        def caller(prompt: str) -> str:
            return json.dumps({"score": 42, "justification": "wow"})

        assert score_output("t", "output", caller)["score"] == 10

    def test_unparseable_score_returns_none(self):
        assert score_output("t", "output", lambda p: "not json") is None

    def test_caller_error_returns_none(self):
        def broken(prompt: str) -> str:
            raise ConnectionError("down")

        assert score_output("t", "output", broken) is None

    def test_no_caller_returns_none(self):
        assert score_output("t", "output", None) is None


class TestReport:
    def test_render_report_contains_table_and_best(self):
        results = evaluate_workflows(
            "test topic", runners=fake_runners(), llm_caller=scoring_caller
        )
        report = render_report("test topic", results)

        assert "| Workflow | Duration (s) |" in report
        assert "| network |" in report
        assert "failed: boom" in report
        assert "**Best scored:** `network`" in report

    def test_save_eval_report_writes_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        results = evaluate_workflows("test topic", runners=fake_runners())
        path = save_eval_report("test topic", results)

        assert path.exists()
        assert "Workflow Evaluation: test topic" in path.read_text()
