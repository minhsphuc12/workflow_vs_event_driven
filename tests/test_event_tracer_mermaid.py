import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from event_driven_approach.event_tracer import EventTracer


def _mermaid_block(md: str) -> str:
    start = md.index("```mermaid") + len("```mermaid")
    end = md.index("```", start)
    return md[start:end].strip()


class TestMermaidRender(unittest.TestCase):
    def test_mermaid_shows_bus_and_distinct_handlers(self) -> None:
        with TemporaryDirectory() as d:
            tmp_path = Path(d)
            t = EventTracer(output_dir=tmp_path)
            # First event of application: Publisher -> Bus (no handler_name on publish)
            t.record(
                kind="publish",
                trace_id="t1",
                application_id="app-1",
                event_name="ApplicationSubmitted",
                handler_name=None,
                span_id="p0",
                parent_span_id=None,
                payload_summary={},
                duration_ms=None,
                error=None,
            )
            t.record(
                kind="handle_start",
                trace_id="t1",
                application_id="app-1",
                event_name="ApplicationSubmitted",
                handler_name="Router.on_submitted",
                span_id="h1",
                parent_span_id=None,
                payload_summary={"credit_score": 700},
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
                payload_summary={"credit_score": 700},
                duration_ms=None,
                error=None,
            )
            t.record(
                kind="handle_start",
                trace_id="t1",
                application_id="app-1",
                event_name="IdentityVerificationRequested",
                handler_name="IdentityHandler.on_identity_verification_requested",
                span_id="h2",
                parent_span_id="p1",
                payload_summary={},
                duration_ms=None,
                error=None,
            )
            t.record(
                kind="publish",
                trace_id="t1",
                application_id="app-1",
                event_name="IdentityVerified",
                handler_name="IdentityHandler.on_identity_verification_requested",
                span_id="p2",
                parent_span_id="h2",
                payload_summary={},
                duration_ms=None,
                error=None,
            )

            md = t.render_markdown(application_id="app-1")
            self.assertIn("```mermaid", md)
            self.assertIn("sequenceDiagram", md)
            block = _mermaid_block(md)
            self.assertIn("participant Publisher", block)
            self.assertIn("participant Bus", block)
            self.assertIn('participant Router_on_submitted as "Router.on_submitted"', block)
            self.assertIn(
                'participant IdentityHandler_on_identity_verification_requested as "IdentityHandler.on_identity_verification_requested"',
                block,
            )
            self.assertIn("Publisher ->> Bus: ApplicationSubmitted", block)
            self.assertIn("Bus ->> Router_on_submitted: ApplicationSubmitted", block)
            self.assertIn("Router_on_submitted ->> Bus: IdentityVerificationRequested", block)
            self.assertIn(
                "Bus ->> IdentityHandler_on_identity_verification_requested: IdentityVerificationRequested",
                block,
            )
            self.assertIn("IdentityHandler_on_identity_verification_requested ->> Bus: IdentityVerified", block)
            self.assertNotIn("(", block)
            self.assertNotIn("credit_score", block)


if __name__ == "__main__":
    unittest.main()
