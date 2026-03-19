import json
import unittest
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from event_driven_approach.event_bus import EventBus
from event_driven_approach.event_tracer import EventTracer


@dataclass
class E:
    application_id: str


@dataclass
class E2:
    application_id: str


class TestEventBusTracing(unittest.TestCase):
    def test_publish_emits_trace_record(self) -> None:
        with TemporaryDirectory() as d:
            tmp_path = Path(d)
            bus = EventBus()
            tracer = EventTracer(output_dir=tmp_path)
            bus.set_tracer(tracer, trace_id="t1")

            bus.publish(E("app-1"))

            p = tracer.flush_jsonl(application_id="app-1")
            lines = p.read_text().splitlines()
            self.assertGreaterEqual(len(lines), 1)
            obj = json.loads(lines[0])
            self.assertEqual(obj["kind"], "publish")
            self.assertEqual(obj["event_name"], "E")
            self.assertEqual(obj["application_id"], "app-1")

    def test_handler_span_has_duration_and_links_publish(self) -> None:
        with TemporaryDirectory() as d:
            tmp_path = Path(d)
            bus = EventBus()
            tracer = EventTracer(output_dir=tmp_path)
            bus.set_tracer(tracer, trace_id="t1")

            def handler(evt: E) -> None:
                bus.publish(E2(evt.application_id))

            bus.subscribe(E, handler)
            bus.publish(E("app-1"))

            p = tracer.flush_jsonl(application_id="app-1")
            lines = [json.loads(l) for l in p.read_text().splitlines()]

            kinds = {o["kind"] for o in lines}
            self.assertIn("handle_start", kinds)
            self.assertIn("handle_end", kinds)

            handle_ends = [o for o in lines if o["kind"] == "handle_end"]
            self.assertGreaterEqual(len(handle_ends), 1)
            self.assertIsNotNone(handle_ends[0]["duration_ms"])

            publishes = [o for o in lines if o["kind"] == "publish"]
            # at least one publish is from inside handler and must link to a parent span
            self.assertTrue(any(o.get("parent_span_id") for o in publishes))


if __name__ == "__main__":
    unittest.main()

