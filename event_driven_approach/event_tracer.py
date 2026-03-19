from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import time
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


def _cap_string(value: str, *, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 1] + "…"


def summarize_payload(payload: object) -> Dict[str, Any]:
    """
    Best-effort payload summarizer for tracing/logging.

    Keep output small and stable-ish for demo purposes.
    """

    out: Dict[str, Any] = {}

    for key in ("application_id", "reason", "credit_score", "risk_score", "message"):
        if hasattr(payload, key):
            value = getattr(payload, key)
            if isinstance(value, str):
                out[key] = _cap_string(value, max_len=200)
            else:
                out[key] = value

    return out


@dataclass(frozen=True, slots=True)
class TraceRecord:
    kind: str
    ts_ms: int
    trace_id: str
    application_id: Optional[str]
    event_name: Optional[str]
    handler_name: Optional[str]
    span_id: str
    parent_span_id: Optional[str]
    payload_summary: Dict[str, Any]
    duration_ms: Optional[float]
    error: Optional[str]


class EventTracer:
    def __init__(self, *, output_dir: Path):
        self._output_dir = output_dir
        self._records: List[TraceRecord] = []

    def record(
        self,
        *,
        kind: str,
        trace_id: str,
        application_id: Optional[str],
        event_name: Optional[str],
        handler_name: Optional[str],
        span_id: str,
        parent_span_id: Optional[str],
        payload_summary: Dict[str, Any],
        duration_ms: Optional[float],
        error: Optional[str],
    ) -> None:
        self._records.append(
            TraceRecord(
                kind=kind,
                ts_ms=int(time.time() * 1000),
                trace_id=trace_id,
                application_id=application_id,
                event_name=event_name,
                handler_name=handler_name,
                span_id=span_id,
                parent_span_id=parent_span_id,
                payload_summary=payload_summary,
                duration_ms=duration_ms,
                error=error,
            )
        )

    def _iter_for_application(self, application_id: str) -> Iterable[TraceRecord]:
        for r in self._records:
            if r.application_id == application_id:
                yield r

    def flush_jsonl(self, *, application_id: str) -> Path:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        path = self._output_dir / f"event_trace_{application_id}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for r in self._iter_for_application(application_id):
                f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
        return path

    def _node_id_event(self, event_name: str) -> str:
        return f"E_{event_name}"

    def _node_id_handler(self, handler_name: str) -> str:
        safe = "".join(ch if ch.isalnum() else "_" for ch in handler_name)
        return f"H_{safe}"

    def render_markdown(self, *, application_id: str) -> str:
        records = list(self._iter_for_application(application_id))

        edges: Set[Tuple[str, str]] = set()
        labels: Dict[str, str] = {}
        handler_durations: Dict[str, float] = {}

        for r in records:
            if r.kind == "handle_start" and r.event_name and r.handler_name:
                e_id = self._node_id_event(r.event_name)
                h_id = self._node_id_handler(r.handler_name)
                labels[e_id] = r.event_name
                labels[h_id] = r.handler_name
                edges.add((e_id, h_id))

            if r.kind == "publish" and r.event_name and r.handler_name:
                h_id = self._node_id_handler(r.handler_name)
                e_id = self._node_id_event(r.event_name)
                labels[h_id] = r.handler_name
                labels[e_id] = r.event_name
                edges.add((h_id, e_id))

            if r.kind == "handle_end" and r.handler_name and r.duration_ms is not None:
                handler_durations[r.handler_name] = handler_durations.get(r.handler_name, 0.0) + float(r.duration_ms)

        mermaid_lines: List[str] = ["flowchart TD"]
        for node_id, label in sorted(labels.items()):
            mermaid_lines.append(f'  {node_id}["{label}"]')
        for a, b in sorted(edges):
            mermaid_lines.append(f"  {a} --> {b}")

        mermaid = "\n".join(mermaid_lines)

        summary_lines: List[str] = []
        if handler_durations:
            summary_lines.extend(
                [
                    "## Handler duration summary",
                    "",
                    "| handler | total_ms |",
                    "|---|---:|",
                ]
            )
            for name, total in sorted(handler_durations.items(), key=lambda kv: kv[1], reverse=True):
                summary_lines.append(f"| `{name}` | {total:.2f} |")
            summary_lines.append("")

        return "\n".join(
            [
                f"# Event Trace: {application_id}",
                "",
                "```mermaid",
                mermaid,
                "```",
                "",
                *summary_lines,
            ]
        )

    def flush_markdown(self, *, application_id: str) -> Path:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        path = self._output_dir / f"event_trace_{application_id}.md"
        path.write_text(self.render_markdown(application_id=application_id), encoding="utf-8")
        return path

