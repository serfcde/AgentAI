"""FastAPI service exposing the multi-agent workflows with SSE streaming.

Endpoints:
- ``POST /workflows``            start a workflow run (returns a job id)
- ``GET  /workflows/{job_id}``   poll job status and final result
- ``GET  /workflows/{job_id}/stream``  Server-Sent Events: live A2A bus
  traffic and status updates while the job runs
- ``GET  /health``               liveness probe

Run with: ``my-crew-api`` (or ``uvicorn my_crew.api:app``).
"""

import json
import os
import threading
from queue import Empty, Queue
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from my_crew.a2a.communication import CommunicationBus
from my_crew.a2a.message import describe_message
from my_crew.agents.supervisor import decide_workflow
from my_crew.utils.logger import get_logger
from my_crew.workflows.workflow_router import WORKFLOW_RUNNERS

logger = get_logger("my_crew.api")

app = FastAPI(
    title="my-crew",
    description="Multi-agent CrewAI workflows over the Google A2A protocol.",
    version="0.2.0",
)


class WorkflowRequest(BaseModel):
    topic: str = Field(min_length=1)
    workflow: Literal["auto", "network", "hierarchical", "parallel"] = "auto"


class Job:
    def __init__(self, topic: str, workflow: str):
        self.id = str(uuid4())
        self.topic = topic
        self.workflow = workflow
        self.status = "queued"
        self.result: str | None = None
        self.error: str | None = None
        self.events: Queue = Queue()

    def emit(self, event: str, data: str) -> None:
        self.events.put({"event": event, "data": data})

    def to_dict(self) -> dict:
        return {
            "job_id": self.id,
            "topic": self.topic,
            "workflow": self.workflow,
            "status": self.status,
            "error": self.error,
            "result": self.result,
        }


JOBS: dict[str, Job] = {}


def run_job(job: Job) -> None:
    def on_message(message) -> None:
        job.emit("a2a_message", describe_message(message))

    CommunicationBus.add_global_subscriber(on_message)
    try:
        job.status = "running"
        job.emit("status", "running")

        if job.workflow == "auto":
            job.workflow = decide_workflow(job.topic)
        job.emit("status", f"routed to {job.workflow} workflow")

        result = WORKFLOW_RUNNERS[job.workflow](job.topic)

        job.result = str(result)
        job.status = "completed"
        job.emit("result", job.result)
        job.emit("status", "completed")
    except Exception as error:
        job.status = "failed"
        job.error = str(error)
        job.emit("status", f"failed: {error}")
        logger.warning("Job %s failed: %s", job.id, error)
    finally:
        CommunicationBus.remove_global_subscriber(on_message)
        job.events.put(None)


@app.post("/workflows", status_code=202)
def create_workflow(request: WorkflowRequest) -> dict:
    job = Job(topic=request.topic, workflow=request.workflow)
    JOBS[job.id] = job

    threading.Thread(target=run_job, args=(job,), daemon=True).start()
    return {"job_id": job.id, "status": job.status}


@app.get("/workflows/{job_id}")
def get_workflow(job_id: str) -> dict:
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job.to_dict()


@app.get("/workflows/{job_id}/stream")
def stream_workflow(job_id: str) -> StreamingResponse:
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    def event_source():
        while True:
            try:
                item = job.events.get(timeout=300)
            except Empty:
                break
            if item is None:
                break
            yield (
                f"event: {item['event']}\n"
                f"data: {json.dumps(item['data'])}\n\n"
            )

    return StreamingResponse(event_source(), media_type="text/event-stream")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("MY_CREW_API_HOST", "127.0.0.1"),
        port=int(os.getenv("MY_CREW_API_PORT", "8000")),
    )


if __name__ == "__main__":
    main()
