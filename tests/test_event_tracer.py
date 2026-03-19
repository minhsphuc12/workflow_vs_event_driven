import unittest
from dataclasses import dataclass
import json
from pathlib import Path


class TestPayloadSummarizer(unittest.TestCase):
    def test_summarize_payload_picks_common_fields_and_bounds(self) -> None:
        from event_driven_approach.event_tracer import summarize_payload

        @dataclass
        class Evt:
            application_id: str
            reason: str
            credit_score: int
            message: str

        evt = Evt(
            application_id="app-1",
            reason="some reason",
            credit_score=700,
            message="x" * 500,
        )
        s = summarize_payload(evt)
        self.assertEqual(s["application_id"], "app-1")
        self.assertEqual(s["reason"], "some reason")
        self.assertEqual(s["credit_score"], 700)
        self.assertIsInstance(s["message"], str)
        self.assertLessEqual(len(s["message"]), 200)


class TestEventTracerJsonl(unittest.TestCase):
    def test_event_tracer_writes_jsonl(self) -> None:
        from event_driven_approach.event_tracer import EventTracer

        with self.subTest("writes one json record line"):
            with self._tmpdir() as tmp_path:
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
                self.assertTrue(path.exists())
                lines = path.read_text().splitlines()
                self.assertEqual(len(lines), 1)
                obj = json.loads(lines[0])
                self.assertEqual(obj["kind"], "publish")
                self.assertEqual(obj["application_id"], "app-1")

    # Minimal tempdir helper (stdlib only)
    from contextlib import contextmanager
    import tempfile

    @contextmanager
    def _tmpdir(self):
        with self.tempfile.TemporaryDirectory() as d:
            yield Path(d)


if __name__ == "__main__":
    unittest.main()

