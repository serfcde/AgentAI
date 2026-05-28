import json
from typing import Any
from uuid import uuid4

from my_crew.a2a.message import (
    A2ATask,
    AgentCapability,
    AgentCard,
    AgentMessage,
    MessageType,
    TaskStatus,
    utc_now,
)


class A2AProtocolError(ValueError):
    pass


class A2AProtocol:
    required_message_fields = {"sender", "receiver", "content"}
    required_card_fields = {"agent_id", "name", "description"}

    @classmethod
    def validate_message(cls, message: AgentMessage) -> bool:
        missing = [
            field for field in cls.required_message_fields
            if not getattr(message, field, None)
        ]
        if missing:
            raise A2AProtocolError(
                f"Message is missing required fields: {', '.join(missing)}"
            )

        if not isinstance(message.message_type, MessageType):
            raise A2AProtocolError("message_type must be a MessageType value.")

        if message.status and not isinstance(message.status, TaskStatus):
            raise A2AProtocolError("status must be a TaskStatus value.")

        return True

    @classmethod
    def validate_agent_card(cls, card: AgentCard) -> bool:
        missing = [
            field for field in cls.required_card_fields
            if not getattr(card, field, None)
        ]
        if missing:
            raise A2AProtocolError(
                f"Agent card is missing required fields: {', '.join(missing)}"
            )
        return True

    @classmethod
    def serialize_message(cls, message: AgentMessage) -> str:
        cls.validate_message(message)
        return json.dumps(message.to_dict(), indent=2)

    @classmethod
    def deserialize_message(cls, message_json: str) -> AgentMessage:
        data = json.loads(message_json)
        message = cls.message_from_dict(data)
        cls.validate_message(message)
        return message

    @staticmethod
    def message_from_dict(data: dict[str, Any]) -> AgentMessage:
        return AgentMessage(
            sender=data["sender"],
            receiver=data["receiver"],
            content=data["content"],
            message_type=MessageType(data.get("message_type", "task_request")),
            task_id=data.get("task_id"),
            message_id=data.get("message_id") or str(uuid4()),
            correlation_id=data.get("correlation_id"),
            timestamp=data.get("timestamp") or utc_now(),
            status=TaskStatus(data["status"]) if data.get("status") else None,
            metadata=data.get("metadata", {}),
            final=data.get("final", True),
        )

    @classmethod
    def serialize_agent_card(cls, card: AgentCard) -> str:
        cls.validate_agent_card(card)
        return json.dumps(card.to_dict(), indent=2)

    @classmethod
    def deserialize_agent_card(cls, card_json: str) -> AgentCard:
        data = json.loads(card_json)
        capabilities = [
            AgentCapability(**capability)
            for capability in data.get("capabilities", [])
        ]
        card = AgentCard(
            agent_id=data["agent_id"],
            name=data["name"],
            description=data["description"],
            version=data.get("version", "1.0.0"),
            endpoint=data.get("endpoint"),
            capabilities=capabilities,
            metadata=data.get("metadata", {}),
        )
        cls.validate_agent_card(card)
        return card

    @staticmethod
    def serialize_task(task: A2ATask) -> str:
        return json.dumps(task.to_dict(), indent=2)
