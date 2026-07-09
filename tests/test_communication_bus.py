import pytest

from my_crew.a2a.communication import CommunicationBus
from my_crew.a2a.message import (
    AgentCard,
    Message,
    MessageKind,
    TaskState,
    build_agent_card,
    message_kind,
    message_meta,
    message_sender,
    message_text,
    new_agent_message,
)
from my_crew.a2a.protocol import A2AProtocol, A2AProtocolError


def make_card(name: str) -> AgentCard:
    return build_agent_card(
        name=name,
        description=f"{name} test agent",
        skill_id=name.lower().replace(" ", "-"),
        skill_description=f"{name} skill",
    )


def make_bus(*agent_names: str) -> CommunicationBus:
    bus = CommunicationBus()
    for name in agent_names:
        bus.register_agent(make_card(name))
    return bus


class TestRegistration:
    def test_register_and_list_agents(self):
        bus = make_bus("Agent A", "Agent B")
        cards = bus.list_agent_cards()
        assert {card.name for card in cards} == {"Agent A", "Agent B"}

    def test_card_without_skills_is_rejected(self):
        bus = CommunicationBus()
        with pytest.raises(A2AProtocolError):
            bus.register_agent(
                AgentCard(name="Agent A", description="no skills", version="1.0.0")
            )

    def test_card_without_name_is_rejected(self):
        bus = CommunicationBus()
        with pytest.raises(A2AProtocolError):
            bus.register_agent(AgentCard())


class TestMessaging:
    def test_direct_message_lands_in_receiver_inbox(self):
        bus = make_bus("Agent A", "Agent B")
        bus.send_message("Agent A", "Agent B", "hello")

        inbox = bus.receive_messages("Agent B")
        assert len(inbox) == 1
        assert message_text(inbox[0]) == "hello"
        assert message_sender(inbox[0]) == "Agent A"

    def test_receive_messages_drains_inbox(self):
        bus = make_bus("Agent A", "Agent B")
        bus.send_message("Agent A", "Agent B", "hello")
        assert len(bus.receive_messages("Agent B")) == 1
        assert bus.receive_messages("Agent B") == []

    def test_broadcast_reaches_everyone_except_sender(self):
        bus = make_bus("Agent A", "Agent B", "Agent C")
        bus.broadcast("Agent A", "announcement")

        assert len(bus.receive_messages("Agent B")) == 1
        assert len(bus.receive_messages("Agent C")) == 1
        assert bus.receive_messages("Agent A") == []

    def test_message_without_content_is_rejected(self):
        bus = make_bus("Agent A", "Agent B")
        with pytest.raises(A2AProtocolError):
            bus.send_message("Agent A", "Agent B", "")

    def test_subscriber_callback_fires(self):
        bus = make_bus("Agent A", "Agent B")
        received: list[Message] = []
        bus.subscribe("Agent B", received.append)

        bus.send_message("Agent A", "Agent B", "ping")
        assert len(received) == 1
        assert message_text(received[0]) == "ping"

    def test_stream_message_marks_last_chunk_final(self):
        bus = make_bus("Agent A", "Agent B")
        messages = bus.stream_message(
            "Agent A", "Agent B", ["chunk one", "chunk two", "chunk three"]
        )

        finals = [message_meta(m, "final") for m in messages]
        assert finals == [False, False, True]
        assert all(
            message_kind(m) == MessageKind.STREAM_CHUNK.value for m in messages
        )
        assert [message_meta(m, "chunk_index") for m in messages] == [0, 1, 2]


class TestTasks:
    def test_create_task_and_status_update(self):
        bus = make_bus("Agent A", "Agent B")
        task = bus.create_task("demo task", owner="Agent A")
        assert (
            bus.get_task(task.id).status.state == TaskState.TASK_STATE_SUBMITTED
        )

        bus.update_task_status(
            task.id, TaskState.TASK_STATE_COMPLETED, sender="Agent A"
        )
        assert (
            bus.get_task(task.id).status.state == TaskState.TASK_STATE_COMPLETED
        )

    def test_task_records_message_history(self):
        bus = make_bus("Agent A", "Agent B")
        task = bus.create_task("demo task", owner="Agent A")
        message = bus.send_message(
            "Agent A", "Agent B", "work update", task_id=task.id
        )

        history_ids = [m.message_id for m in bus.get_task(task.id).history]
        assert message.message_id in history_ids

    def test_task_snapshot_serializes(self):
        bus = make_bus("Agent A")
        bus.create_task("demo task", owner="Agent A", metadata={"k": "v"})
        snapshot = bus.task_snapshot()
        assert len(snapshot) == 1
        assert snapshot[0]["metadata"]["k"] == "v"
        assert snapshot[0]["metadata"]["title"] == "demo task"
        assert snapshot[0]["status"]["state"] == "TASK_STATE_SUBMITTED"


class TestProtocol:
    def test_message_roundtrip(self):
        message = new_agent_message(
            sender="Agent A",
            receiver="Agent B",
            content="hello",
            kind=MessageKind.TASK_RESPONSE,
            metadata={"phase": "research"},
        )
        restored = A2AProtocol.deserialize_message(
            A2AProtocol.serialize_message(message)
        )
        assert restored == message

    def test_agent_card_roundtrip(self):
        card = make_card("Agent A")
        restored = A2AProtocol.deserialize_agent_card(
            A2AProtocol.serialize_agent_card(card)
        )
        assert restored == card

    def test_bus_accepts_serialized_protocol_message(self):
        bus = make_bus("Agent A", "Agent B")
        serialized = A2AProtocol.serialize_message(
            new_agent_message("Agent A", "Agent B", "over the wire")
        )
        bus.send_protocol_message(serialized)
        inbox = bus.receive_messages("Agent B")
        assert message_text(inbox[0]) == "over the wire"

    def test_invalid_payload_raises(self):
        with pytest.raises(A2AProtocolError):
            A2AProtocol.deserialize_message("{not json")
