from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, DefaultDict, Dict, List, Type, TypeVar


TEvent = TypeVar("TEvent")
Handler = Callable[[Any], None]


@dataclass(slots=True)
class PublishedEvent:
    name: str
    payload: Any


class EventBus:
    """
    Minimal in-memory pub/sub bus (synchronous) for learning.

    Notes:
    - publish() calls handlers immediately (no threads/async).
    - We keep a trace of published events to make the flow visible.
    """

    def __init__(self) -> None:
        self._handlers: DefaultDict[Type[Any], List[Handler]] = defaultdict(list)
        self.trace: List[PublishedEvent] = []

    def subscribe(self, event_type: Type[TEvent], handler: Callable[[TEvent], None]) -> None:
        self._handlers[event_type].append(handler)  # type: ignore[arg-type]

    def publish(self, event: Any) -> None:
        self.trace.append(PublishedEvent(type(event).__name__, event))
        for handler in list(self._handlers[type(event)]):
            handler(event)

    def subscriptions(self) -> Dict[str, int]:
        return {t.__name__: len(hs) for t, hs in self._handlers.items()}

