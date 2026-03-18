from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ApplicationStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    IDENTITY_VERIFIED = "IDENTITY_VERIFIED"
    CREDIT_CHECKED = "CREDIT_CHECKED"
    RISK_ASSESSED = "RISK_ASSESSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


@dataclass(slots=True)
class ProcessingResult:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


@dataclass(slots=True)
class LoanApplication:
    application_id: str
    applicant_name: str
    amount: float
    income: float
    credit_score: int

    status: ApplicationStatus = ApplicationStatus.SUBMITTED
    history: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def record(self, message: str) -> None:
        self.history.append(message)

