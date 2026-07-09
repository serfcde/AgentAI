"""Google A2A protocol types (official ``a2a-sdk``) plus local conventions.

All wire objects (``AgentCard``, ``Message``, ``Task``, ...) are the official
protobuf types from the A2A v1 specification. The A2A protocol addresses
agents at the transport level, so for the in-process bus the sender,
receiver, and message kind travel in ``Message.metadata`` under the
``META_*`` keys defined here.
"""

from enum import Enum
from typing import Any
from uuid import uuid4

from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    Artifact,
    Message,
    Part,
    Role,
    Task,
    TaskState,
    TaskStatus,
)
from google.protobuf import struct_pb2
from google.protobuf.json_format import MessageToDict


__all__ = [
    "AgentCapabilities",
    "AgentCard",
    "AgentInterface",
    "AgentSkill",
    "Artifact",
    "Message",
    "MessageKind",
    "Part",
    "Role",
    "Task",
    "TaskState",
    "TaskStatus",
    "build_agent_card",
    "describe_message",
    "message_kind",
    "message_meta",
    "message_receiver",
    "message_sender",
    "message_text",
    "new_agent_message",
    "new_task",
    "set_task_state",
    "task_state_name",
    "task_to_dict",
    "to_struct",
]


class MessageKind(str, Enum):
    """Local convention for classifying bus messages (stored in metadata)."""

    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    EVENT = "event"
    STREAM_CHUNK = "stream_chunk"


META_SENDER = "sender"
META_RECEIVER = "receiver"
META_KIND = "kind"
META_FINAL = "final"


def to_struct(data: dict[str, Any] | None) -> struct_pb2.Struct:
    struct = struct_pb2.Struct()
    if data:
        struct.update(data)
    return struct


def new_agent_message(
    sender: str,
    receiver: str,
    content: str,
    kind: MessageKind = MessageKind.TASK_REQUEST,
    task_id: str | None = None,
    context_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    final: bool = True,
) -> Message:
    meta = {
        META_SENDER: sender,
        META_RECEIVER: receiver,
        META_KIND: kind.value,
        META_FINAL: final,
        **(metadata or {}),
    }
    return Message(
        message_id=str(uuid4()),
        task_id=task_id or "",
        context_id=context_id or "",
        role=Role.ROLE_AGENT,
        parts=[Part(text=content)],
        metadata=to_struct(meta),
    )


def message_text(message: Message) -> str:
    return "\n".join(part.text for part in message.parts if part.text)


def message_meta(message: Message, key: str, default: Any = None) -> Any:
    return dict(message.metadata).get(key, default)


def message_sender(message: Message) -> str:
    return str(message_meta(message, META_SENDER, ""))


def message_receiver(message: Message) -> str:
    return str(message_meta(message, META_RECEIVER, ""))


def message_kind(message: Message) -> str:
    return str(message_meta(message, META_KIND, MessageKind.TASK_REQUEST.value))


def describe_message(message: Message) -> str:
    text = message_text(message)
    if len(text) > 200:
        text = f"{text[:200]}..."
    return (
        f"[{message_kind(message)}] "
        f"{message_sender(message)} -> {message_receiver(message)}: {text}"
    )


def build_agent_card(
    name: str,
    description: str,
    skill_id: str,
    skill_description: str,
    streaming: bool = False,
) -> AgentCard:
    return AgentCard(
        name=name,
        description=description,
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=streaming),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            AgentSkill(
                id=skill_id,
                name=skill_id,
                description=skill_description,
                tags=[skill_id],
            )
        ],
        supported_interfaces=[AgentInterface(url=f"local://agents/{skill_id}")],
    )


def new_task(
    title: str,
    owner: str,
    metadata: dict[str, Any] | None = None,
) -> Task:
    task = Task(
        id=str(uuid4()),
        context_id=str(uuid4()),
        metadata=to_struct({"title": title, "owner": owner, **(metadata or {})}),
    )
    set_task_state(task, TaskState.TASK_STATE_SUBMITTED)
    return task


def set_task_state(task: Task, state: "TaskState") -> None:
    task.status.state = state
    task.status.timestamp.GetCurrentTime()


def task_state_name(state: "TaskState") -> str:
    return TaskState.Name(state).removeprefix("TASK_STATE_").lower()


def task_to_dict(task: Task) -> dict[str, Any]:
    return MessageToDict(task)
