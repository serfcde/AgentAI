from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MessageType(str, Enum):
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    EVENT = "event"
    STREAM_CHUNK = "stream_chunk"
    ERROR = "error"


class TaskStatus(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input_required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass(frozen=True)
class AgentCapability:
    name: str
    description: str
    input_modes: list[str] = field(default_factory=lambda: ["text/plain"])
    output_modes: list[str] = field(default_factory=lambda: ["text/plain"])
    streaming: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentCard:
    agent_id: str
    name: str
    description: str
    version: str = "1.0.0"
    endpoint: str | None = None
    capabilities: list[AgentCapability] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["capabilities"] = [
            capability.to_dict() for capability in self.capabilities
        ]
        return data


@dataclass
class A2ATask:
    task_id: str
    title: str
    owner: str
    status: TaskStatus = TaskStatus.SUBMITTED
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    messages: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_message(self, message_id: str) -> None:
        self.messages.append(message_id)
        self.updated_at = utc_now()

    def set_status(self, status: TaskStatus) -> None:
        self.status = status
        self.updated_at = utc_now()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(frozen=True)
class AgentMessage:
    sender: str
    receiver: str
    content: str
    message_type: MessageType = MessageType.TASK_REQUEST
    task_id: str | None = None
    message_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str | None = None
    timestamp: str = field(default_factory=utc_now)
    status: TaskStatus | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    final: bool = True

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["message_type"] = self.message_type.value
        data["status"] = self.status.value if self.status else None
        return data

    def __str__(self) -> str:
        status = f" status={self.status.value}" if self.status else ""
        task = f" task={self.task_id}" if self.task_id else ""
        return (
            f"\n[{self.message_type.value}{status}{task}] "
            f"{self.sender} -> {self.receiver}\n"
            f"{self.content}\n"
        )
