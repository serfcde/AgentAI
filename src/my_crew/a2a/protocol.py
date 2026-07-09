"""Validation and JSON wire serialization for Google A2A protocol objects.

Messages travel in the official ``SendMessageRequest`` envelope and are
serialized with protobuf's canonical JSON mapping, so payloads are
interoperable with any A2A v1 implementation.
"""

from a2a.types import AgentCard, Message, Role, SendMessageRequest, Task
from google.protobuf.json_format import MessageToJson, Parse, ParseError

from my_crew.a2a.message import META_RECEIVER, META_SENDER


class A2AProtocolError(ValueError):
    pass


class A2AProtocol:
    @classmethod
    def validate_message(cls, message: Message) -> bool:
        if not message.message_id:
            raise A2AProtocolError("Message is missing a message_id.")

        if message.role == Role.ROLE_UNSPECIFIED:
            raise A2AProtocolError("Message role must be specified.")

        if not any(part.text for part in message.parts):
            raise A2AProtocolError(
                "Message must contain at least one non-empty text part."
            )

        meta = dict(message.metadata)
        missing = [
            key for key in (META_SENDER, META_RECEIVER) if not meta.get(key)
        ]
        if missing:
            raise A2AProtocolError(
                f"Message metadata is missing required keys: {', '.join(missing)}"
            )

        return True

    @classmethod
    def validate_agent_card(cls, card: AgentCard) -> bool:
        missing = [
            field for field in ("name", "description", "version")
            if not getattr(card, field)
        ]
        if missing:
            raise A2AProtocolError(
                f"Agent card is missing required fields: {', '.join(missing)}"
            )

        if not card.skills:
            raise A2AProtocolError("Agent card must declare at least one skill.")

        return True

    @classmethod
    def serialize_message(cls, message: Message) -> str:
        cls.validate_message(message)
        return MessageToJson(SendMessageRequest(message=message))

    @classmethod
    def deserialize_message(cls, message_json: str) -> Message:
        try:
            request = Parse(message_json, SendMessageRequest())
        except ParseError as error:
            raise A2AProtocolError(f"Invalid A2A message payload: {error}") from error

        cls.validate_message(request.message)
        return request.message

    @classmethod
    def serialize_agent_card(cls, card: AgentCard) -> str:
        cls.validate_agent_card(card)
        return MessageToJson(card)

    @classmethod
    def deserialize_agent_card(cls, card_json: str) -> AgentCard:
        try:
            card = Parse(card_json, AgentCard())
        except ParseError as error:
            raise A2AProtocolError(f"Invalid A2A agent card: {error}") from error

        cls.validate_agent_card(card)
        return card

    @staticmethod
    def serialize_task(task: Task) -> str:
        return MessageToJson(task)
