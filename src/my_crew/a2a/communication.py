from collections import defaultdict, deque
from collections.abc import Callable
from queue import Empty, Queue
from threading import Event, Lock, Thread
from typing import Any
from uuid import uuid4

from my_crew.a2a.message import (
    A2ATask,
    AgentCard,
    AgentMessage,
    MessageType,
    TaskStatus,
)
from my_crew.a2a.protocol import A2AProtocol
from my_crew.utils.logger import get_logger


logger = get_logger("my_crew.a2a")

Subscriber = Callable[[AgentMessage], None]


class CommunicationBus:
    """Thread-safe local A2A backbone with routing, inboxes, and pub-sub."""

    BROADCAST = "*"

    def __init__(self, auto_start: bool = False):
        self.agent_cards: dict[str, AgentCard] = {}
        self.inboxes: dict[str, deque[AgentMessage]] = defaultdict(deque)
        self.messages: list[AgentMessage] = []
        self.tasks: dict[str, A2ATask] = {}
        self.subscriptions: dict[str, list[Subscriber]] = defaultdict(list)
        self._dispatch_queue: Queue[AgentMessage] = Queue()
        self._lock = Lock()
        self._stop_event = Event()
        self._dispatcher: Thread | None = None

        if auto_start:
            self.start()

    def start(self) -> None:
        if self._dispatcher and self._dispatcher.is_alive():
            return

        self._stop_event.clear()
        self._dispatcher = Thread(
            target=self._dispatch_loop,
            name="a2a-dispatcher",
            daemon=True,
        )
        self._dispatcher.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._dispatcher:
            self._dispatcher.join(timeout=2)

    def register_agent(self, card: AgentCard) -> AgentCard:
        A2AProtocol.validate_agent_card(card)
        with self._lock:
            self.agent_cards[card.agent_id] = card
            self.inboxes.setdefault(card.agent_id, deque())
        return card

    def list_agent_cards(self) -> list[AgentCard]:
        with self._lock:
            return list(self.agent_cards.values())

    def get_agent_card(self, agent_id: str) -> AgentCard | None:
        with self._lock:
            return self.agent_cards.get(agent_id)

    def create_task(
        self,
        title: str,
        owner: str,
        metadata: dict[str, Any] | None = None,
    ) -> A2ATask:
        task = A2ATask(
            task_id=str(uuid4()),
            title=title,
            owner=owner,
            metadata=metadata or {},
        )
        with self._lock:
            self.tasks[task.task_id] = task
        return task

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        sender: str = "system",
        receiver: str = BROADCAST,
        content: str | None = None,
    ) -> AgentMessage:
        with self._lock:
            task = self.tasks[task_id]
            task.set_status(status)

        return self.send_message(
            sender=sender,
            receiver=receiver,
            content=content or f"Task {task_id} is {status.value}.",
            message_type=MessageType.STATUS_UPDATE,
            task_id=task_id,
            status=status,
        )

    def send_message(
        self,
        sender: str,
        receiver: str,
        content: str,
        message_type: MessageType = MessageType.TASK_REQUEST,
        task_id: str | None = None,
        correlation_id: str | None = None,
        status: TaskStatus | None = None,
        metadata: dict[str, Any] | None = None,
        final: bool = True,
        async_dispatch: bool = False,
    ) -> AgentMessage:
        message = AgentMessage(
            sender=sender,
            receiver=receiver,
            content=content,
            message_type=message_type,
            task_id=task_id,
            correlation_id=correlation_id,
            status=status,
            metadata=metadata or {},
            final=final,
        )
        A2AProtocol.validate_message(message)

        if async_dispatch:
            self.start()
            self._dispatch_queue.put(message)
        else:
            self._route(message)

        return message

    def send_protocol_message(
        self,
        serialized_message: str,
        async_dispatch: bool = False,
    ) -> AgentMessage:
        message = A2AProtocol.deserialize_message(serialized_message)
        if async_dispatch:
            self.start()
            self._dispatch_queue.put(message)
        else:
            self._route(message)
        return message

    def broadcast(
        self,
        sender: str,
        content: str,
        message_type: MessageType = MessageType.EVENT,
        task_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentMessage:
        return self.send_message(
            sender=sender,
            receiver=self.BROADCAST,
            content=content,
            message_type=message_type,
            task_id=task_id,
            metadata=metadata,
        )

    def stream_message(
        self,
        sender: str,
        receiver: str,
        chunks: list[str],
        task_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[AgentMessage]:
        messages = []
        for index, chunk in enumerate(chunks):
            messages.append(
                self.send_message(
                    sender=sender,
                    receiver=receiver,
                    content=chunk,
                    message_type=MessageType.STREAM_CHUNK,
                    task_id=task_id,
                    metadata={
                        **(metadata or {}),
                        "chunk_index": index,
                        "chunk_count": len(chunks),
                    },
                    final=index == len(chunks) - 1,
                )
            )
        return messages

    def subscribe(self, topic: str, callback: Subscriber) -> None:
        with self._lock:
            self.subscriptions[topic].append(callback)

    def receive_messages(
        self,
        agent_id: str,
        max_messages: int | None = None,
    ) -> list[AgentMessage]:
        with self._lock:
            inbox = self.inboxes[agent_id]
            limit = max_messages or len(inbox)
            messages = []
            for _ in range(min(limit, len(inbox))):
                messages.append(inbox.popleft())
            return messages

    def get_messages(self) -> list[AgentMessage]:
        with self._lock:
            return list(self.messages)

    def get_task(self, task_id: str) -> A2ATask | None:
        with self._lock:
            return self.tasks.get(task_id)

    def task_snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [task.to_dict() for task in self.tasks.values()]

    def _dispatch_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                message = self._dispatch_queue.get(timeout=0.2)
            except Empty:
                continue

            self._route(message)
            self._dispatch_queue.task_done()

    def _route(self, message: AgentMessage) -> None:
        A2AProtocol.validate_message(message)
        subscribers = []

        with self._lock:
            self.messages.append(message)

            if message.task_id and message.task_id in self.tasks:
                self.tasks[message.task_id].add_message(message.message_id)

            if message.receiver == self.BROADCAST:
                for agent_id in self.agent_cards:
                    if agent_id != message.sender:
                        self.inboxes[agent_id].append(message)
            else:
                self.inboxes[message.receiver].append(message)

            subscribers.extend(self.subscriptions.get(message.receiver, []))
            subscribers.extend(self.subscriptions.get(self.BROADCAST, []))
            subscribers.extend(self.subscriptions.get(message.message_type.value, []))

        logger.info(str(message))

        for callback in subscribers:
            callback(message)
