import time

import pytest
from fastapi.testclient import TestClient

import my_crew.api as api_module
from my_crew.api import app

client = TestClient(app)

FAKE_RESULT = "Detailed workflow result for the requested topic. " * 5


def wait_for_completion(job_id: str, timeout: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        payload = client.get(f"/workflows/{job_id}").json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.02)
    raise TimeoutError(f"Job {job_id} did not finish in {timeout}s")


@pytest.fixture
def fake_runners(monkeypatch):
    runners = {
        "network": lambda topic: FAKE_RESULT,
        "hierarchical": lambda topic: FAKE_RESULT,
        "parallel": lambda topic: FAKE_RESULT,
    }
    monkeypatch.setattr(api_module, "WORKFLOW_RUNNERS", runners)
    monkeypatch.setattr(api_module, "decide_workflow", lambda topic: "network")
    return runners


class TestHealth:
    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestCreateWorkflow:
    def test_run_to_completion(self, fake_runners):
        response = client.post(
            "/workflows", json={"topic": "test topic", "workflow": "network"}
        )
        assert response.status_code == 202
        job_id = response.json()["job_id"]

        payload = wait_for_completion(job_id)
        assert payload["status"] == "completed"
        assert payload["result"] == FAKE_RESULT
        assert payload["error"] is None

    def test_auto_routing_resolves_workflow(self, fake_runners):
        response = client.post("/workflows", json={"topic": "test topic"})
        job_id = response.json()["job_id"]

        payload = wait_for_completion(job_id)
        assert payload["workflow"] == "network"
        assert payload["status"] == "completed"

    def test_failed_runner_reports_error(self, fake_runners, monkeypatch):
        def boom(topic):
            raise RuntimeError("workflow exploded")

        monkeypatch.setattr(
            api_module, "WORKFLOW_RUNNERS", {"network": boom}
        )
        response = client.post(
            "/workflows", json={"topic": "test topic", "workflow": "network"}
        )
        payload = wait_for_completion(response.json()["job_id"])
        assert payload["status"] == "failed"
        assert "workflow exploded" in payload["error"]

    def test_invalid_workflow_rejected(self):
        response = client.post(
            "/workflows", json={"topic": "x", "workflow": "quantum"}
        )
        assert response.status_code == 422

    def test_empty_topic_rejected(self):
        response = client.post("/workflows", json={"topic": ""})
        assert response.status_code == 422


class TestStatusAndStream:
    def test_unknown_job_is_404(self):
        assert client.get("/workflows/nope").status_code == 404
        assert client.get("/workflows/nope/stream").status_code == 404

    def test_stream_delivers_status_and_result_events(self, fake_runners):
        response = client.post(
            "/workflows", json={"topic": "test topic", "workflow": "network"}
        )
        job_id = response.json()["job_id"]
        wait_for_completion(job_id)

        stream = client.get(f"/workflows/{job_id}/stream")
        assert stream.status_code == 200
        assert stream.headers["content-type"].startswith("text/event-stream")
        body = stream.text
        assert "event: status" in body
        assert "event: result" in body
        assert "completed" in body
