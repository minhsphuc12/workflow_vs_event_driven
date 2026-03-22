from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import time
import uuid
from typing import Any, Callable, DefaultDict, Dict, List, Optional, Type, TypeVar

from event_driven_approach.event_tracer import EventTracer, summarize_payload


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
        self._tracer: Optional[EventTracer] = None
        self._trace_id: Optional[str] = None
        self._active_handler_spans: List[tuple[str, str]] = []

    def subscribe(self, event_type: Type[TEvent], handler: Callable[[TEvent], None]) -> None:
        """
        Subscribe a handler function to a specific event type.

        When an event of the given type is published, the provided handler will be
        called synchronously with the event instance as an argument. If tracing is
        enabled (via set_tracer), the handler executions are traced for observability.

        Args:
            event_type: The type of event to listen for.
            handler: A callable that takes a single event object of type event_type.
        """
        def handler_name() -> str:
            if hasattr(handler, "__self__") and getattr(handler, "__self__", None) is not None:
                return f"{handler.__self__.__class__.__name__}.{handler.__name__}"  # type: ignore[attr-defined]
            return getattr(handler, "__name__", "handler")

        def wrapped(evt: TEvent) -> None:
            if self._tracer is None or self._trace_id is None:
                handler(evt)
                return

            span_id = uuid.uuid4().hex
            name = handler_name()
            application_id = getattr(evt, "application_id", None)
            event_name = type(evt).__name__

            self._tracer.record(
                kind="handle_start",
                trace_id=self._trace_id,
                application_id=application_id,
                event_name=event_name,
                handler_name=name,
                span_id=span_id,
                parent_span_id=self._active_handler_spans[-1][0] if self._active_handler_spans else None,
                payload_summary=summarize_payload(evt),
                duration_ms=None,
                error=None,
            )

            t0 = time.perf_counter()
            self._active_handler_spans.append((span_id, name))
            try:
                handler(evt)
                dt_ms = (time.perf_counter() - t0) * 1000.0
                self._tracer.record(
                    kind="handle_end",
                    trace_id=self._trace_id,
                    application_id=application_id,
                    event_name=event_name,
                    handler_name=name,
                    span_id=span_id,
                    parent_span_id=self._active_handler_spans[-2][0] if len(self._active_handler_spans) > 1 else None,
                    payload_summary=summarize_payload(evt),
                    duration_ms=dt_ms,
                    error=None,
                )
            except Exception as e:  # noqa: BLE001 - demo tracer
                dt_ms = (time.perf_counter() - t0) * 1000.0
                self._tracer.record(
                    kind="handle_error",
                    trace_id=self._trace_id,
                    application_id=application_id,
                    event_name=event_name,
                    handler_name=name,
                    span_id=span_id,
                    parent_span_id=self._active_handler_spans[-2][0] if len(self._active_handler_spans) > 1 else None,
                    payload_summary=summarize_payload(evt),
                    duration_ms=dt_ms,
                    error=str(e),
                )
                raise
            finally:
                # best-effort pop (keep stack consistent)
                if self._active_handler_spans and self._active_handler_spans[-1][0] == span_id:
                    self._active_handler_spans.pop()

        self._handlers[event_type].append(wrapped)  # type: ignore[arg-type]

    def set_tracer(self, tracer: EventTracer, *, trace_id: Optional[str] = None) -> None:
        self._tracer = tracer
        self._trace_id = trace_id or uuid.uuid4().hex

    def publish(self, event: Any) -> None:
        self.trace.append(PublishedEvent(type(event).__name__, event))
        if self._tracer is not None and self._trace_id is not None:
            application_id = getattr(event, "application_id", None)
            parent_span_id = self._active_handler_spans[-1][0] if self._active_handler_spans else None
            active_handler_name = self._active_handler_spans[-1][1] if self._active_handler_spans else None
            self._tracer.record(
                kind="publish",
                trace_id=self._trace_id,
                application_id=application_id,
                event_name=type(event).__name__,
                handler_name=active_handler_name,
                span_id=uuid.uuid4().hex,
                parent_span_id=parent_span_id,
                payload_summary=summarize_payload(event),
                duration_ms=None,
                error=None,
            )
        for handler in list(self._handlers[type(event)]):
            handler(event)

    def subscriptions(self) -> Dict[str, int]:
        return {t.__name__: len(hs) for t, hs in self._handlers.items()}

