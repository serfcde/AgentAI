import json

from my_crew.agents.llm_judge import classify_workflow, extract_json
from my_crew.agents.supervisor import decide_workflow, decide_workflow_heuristic


class TestHeuristicRouting:
    def test_analysis_routes_hierarchical(self):
        assert decide_workflow_heuristic("analysis of agent frameworks") == "hierarchical"

    def test_multiple_routes_parallel(self):
        assert decide_workflow_heuristic("multiple AI strategies") == "parallel"

    def test_default_routes_network(self):
        assert decide_workflow_heuristic("future of AI agents") == "network"


class TestLLMRouting:
    def test_llm_choice_wins(self):
        def caller(prompt: str) -> str:
            return json.dumps({"workflow": "parallel"})

        assert decide_workflow("future of AI agents", llm_caller=caller) == "parallel"

    def test_invalid_llm_choice_falls_back_to_heuristics(self):
        def caller(prompt: str) -> str:
            return json.dumps({"workflow": "quantum"})

        assert decide_workflow("analysis of X", llm_caller=caller) == "hierarchical"

    def test_llm_error_falls_back_to_heuristics(self):
        def caller(prompt: str) -> str:
            raise ConnectionError("Ollama is down")

        assert decide_workflow("future of AI agents", llm_caller=caller) == "network"

    def test_classify_workflow_without_caller_returns_none(self):
        assert classify_workflow("any topic", None) is None


class TestExtractJson:
    def test_plain_json(self):
        assert extract_json('{"workflow": "network"}') == {"workflow": "network"}

    def test_json_embedded_in_prose(self):
        raw = 'Sure! Here is the answer:\n{"verdict": "pass"}\nHope that helps.'
        assert extract_json(raw) == {"verdict": "pass"}

    def test_garbage_returns_none(self):
        assert extract_json("no json here") is None
        assert extract_json("{broken json") is None
