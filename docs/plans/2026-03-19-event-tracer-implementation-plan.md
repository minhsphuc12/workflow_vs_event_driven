# Event Tracer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an Event Tracer to the event-driven demo that exports structured logs (`.jsonl`) and a Mermaid visualization (`.md`) including Event+Handler nodes to `tmp/` per `application_id`.

**Architecture:** Instrument `EventBus.subscribe()` and `EventBus.publish()` to emit trace records to a pluggable tracer sink. Use an `EventTracer` module to buffer records, write `jsonl`, and render Mermaid/summary markdown.

**Tech Stack:** Python 3 (stdlib only), `dataclasses`, `time`, `json`, `pathlib`.

---

### Task 1: Add tracer record types + payload summary helper

**Files:**
- Create: `event_driven_approach/event_tracer.py`
- Test: `tests/test_event_tracer.py`

**Step 1: Write the failing test**

Create `tests/test_event_tracer.py`:

```python
from dataclasses import dataclass

from event_driven_approach.event_tracer import summarize_payload


@dataclass
class Evt:
    application_id: str
    reason: str
    credit_score: int
    message: str


def test_summarize_payload_picks_common_fields_and_bounds() -> None:
    evt = Evt(
        application_id="app-1",
        reason="some reason",
        credit_score=700,
        message="x" * 500,
    )
    s = summarize_payload(evt)
    assert s["application_id"] == "app-1"
    assert s["reason"] == "some reason"
    assert s["credit_score"] == 700
    assert isinstance(s["message"], str)
    assert len(s["message"]) <= 200
```

**Step 2: Run test to verify it fails**

Run:
- `python -m pytest -q`

Expected:
- FAIL because `event_driven_approach.event_tracer` or `summarize_payload` does not exist.

**Step 3: Write minimal implementation**

Create `event_driven_approach/event_tracer.py` with:
- `def summarize_payload(payload: object) -> dict[str, object]`
  - extract the common fields if present
  - bound message length to 200

**Step 4: Run test to verify it passes**

Run:
- `python -m pytest -q`

Expected:
- PASS for the new test.

**Step 5: Commit**

```bash
git add event_driven_approach/event_tracer.py tests/test_event_tracer.py
git commit -m "feat: add payload summarizer for tracing"
```

---

### Task 2: Add basic `EventTracer` buffer + JSONL writer

**Files:**
- Modify: `event_driven_approach/event_tracer.py`
- Test: `tests/test_event_tracer.py`

**Step 1: Write the failing test**

Append to `tests/test_event_tracer.py`:

```python
import json
from pathlib import Path

from event_driven_approach.event_tracer import EventTracer


def test_event_tracer_writes_jsonl(tmp_path: Path) -> None:
    t = EventTracer(output_dir=tmp_path)
    t.record(
        kind="publish",
        trace_id="t1",
        application_id="app-1",
        event_name="ApplicationSubmitted",
        handler_name=None,
        span_id="s1",
        parent_span_id=None,
        payload_summary={"application_id": "app-1"},
        duration_ms=None,
        error=None,
    )
    path = t.flush_jsonl(application_id="app-1")
    assert path.exists()
    lines = path.read_text().splitlines()
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert obj["kind"] == "publish"
    assert obj["application_id"] == "app-1"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q`

Expected: FAIL because `EventTracer`/`flush_jsonl` do not exist.

**Step 3: Write minimal implementation**

In `event_driven_approach/event_tracer.py`:
- Define a `TraceRecord` dataclass
- Implement `EventTracer`:
  - constructor with `output_dir: Path`
  - `record(...)` appends to buffer
  - `flush_jsonl(application_id)` writes only matching records to `event_trace_<application_id>.jsonl`
  - returns path

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add event_driven_approach/event_tracer.py tests/test_event_tracer.py
git commit -m "feat: add jsonl event tracer writer"
```

---

### Task 3: Instrument `EventBus` to emit `publish` records

**Files:**
- Modify: `event_driven_approach/event_bus.py`
- Modify: `event_driven_approach/event_tracer.py`
- Test: `tests/test_event_bus_tracing.py`

**Step 1: Write the failing test**

Create `tests/test_event_bus_tracing.py`:

```python
from dataclasses import dataclass

from event_driven_approach.event_bus import EventBus
from event_driven_approach.event_tracer import EventTracer


@dataclass
class E:
    application_id: str


def test_publish_emits_trace_record(tmp_path) -> None:
    bus = EventBus()
    tracer = EventTracer(output_dir=tmp_path)
    bus.set_tracer(tracer, trace_id="t1")

    bus.publish(E("app-1"))

    p = tracer.flush_jsonl("app-1")
    text = p.read_text()
    assert "publish" in text
    assert "E" in text
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q`

Expected: FAIL because `set_tracer` doesn’t exist and publish doesn’t emit records.

**Step 3: Write minimal implementation**

In `event_driven_approach/event_bus.py`:
- Add optional tracer sink and `trace_id`
- Implement `set_tracer(tracer, trace_id: str)`
- On `publish(event)`:
  - create record `kind="publish"`, `event_name=type(event).__name__`
  - extract `application_id` via `getattr(event, "application_id", None)`
  - include `payload_summary=summarize_payload(event)`

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add event_driven_approach/event_bus.py tests/test_event_bus_tracing.py
git commit -m "feat: trace published events in event bus"
```

---

### Task 4: Instrument `subscribe()` to wrap handlers with start/end + duration

**Files:**
- Modify: `event_driven_approach/event_bus.py`
- Test: `tests/test_event_bus_tracing.py`

**Step 1: Write the failing test**

Append to `tests/test_event_bus_tracing.py`:

```python
def test_handler_span_has_duration_and_links_publish(tmp_path) -> None:
    bus = EventBus()
    tracer = EventTracer(output_dir=tmp_path)
    bus.set_tracer(tracer, trace_id="t1")

    published = []

    def handler(evt: E) -> None:
        published.append("handled")
        bus.publish(E(evt.application_id))

    bus.subscribe(E, handler)
    bus.publish(E("app-1"))

    p = tracer.flush_jsonl("app-1")
    text = p.read_text()
    assert "handle_start" in text
    assert "handle_end" in text
    assert "duration_ms" in text
    # linked publish should have parent_span_id populated
    assert "parent_span_id" in text
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q`

Expected: FAIL because handler wrapping and parent-span linking is missing.

**Step 3: Write minimal implementation**

In `event_driven_approach/event_bus.py`:
- On `subscribe(event_type, handler)` store a wrapper that:
  - computes handler name:
    - if handler is bound method: `handler.__self__.__class__.__name__ + "." + handler.__name__`
    - else: `handler.__name__`
  - emits `handle_start` (span id)
  - pushes active span id as current context (stack)
  - calls handler
  - emits `handle_end` with duration (ms)
  - pops context even on error
  - on exception, emits `handle_error` and re-raises
- On `publish(event)` include `parent_span_id` if there is an active handler span.

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add event_driven_approach/event_bus.py tests/test_event_bus_tracing.py
git commit -m "feat: trace handler spans and link publishes"
```

---

### Task 5: Render Mermaid graph and export markdown

**Files:**
- Modify: `event_driven_approach/event_tracer.py`
- Test: `tests/test_event_tracer_mermaid.py`

**Step 1: Write the failing test**

Create `tests/test_event_tracer_mermaid.py`:

```python
from pathlib import Path

from event_driven_approach.event_tracer import EventTracer


def test_mermaid_contains_event_and_handler_edges(tmp_path: Path) -> None:
    t = EventTracer(output_dir=tmp_path)
    t.record(
        kind="handle_start",
        trace_id="t1",
        application_id="app-1",
        event_name="ApplicationSubmitted",
        handler_name="Router.on_submitted",
        span_id="h1",
        parent_span_id=None,
        payload_summary={"application_id": "app-1"},
        duration_ms=None,
        error=None,
    )
    t.record(
        kind="publish",
        trace_id="t1",
        application_id="app-1",
        event_name="IdentityVerificationRequested",
        handler_name="Router.on_submitted",
        span_id="p1",
        parent_span_id="h1",
        payload_summary={"application_id": "app-1"},
        duration_ms=None,
        error=None,
    )
    md = t.render_markdown(application_id="app-1")
    assert "flowchart TD" in md
    assert "ApplicationSubmitted" in md
    assert "Router.on_submitted" in md
    # expects both directions to exist
    assert "-->" in md
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q`

Expected: FAIL because `render_markdown` doesn’t exist.

**Step 3: Write minimal implementation**

In `event_driven_approach/event_tracer.py`:
- Implement `render_markdown(application_id)`:
  - build edges `Event -> Handler` from `handle_start`
  - build edges `Handler -> Event` from `publish` (where parent_span_id exists)
  - output Mermaid code block and a minimal summary section
- Implement `flush_markdown(application_id)` writing `event_trace_<application_id>.md`.

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add event_driven_approach/event_tracer.py tests/test_event_tracer_mermaid.py
git commit -m "feat: render mermaid handler graph for traces"
```

---

### Task 6: Wire tracer into the demo entrypoint and ensure `tmp/` output

**Files:**
- Modify: `event_driven_approach/main.py`
- (Optional) Modify: `event_driven_approach/event_driven_README.md`
- Test: manual run

**Step 1: Write a failing “smoke” test (optional)**

If we want an automated smoke test, add:
- `tests/test_demo_smoke.py` that runs a minimal scenario without sleeping (set delays to 0).

Otherwise skip and do a manual run.

**Step 2: Implement wiring**

In `event_driven_approach/main.py`:
- Ensure `tmp/` exists at repo root (use `Path("tmp").mkdir(parents=True, exist_ok=True)`).
- Create `EventTracer(output_dir=Path("tmp"))` per scenario run.
- Set tracer on the bus with a new `trace_id` (e.g. uuid4).
- After `bus.publish(ApplicationSubmitted(...))` completes:
  - call `tracer.flush_jsonl(application_id)`
  - call `tracer.flush_markdown(application_id)`
- Keep existing console output intact (the tracer is additive).

**Step 3: Manual verification**

Run:
- `python -m event_driven_approach.main`

Expected:
- for each scenario, you see files in `tmp/`:
  - `event_trace_<application_id>.jsonl`
  - `event_trace_<application_id>.md`
and the `.md` contains a Mermaid `flowchart TD` with both event and handler nodes.

**Step 4: Commit**

```bash
git add event_driven_approach/main.py event_driven_approach/event_driven_README.md
git commit -m "feat: export event tracer logs and mermaid to tmp"
```

