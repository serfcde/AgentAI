import pytest

from my_crew.a2a.communication import CommunicationBus
from my_crew.a2a.message import (
    AgentCard,
    AgentMessage,
    MessageType,
    TaskStatus,
)
from my_crew.a2a.protocol import A2AProtocol, A2AProtocolError


def make_bus(*agent_ids: str) -> CommunicationBus:
    bus = CommunicationBus()
    for agent_id in agent_ids:
        bus.register_agent(
            AgentCard(agent_id=agent_id, name=agent_id, description=agent_id)
        )
    return bus


class TestRegistration:
    def test_register_and_list_agents(self):
        bus = make_bus("Agent A", "Agent B")
        cards = bus.list_agent_cards()
        assert {card.agent_id for card in cards} == {"Agent A", "Agent B"}

    def test_invalid_card_is_rejected(self):
        bus = CommunicationBus()
        with pytest.raises(A2AProtocolError):
            bus.register_agent(AgentCard(agent_id="", name="", description=""))


class TestMessaging:
    def test_direct_message_lands_in_receiver_inbox(self):
        bus = make_bus("Agent A", "Agent B")
        bus.send_message("Agent A", "Agent B", "hello")

        inbox = bus.receive_messages("Agent B")
        assert len(inbox) == 1
        assert inbox[0].content == "hello"
        assert inbox[0].sender == "Agent A"

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
        received: list[AgentMessage] = []
        bus.subscribe("Agent B", received.append)

        bus.send_message("Agent A", "Agent B", "ping")
        assert len(received) == 1
        assert received[0].content == "ping"

    def test_stream_message_marks_last_chunk_final(self):
        bus = make_bus("Agent A", "Agent B")
        messages = bus.stream_message(
            "Agent A", "Agent B", ["chunk one", "chunk two", "chunk three"]
        )

        assert [m.final for m in messages] == [False, False, True]
        assert all(m.message_type == MessageType.STREAM_CHUNK for m in messages)
        assert [m.metadata["chunk_index"] for m in messages] == [0, 1, 2]


class TestTasks:
    def test_create_task_and_status_update(self):
        bus = make_bus("Agent A", "Agent B")
        task = bus.create_task("demo task", owner="Agent A")
        assert bus.get_task(task.task_id).status == TaskStatus.SUBMITTED

        bus.update_task_status(task.task_id, TaskStatus.COMPLETED, sender="Agent A")
        assert bus.get_task(task.task_id).status == TaskStatus.COMPLETED

    def test_task_records_message_ids(self):
        bus = make_bus("Agent A", "Agent B")
        task = bus.create_task("demo task", owner="Agent A")
        message = bus.send_message(
            "Agent A", "Agent B", "work update", task_id=task.task_id
        )

        assert message.message_id in bus.get_task(task.task_id).messages

    def test_task_snapshot_serializes(self):
        bus = make_bus("Agent A")
        bus.create_task("demo task", owner="Agent A", metadata={"k": "v"})
        snapshot = bus.task_snapshot()
        assert len(snapshot) == 1
        assert snapshot[0]["metadata"] == {"k": "v"}
        assert snapshot[0]["status"] == "submitted"


class TestProtocol:
    def test_message_roundtrip(self):
        message = AgentMessage(
            sender="Agent A",
            receiver="Agent B",
            content="hello",
            message_type=MessageType.TASK_RESPONSE,
            status=TaskStatus.WORKING,
            metadata={"phase": "research"},
        )
        restored = A2AProtocol.deserialize_message(
            A2AProtocol.serialize_message(message)
        )
        assert restored == message

    def test_agent_card_roundtrip(self):
        card = AgentCard(
            agent_id="Agent A", name="Agent A", description="test agent"
        )
        restored = A2AProtocol.deserialize_agent_card(
            A2AProtocol.serialize_agent_card(card)
        )
        assert restored == card

    def test_bus_accepts_serialized_protocol_message(self):
        bus = make_bus("Agent A", "Agent B")
        serialized = A2AProtocol.serialize_message(
            AgentMessage(sender="Agent A", receiver="Agent B", content="over the wire")
        )
        bus.send_protocol_message(serialized)
        inbox = bus.receive_messages("Agent B")
        assert inbox[0].content == "over the wire"
