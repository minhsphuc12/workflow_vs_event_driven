import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from event_driven_approach.event_tracer import EventTracer


class TestMermaidRender(unittest.TestCase):
    def test_mermaid_contains_event_and_handler_edges(self) -> None:
        with TemporaryDirectory() as d:
            tmp_path = Path(d)
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
            self.assertIn("```mermaid", md)
            self.assertIn("flowchart TD", md)
            self.assertIn("ApplicationSubmitted", md)
            self.assertIn("Router.on_submitted", md)


if __name__ == "__main__":
    unittest.main()

