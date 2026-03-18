from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from workflow_approach.models import ApplicationStatus, LoanApplication, ProcessingResult
from workflow_approach.services import CreditService, IdentityService, NotificationService, RiskService


@dataclass(slots=True)
class DecisionPolicy:
    min_credit_score: int = 620
    max_risk_score: float = 0.55


class LoanWorkflowOrchestrator:
    """
    A classic workflow/orchestration approach:
    one component knows the whole process and calls each step in order.
    """

    def __init__(
        self,
        *,
        identity: IdentityService,
        credit: CreditService,
        risk: RiskService,
        notify: NotificationService,
        policy: DecisionPolicy = DecisionPolicy(),
        log: Optional[Callable[[str], None]] = None,
    ):
        self._identity = identity
        self._credit = credit
        self._risk = risk
        self._notify = notify
        self._policy = policy
        self._log = log or (lambda _: None)

    def process(self, app: LoanApplication) -> LoanApplication:
        self._log(f"[Workflow] start application_id={app.application_id}")
        app.record("workflow:start")

        try:
            self._step_identity(app)
            self._step_credit(app)
            self._step_risk(app)
            self._step_decision(app)
            self._step_notification(app)
            self._log(f"[Workflow] done status={app.status.value}")
            return app
        except Exception as e:  # noqa: BLE001 - demo-only central error handling
            app.status = ApplicationStatus.FAILED
            app.record(f"workflow:failed:{type(e).__name__}:{e}")
            self._log(f"[Workflow] FAILED error={type(e).__name__}: {e}")
            # Best-effort notify on failure
            self._notify.send(app, f"Loan application failed: {type(e).__name__}")
            return app

    def _require(self, result: ProcessingResult, app: LoanApplication, *, step: str) -> None:
        if not result.success:
            app.record(f"{step}:error:{result.message}")
            raise RuntimeError(f"{step} failed: {result.message}")
        if result.data:
            app.metadata.update(result.data)

    def _step_identity(self, app: LoanApplication) -> None:
        self._log("[Workflow] identity.verify()")
        res = self._identity.verify(app)
        self._require(res, app, step="identity")
        app.status = ApplicationStatus.IDENTITY_VERIFIED
        app.record("identity:ok")

    def _step_credit(self, app: LoanApplication) -> None:
        self._log("[Workflow] credit.check()")
        res = self._credit.check(app)
        self._require(res, app, step="credit")
        app.status = ApplicationStatus.CREDIT_CHECKED
        app.record("credit:ok")

    def _step_risk(self, app: LoanApplication) -> None:
        self._log("[Workflow] risk.assess()")
        res = self._risk.assess(app)
        self._require(res, app, step="risk")
        app.status = ApplicationStatus.RISK_ASSESSED
        app.record("risk:ok")

    def _step_decision(self, app: LoanApplication) -> None:
        credit_score = int(app.metadata.get("credit_score", app.credit_score))
        risk_score = float(app.metadata.get("risk_score", 1.0))

        if credit_score < self._policy.min_credit_score:
            app.status = ApplicationStatus.REJECTED
            app.record(f"decision:rejected:credit<{self._policy.min_credit_score}")
            self._log("[Workflow] decision=REJECTED (credit)")
            return

        if risk_score > self._policy.max_risk_score:
            app.status = ApplicationStatus.REJECTED
            app.record(f"decision:rejected:risk>{self._policy.max_risk_score}")
            self._log("[Workflow] decision=REJECTED (risk)")
            return

        app.status = ApplicationStatus.APPROVED
        app.record("decision:approved")
        self._log("[Workflow] decision=APPROVED")

    def _step_notification(self, app: LoanApplication) -> None:
        if app.status == ApplicationStatus.APPROVED:
            msg = "Congratulations! Your loan is approved."
        elif app.status == ApplicationStatus.REJECTED:
            msg = "Your loan application was rejected."
        else:
            msg = f"Loan application ended with status {app.status.value}."

        self._log("[Workflow] notify.send()")
        res = self._notify.send(app, msg)
        # Notification errors should not flip business outcome in this demo.
        if not res.success:
            app.record(f"notify:error:{res.message}")
            self._log(f"[Workflow] notify failed: {res.message}")
        else:
            app.record("notify:ok")

