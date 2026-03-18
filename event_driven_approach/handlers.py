from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional

from event_driven_approach.event_bus import EventBus
from event_driven_approach.events import (
    ApplicationSubmitted,
    CreditChecked,
    CreditFailed,
    IdentityFailed,
    IdentityVerified,
    LoanApproved,
    LoanRejected,
    NotificationFailed,
    NotifyApplicant,
    ProcessingFailed,
    RiskAssessed,
    RiskFailed,
)
from event_driven_approach.models import ApplicationStatus, LoanApplication


@dataclass(slots=True)
class HandlerConfig:
    min_delay_s: float = 0.05
    max_delay_s: float = 0.20
    failure_rate: float = 0.0
    rng_seed: Optional[int] = None

    def rng(self) -> random.Random:
        return random.Random(self.rng_seed)


class ApplicationStore:
    """
    In-memory store to let handlers find and update applications by id.
    This simulates a database/aggregate store in a conceptual demo.
    """

    def __init__(self) -> None:
        self._apps: Dict[str, LoanApplication] = {}

    def put(self, app: LoanApplication) -> None:
        self._apps[app.application_id] = app

    def get(self, application_id: str) -> LoanApplication:
        return self._apps[application_id]


class IdentityHandler:
    def __init__(self, *, bus: EventBus, store: ApplicationStore, config: HandlerConfig, log: Callable[[str], None]):
        self._bus = bus
        self._store = store
        self._cfg = config
        self._rng = config.rng()
        self._log = log

        bus.subscribe(ApplicationSubmitted, self.on_submitted)

    def on_submitted(self, evt: ApplicationSubmitted) -> None:
        app = self._store.get(evt.application_id)
        self._log("[EventDriven] IdentityHandler <= ApplicationSubmitted")
        time.sleep(self._rng.uniform(self._cfg.min_delay_s, self._cfg.max_delay_s))

        if self._rng.random() < self._cfg.failure_rate:
            app.status = ApplicationStatus.FAILED
            app.record("identity:error:service_unavailable")
            self._bus.publish(IdentityFailed(app.application_id, "Identity service unavailable"))
            return

        if not app.applicant_name.strip():
            app.status = ApplicationStatus.REJECTED
            app.record("identity:error:missing_name")
            self._bus.publish(IdentityFailed(app.application_id, "Applicant name is missing"))
            return

        app.status = ApplicationStatus.IDENTITY_VERIFIED
        app.metadata["identity_verified"] = True
        app.record("identity:ok")
        self._bus.publish(IdentityVerified(app.application_id))


class CreditHandler:
    def __init__(self, *, bus: EventBus, store: ApplicationStore, config: HandlerConfig, log: Callable[[str], None]):
        self._bus = bus
        self._store = store
        self._cfg = config
        self._rng = config.rng()
        self._log = log

        bus.subscribe(IdentityVerified, self.on_identity_verified)

    def on_identity_verified(self, evt: IdentityVerified) -> None:
        app = self._store.get(evt.application_id)
        self._log("[EventDriven] CreditHandler <= IdentityVerified")
        time.sleep(self._rng.uniform(self._cfg.min_delay_s, self._cfg.max_delay_s))

        if self._rng.random() < self._cfg.failure_rate:
            app.status = ApplicationStatus.FAILED
            app.record("credit:error:timeout")
            self._bus.publish(CreditFailed(app.application_id, "Credit bureau timeout"))
            return

        if app.credit_score < 0 or app.credit_score > 900:
            app.status = ApplicationStatus.FAILED
            app.record("credit:error:invalid_score")
            self._bus.publish(CreditFailed(app.application_id, f"Invalid credit_score={app.credit_score}"))
            return

        app.status = ApplicationStatus.CREDIT_CHECKED
        app.metadata["credit_score"] = app.credit_score
        app.record("credit:ok")
        self._bus.publish(CreditChecked(app.application_id, app.credit_score))


class RiskHandler:
    def __init__(self, *, bus: EventBus, store: ApplicationStore, config: HandlerConfig, log: Callable[[str], None]):
        self._bus = bus
        self._store = store
        self._cfg = config
        self._rng = config.rng()
        self._log = log

        bus.subscribe(CreditChecked, self.on_credit_checked)

    def on_credit_checked(self, evt: CreditChecked) -> None:
        app = self._store.get(evt.application_id)
        self._log("[EventDriven] RiskHandler <= CreditChecked")
        time.sleep(self._rng.uniform(self._cfg.min_delay_s, self._cfg.max_delay_s))

        if self._rng.random() < self._cfg.failure_rate:
            app.status = ApplicationStatus.FAILED
            app.record("risk:error:overloaded")
            self._bus.publish(RiskFailed(app.application_id, "Risk engine overloaded"))
            return

        dti_proxy = app.amount / max(app.income, 1.0)
        credit_factor = (850 - evt.credit_score) / 850
        risk_score = min(1.0, 0.65 * dti_proxy + 0.45 * credit_factor)
        risk_score = round(risk_score, 3)

        app.status = ApplicationStatus.RISK_ASSESSED
        app.metadata["risk_score"] = risk_score
        app.record("risk:ok")
        self._bus.publish(RiskAssessed(app.application_id, risk_score))


@dataclass(slots=True)
class DecisionPolicy:
    min_credit_score: int = 620
    max_risk_score: float = 0.55


class DecisionHandler:
    def __init__(
        self,
        *,
        bus: EventBus,
        store: ApplicationStore,
        policy: DecisionPolicy,
        log: Callable[[str], None],
    ):
        self._bus = bus
        self._store = store
        self._policy = policy
        self._log = log

        bus.subscribe(RiskAssessed, self.on_risk_assessed)

    def on_risk_assessed(self, evt: RiskAssessed) -> None:
        app = self._store.get(evt.application_id)
        self._log("[EventDriven] DecisionHandler <= RiskAssessed")

        credit_score = int(app.metadata.get("credit_score", app.credit_score))
        risk_score = float(app.metadata.get("risk_score", evt.risk_score))

        if credit_score < self._policy.min_credit_score:
            app.status = ApplicationStatus.REJECTED
            app.record(f"decision:rejected:credit<{self._policy.min_credit_score}")
            self._bus.publish(LoanRejected(app.application_id, "Credit score too low"))
            return

        if risk_score > self._policy.max_risk_score:
            app.status = ApplicationStatus.REJECTED
            app.record(f"decision:rejected:risk>{self._policy.max_risk_score}")
            self._bus.publish(LoanRejected(app.application_id, "Risk score too high"))
            return

        app.status = ApplicationStatus.APPROVED
        app.record("decision:approved")
        self._bus.publish(LoanApproved(app.application_id))


class FailureRouter:
    """
    Centralizes how failures lead to notification. Event-driven systems often
    still have some shared conventions like a "dead-letter" / failure router.
    """

    def __init__(self, *, bus: EventBus, log: Callable[[str], None]):
        self._bus = bus
        self._log = log

        bus.subscribe(IdentityFailed, self.on_failed)
        bus.subscribe(CreditFailed, self.on_failed)
        bus.subscribe(RiskFailed, self.on_failed)

    def on_failed(self, evt: object) -> None:
        self._log(f"[EventDriven] FailureRouter <= {type(evt).__name__}")
        application_id = getattr(evt, "application_id")
        reason = getattr(evt, "reason")
        self._bus.publish(ProcessingFailed(application_id, reason))


class NotificationHandler:
    def __init__(self, *, bus: EventBus, store: ApplicationStore, config: HandlerConfig, log: Callable[[str], None]):
        self._bus = bus
        self._store = store
        self._cfg = config
        self._rng = config.rng()
        self._log = log

        bus.subscribe(LoanApproved, self.on_approved)
        bus.subscribe(LoanRejected, self.on_rejected)
        bus.subscribe(ProcessingFailed, self.on_failed)
        bus.subscribe(NotifyApplicant, self.on_notify)

    def on_approved(self, evt: LoanApproved) -> None:
        self._log("[EventDriven] NotificationHandler <= LoanApproved")
        self._bus.publish(NotifyApplicant(evt.application_id, "Congratulations! Your loan is approved."))

    def on_rejected(self, evt: LoanRejected) -> None:
        self._log("[EventDriven] NotificationHandler <= LoanRejected")
        self._bus.publish(NotifyApplicant(evt.application_id, f"Your loan application was rejected: {evt.reason}"))

    def on_failed(self, evt: ProcessingFailed) -> None:
        self._log("[EventDriven] NotificationHandler <= ProcessingFailed")
        self._bus.publish(NotifyApplicant(evt.application_id, f"Loan application failed: {evt.reason}"))

    def on_notify(self, evt: NotifyApplicant) -> None:
        app = self._store.get(evt.application_id)
        time.sleep(self._rng.uniform(self._cfg.min_delay_s, self._cfg.max_delay_s))
        if self._rng.random() < self._cfg.failure_rate:
            app.record("notify:error:service_unavailable")
            self._bus.publish(NotificationFailed(app.application_id, "Notification service unavailable"))
            return
        app.record("notify:ok")

