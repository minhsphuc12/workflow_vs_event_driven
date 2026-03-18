from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ApplicationSubmitted:
    application_id: str


@dataclass(slots=True)
class IdentityVerified:
    application_id: str


@dataclass(slots=True)
class IdentityFailed:
    application_id: str
    reason: str


@dataclass(slots=True)
class CreditChecked:
    application_id: str
    credit_score: int


@dataclass(slots=True)
class CreditFailed:
    application_id: str
    reason: str


@dataclass(slots=True)
class RiskAssessed:
    application_id: str
    risk_score: float


@dataclass(slots=True)
class RiskFailed:
    application_id: str
    reason: str


@dataclass(slots=True)
class LoanApproved:
    application_id: str


@dataclass(slots=True)
class LoanRejected:
    application_id: str
    reason: str


@dataclass(slots=True)
class ProcessingFailed:
    application_id: str
    reason: str


@dataclass(slots=True)
class NotifyApplicant:
    application_id: str
    message: str


@dataclass(slots=True)
class NotificationFailed:
    application_id: str
    reason: str

