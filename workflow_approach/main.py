from __future__ import annotations

import uuid

from workflow_approach.models import LoanApplication
from workflow_approach.orchestrator import DecisionPolicy, LoanWorkflowOrchestrator
from workflow_approach.services import (
    CreditService,
    IdentityService,
    NotificationService,
    RiskService,
    ServiceConfig,
)


class Ansi:
    RESET = "\033[0m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"


def log(line: str) -> None:
    print(f"{Ansi.CYAN}{line}{Ansi.RESET}")


def print_summary(app: LoanApplication) -> None:
    status_color = {
        "APPROVED": Ansi.GREEN,
        "REJECTED": Ansi.YELLOW,
        "FAILED": Ansi.RED,
    }.get(app.status.value, Ansi.RESET)

    print("")
    print(f"{Ansi.DIM}application_id={app.application_id}{Ansi.RESET}")
    print(f"final_status={status_color}{app.status.value}{Ansi.RESET}")
    print(f"metadata={app.metadata}")
    print("history:")
    for h in app.history:
        print(f"  - {h}")
    print("")


def make_orchestrator(*, failure_rate: float = 0.0, seed: int = 1) -> LoanWorkflowOrchestrator:
    base = ServiceConfig(failure_rate=failure_rate, rng_seed=seed)
    identity = IdentityService(base)
    credit = CreditService(ServiceConfig(failure_rate=failure_rate, rng_seed=seed + 1))
    risk = RiskService(ServiceConfig(failure_rate=failure_rate, rng_seed=seed + 2))
    notify = NotificationService(ServiceConfig(failure_rate=failure_rate, rng_seed=seed + 3))
    return LoanWorkflowOrchestrator(
        identity=identity,
        credit=credit,
        risk=risk,
        notify=notify,
        policy=DecisionPolicy(min_credit_score=620, max_risk_score=0.55),
        log=log,
    )


def scenario_approved() -> LoanApplication:
    return LoanApplication(
        application_id=str(uuid.uuid4())[:8],
        applicant_name="Alex",
        amount=10_000,
        income=80_000,
        credit_score=740,
    )


def scenario_rejected_credit() -> LoanApplication:
    return LoanApplication(
        application_id=str(uuid.uuid4())[:8],
        applicant_name="Blake",
        amount=5_000,
        income=60_000,
        credit_score=540,
    )


def scenario_failure() -> LoanApplication:
    return LoanApplication(
        application_id=str(uuid.uuid4())[:8],
        applicant_name="Casey",
        amount=50_000,
        income=50_000,
        credit_score=700,
    )


def main() -> None:
    print(f"{Ansi.DIM}== Workflow approach demo =={Ansi.RESET}")

    orch = make_orchestrator(failure_rate=0.0, seed=10)
    print(f"{Ansi.DIM}-- Scenario: approved --{Ansi.RESET}")
    app1 = orch.process(scenario_approved())
    print_summary(app1)

    print(f"{Ansi.DIM}-- Scenario: rejected (credit) --{Ansi.RESET}")
    app2 = orch.process(scenario_rejected_credit())
    print_summary(app2)

    print(f"{Ansi.DIM}-- Scenario: failure injection --{Ansi.RESET}")
    orch_flaky = make_orchestrator(failure_rate=0.35, seed=99)
    app3 = orch_flaky.process(scenario_failure())
    print_summary(app3)


if __name__ == "__main__":
    main()

