from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Optional

from workflow_approach.models import LoanApplication, ProcessingResult


@dataclass(slots=True)
class ServiceConfig:
    min_delay_s: float = 0.05
    max_delay_s: float = 0.20
    failure_rate: float = 0.0  # 0.0..1.0
    rng_seed: Optional[int] = None

    def rng(self) -> random.Random:
        return random.Random(self.rng_seed)


class IdentityService:
    def __init__(self, config: ServiceConfig):
        self._config = config
        self._rng = config.rng()

    def verify(self, app: LoanApplication) -> ProcessingResult:
        time.sleep(self._rng.uniform(self._config.min_delay_s, self._config.max_delay_s))
        if self._rng.random() < self._config.failure_rate:
            return ProcessingResult(False, "Identity service unavailable")
        if not app.applicant_name.strip():
            return ProcessingResult(False, "Applicant name is missing")
        return ProcessingResult(True, "Identity verified", {"identity_verified": True})


class CreditService:
    def __init__(self, config: ServiceConfig):
        self._config = config
        self._rng = config.rng()

    def check(self, app: LoanApplication) -> ProcessingResult:
        time.sleep(self._rng.uniform(self._config.min_delay_s, self._config.max_delay_s))
        if self._rng.random() < self._config.failure_rate:
            return ProcessingResult(False, "Credit bureau timeout")
        if app.credit_score < 0 or app.credit_score > 900:
            return ProcessingResult(False, f"Invalid credit_score={app.credit_score}")
        return ProcessingResult(True, "Credit checked", {"credit_score": app.credit_score})


class RiskService:
    def __init__(self, config: ServiceConfig):
        self._config = config
        self._rng = config.rng()

    def assess(self, app: LoanApplication) -> ProcessingResult:
        time.sleep(self._rng.uniform(self._config.min_delay_s, self._config.max_delay_s))
        if self._rng.random() < self._config.failure_rate:
            return ProcessingResult(False, "Risk engine overloaded")

        # Very simplified model for educational purposes:
        # - Higher credit_score decreases risk.
        # - Higher amount-to-income increases risk.
        dti_proxy = app.amount / max(app.income, 1.0)
        credit_factor = (850 - app.credit_score) / 850
        risk_score = min(1.0, 0.65 * dti_proxy + 0.45 * credit_factor)
        return ProcessingResult(True, "Risk assessed", {"risk_score": round(risk_score, 3)})


class NotificationService:
    def __init__(self, config: ServiceConfig):
        self._config = config
        self._rng = config.rng()

    def send(self, app: LoanApplication, message: str) -> ProcessingResult:
        time.sleep(self._rng.uniform(self._config.min_delay_s, self._config.max_delay_s))
        if self._rng.random() < self._config.failure_rate:
            return ProcessingResult(False, "Notification service unavailable")
        return ProcessingResult(True, "Notification sent", {"message": message})

