from collections import defaultdict, deque
from collections.abc import Callable
from queue import Empty, Queue
from threading import Event, Lock, Thread
from typing import Any

from my_crew.a2a.message import (
    AgentCard,
    Message,
    MessageKind,
    Task,
    TaskState,
    describe_message,
    message_kind,
    message_receiver,
    message_sender,
    new_agent_message,
    new_task,
    set_task_state,
    task_state_name,
    task_to_dict,
)
from my_crew.a2a.protocol import A2AProtocol
from my_crew.utils.logger import get_logger

logger = get_logger("my_crew.a2a")

Subscriber = Callable[[Message], None]


class CommunicationBus:
    """Thread-safe in-process transport for Google A2A protocol objects.

    Cards, messages, and tasks are official A2A v1 protobuf types; this bus
    provides local routing, per-agent inboxes, task lifecycle tracking, and
    pub-sub in place of an HTTP/gRPC transport.
    """

    BROADCAST = "*"

    _global_subscribers: list[Subscriber] = []

    @classmethod
    def add_global_subscriber(cls, callback: Subscriber) -> None:
        """Register a callback that receives every message from every bus."""
        cls._global_subscribers.append(callback)

    @classmethod
    def remove_global_subscriber(cls, callback: Subscriber) -> None:
        if callback in cls._global_subscribers:
            cls._global_subscribers.remove(callback)

    def __init__(self, auto_start: bool = False):
        self.agent_cards: dict[str, AgentCard] = {}
        self.inboxes: dict[str, deque[Message]] = defaultdict(deque)
        self.messages: list[Message] = []
        self.tasks: dict[str, Task] = {}
        self.subscriptions: dict[str, list[Subscriber]] = defaultdict(list)
        self._dispatch_queue: Queue[Message] = Queue()
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
            self.agent_cards[card.name] = card
            self.inboxes.setdefault(card.name, deque())
        return card

    def list_agent_cards(self) -> list[AgentCard]:
        with self._lock:
            return list(self.agent_cards.values())

    def get_agent_card(self, agent_name: str) -> AgentCard | None:
        with self._lock:
            return self.agent_cards.get(agent_name)

    def create_task(
        self,
        title: str,
        owner: str,
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        task = new_task(title=title, owner=owner, metadata=metadata)
        with self._lock:
            self.tasks[task.id] = task
        return task

    def update_task_status(
        self,
        task_id: str,
        state: "TaskState",
        sender: str = "system",
        receiver: str = BROADCAST,
        content: str | None = None,
    ) -> Message:
        with self._lock:
            task = self.tasks[task_id]
            set_task_state(task, state)

        return self.send_message(
            sender=sender,
            receiver=receiver,
            content=content or f"Task {task_id} is {task_state_name(state)}.",
            kind=MessageKind.STATUS_UPDATE,
            task_id=task_id,
            metadata={"state": task_state_name(state)},
        )

    def send_message(
        self,
        sender: str,
        receiver: str,
        content: str,
        kind: MessageKind = MessageKind.TASK_REQUEST,
        task_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        final: bool = True,
        async_dispatch: bool = False,
    ) -> Message:
        message = new_agent_message(
            sender=sender,
            receiver=receiver,
            content=content,
            kind=kind,
            task_id=task_id,
            metadata=metadata,
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
    ) -> Message:
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
        kind: MessageKind = MessageKind.EVENT,
        task_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        return self.send_message(
            sender=sender,
            receiver=self.BROADCAST,
            content=content,
            kind=kind,
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
    ) -> list[Message]:
        messages = []
        for index, chunk in enumerate(chunks):
            messages.append(
                self.send_message(
                    sender=sender,
                    receiver=receiver,
                    content=chunk,
                    kind=MessageKind.STREAM_CHUNK,
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
        agent_name: str,
        max_messages: int | None = None,
    ) -> list[Message]:
        with self._lock:
            inbox = self.inboxes[agent_name]
            limit = max_messages or len(inbox)
            messages = []
            for _ in range(min(limit, len(inbox))):
                messages.append(inbox.popleft())
            return messages

    def get_messages(self) -> list[Message]:
        with self._lock:
            return list(self.messages)

    def get_task(self, task_id: str) -> Task | None:
        with self._lock:
            return self.tasks.get(task_id)

    def task_snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [task_to_dict(task) for task in self.tasks.values()]

    def _dispatch_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                message = self._dispatch_queue.get(timeout=0.2)
            except Empty:
                continue

            self._route(message)
            self._dispatch_queue.task_done()

    def _route(self, message: Message) -> None:
        A2AProtocol.validate_message(message)
        sender = message_sender(message)
        receiver = message_receiver(message)
        subscribers = []

        with self._lock:
            self.messages.append(message)

            if message.task_id and message.task_id in self.tasks:
                self.tasks[message.task_id].history.append(message)

            if receiver == self.BROADCAST:
                for agent_name in self.agent_cards:
                    if agent_name != sender:
                        self.inboxes[agent_name].append(message)
            else:
                self.inboxes[receiver].append(message)

            subscribers.extend(self.subscriptions.get(receiver, []))
            subscribers.extend(self.subscriptions.get(self.BROADCAST, []))
            subscribers.extend(self.subscriptions.get(message_kind(message), []))

        logger.info(describe_message(message))

        for callback in [*subscribers, *self._global_subscribers]:
            callback(message)
