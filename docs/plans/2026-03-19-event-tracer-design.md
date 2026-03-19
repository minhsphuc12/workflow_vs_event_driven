# Event Tracer (Event-driven demo) — Design

**Goal:** Increase visibility of the end-to-end event-driven flow by producing (1) structured logs and (2) a Mermaid visualization that includes both Events and Handlers, exported to `tmp/` per `application_id`.

**Non-goals:**
- Distributed tracing across processes/services (this demo is synchronous, in-memory).
- Persistent storage, UI dashboard, or live web visualization.
- Backwards-compatible tracing format guarantees (we can iterate).

## Current state (baseline)

- `event_driven_approach/event_bus.py` keeps a `trace: List[PublishedEvent]` containing only `publish()` calls.
- Handlers already emit console logs (e.g. `"[EventDriven] CreditHandler <= IdentityVerified"`), but these logs are not structured, not correlated, and do not capture durations.

## Requirements

- **Log detail**: include payload summary (at least `application_id`; plus common fields like `reason`, `credit_score`, `risk_score`, `message`) and per-handler duration.
- **Visualization**: Mermaid graph that includes **Event nodes** and **Handler nodes**:
  - Edges `Event -> Handler` (handler consumed event)
  - Edges `Handler -> Event` (handler published subsequent event)
- **Output**: export files to `tmp/`:
  - `tmp/event_trace_<application_id>.jsonl` (structured trace log)
  - `tmp/event_trace_<application_id>.md` (Mermaid + short summary)
- **Minimal intrusion**: avoid touching each handler method; prefer instrumentation at the bus layer.

## Design overview

### Key idea: instrument the bus, not individual handlers

We extend `EventBus` to:
- wrap subscribed handlers (on `subscribe`) to capture:
  - handler name
  - `handle_start` / `handle_end`
  - duration (ms)
  - errors (if thrown)
- capture `publish` events with correlation data so we can build a graph:
  - which handler published this event (if any)
  - which event triggered the handler (parent edge)

This yields a complete, correlated execution trace without modifying each handler.

### Trace correlation model

We introduce a lightweight context stack inside `EventBus`:
- When a handler starts, push an “active handler context”:
  - `trace_id` (per scenario/run)
  - `application_id` (derived from incoming event payload if present)
  - `handler_name`
  - `consumed_event_name`
  - `handler_span_id` (unique id)
- When `publish()` is called:
  - record `published_by_handler_span_id` (if within a handler)
  - record `parent_consumed_event_name` (for graph linking)

Because this demo is synchronous, a simple stack is sufficient and deterministic.

### Data model (trace records)

Each record is a JSON object written as one line (`jsonl`):

- `kind`: one of
  - `publish`
  - `handle_start`
  - `handle_end`
  - `handle_error`
- Common fields:
  - `ts_ms`: unix epoch milliseconds
  - `trace_id`: unique id per scenario run (string)
  - `application_id`: best-effort correlation key (string | null)
  - `event_name`: event class name (string | null)
  - `handler_name`: `"{ClassName}.{method_name}"` (string | null)
  - `span_id`: unique id for this record’s span (string)
  - `parent_span_id`: link to parent handler span (string | null)
  - `payload_summary`: dict (small, bounded)
  - `duration_ms`: number | null (for handle_end / handle_error)
  - `error`: string | null

### Payload summary rules

For any payload (event object), extract:
- If attribute exists: `application_id`
- If attribute exists: `reason`, `credit_score`, `risk_score`, `message`
- Additionally: include a bounded representation of other primitive fields if needed (string/int/float/bool), but cap:
  - max keys: 8
  - max string length: 200

### Output writer

We add an `EventTracer` component (small module) responsible for:
- buffering trace records in memory (for rendering)
- appending to `tmp/event_trace_<application_id>.jsonl`
- producing `tmp/event_trace_<application_id>.md` that includes:
  - Mermaid graph (`flowchart TD`)
  - Summary table (handlers sorted by total duration; optionally include counts)
  - Link hints: “paste Mermaid block into a viewer” (no web tool needed)

We keep this component separated from `EventBus` so the bus stays generic.

### Mermaid graph generation

We render nodes with stable ids:
- Event node id: `E_<EventName>`
- Handler node id: `H_<HandlerName>` (sanitize non-alphanumerics to `_`)

Edges:
- On `handle_start`: create `E_incoming -> H_handler`
- On `publish` within handler: create `H_handler -> E_published`

We generate the graph per `application_id` and per run (trace_id), so multi-scenario runs produce separate files.

## Integration points

- Modify: `event_driven_approach/event_bus.py`
  - Add tracing hooks and a pluggable tracer sink (`set_tracer(...)` or constructor param).
- Create: `event_driven_approach/event_tracer.py`
  - Trace record types, jsonl writer, mermaid renderer.
- Modify: `event_driven_approach/main.py`
  - Ensure `tmp/` exists.
  - Configure the bus with tracer.
  - After scenario completes, call tracer to export `.md` (and flush logs).

## Error handling

- If a handler raises an exception:
  - record `handle_error` with duration up to error
  - re-raise to preserve current behavior (or keep consistent with current demo behavior)
- If file output fails:
  - tracer should fail “softly” (print a warning) but not crash the scenario by default.

## Testing strategy (TDD)

Add tests to validate:
- A handler call produces `handle_start` then `handle_end` with duration.
- `publish` inside a handler is linked to that handler (parent span id present).
- Mermaid output contains expected nodes/edges for a simple 2-step pipeline.
- Payload summary includes `application_id` and bounded fields.

Focus tests on the tracer + bus instrumentation with a minimal fake event and handler.

## Open questions / future extensions

- Support for multiple application_ids interleaved in one run (not needed now).
- Optional filtering / grouping (e.g., collapse repeated notifications).
- ANSI-colored console rendering (not required; files are the source of truth).

