from __future__ import annotations

import uuid

from event_driven_approach.event_bus import EventBus
from event_driven_approach.events import ApplicationSubmitted
from event_driven_approach.handlers import (
    ApplicationStore,
    CreditHandler,
    DecisionHandler,
    DecisionPolicy,
    FailureRouter,
    HandlerConfig,
    IdentityHandler,
    NotificationHandler,
    RiskHandler,
)
from event_driven_approach.models import LoanApplication


class Ansi:
    RESET = "\033[0m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"


def log(line: str) -> None:
    print(f"{Ansi.CYAN}{line}{Ansi.RESET}")


def print_summary(app: LoanApplication, bus: EventBus) -> None:
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
    print("event_trace:")
    for pe in bus.trace:
        if getattr(pe.payload, "application_id", None) == app.application_id:
            print(f"  - {pe.name}")
    print("")


def build_system(*, failure_rate: float, seed: int) -> tuple[EventBus, ApplicationStore]:
    bus = EventBus()
    store = ApplicationStore()

    IdentityHandler(bus=bus, store=store, config=HandlerConfig(failure_rate=failure_rate, rng_seed=seed), log=log)
    CreditHandler(bus=bus, store=store, config=HandlerConfig(failure_rate=failure_rate, rng_seed=seed + 1), log=log)
    RiskHandler(bus=bus, store=store, config=HandlerConfig(failure_rate=failure_rate, rng_seed=seed + 2), log=log)
    DecisionHandler(bus=bus, store=store, policy=DecisionPolicy(), log=log)
    FailureRouter(bus=bus, log=log)
    NotificationHandler(bus=bus, store=store, config=HandlerConfig(failure_rate=failure_rate, rng_seed=seed + 3), log=log)

    return bus, store


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


def run_scenario(app: LoanApplication, *, failure_rate: float, seed: int) -> None:
    bus, store = build_system(failure_rate=failure_rate, seed=seed)
    store.put(app)
    app.record("event_driven:start")
    log(f"[EventDriven] publish ApplicationSubmitted application_id={app.application_id}")
    bus.publish(ApplicationSubmitted(app.application_id))
    print_summary(app, bus)


def main() -> None:
    print(f"{Ansi.DIM}== Event-driven approach demo =={Ansi.RESET}")

    print(f"{Ansi.DIM}-- Scenario: approved --{Ansi.RESET}")
    run_scenario(scenario_approved(), failure_rate=0.0, seed=10)

    print(f"{Ansi.DIM}-- Scenario: rejected (credit) --{Ansi.RESET}")
    run_scenario(scenario_rejected_credit(), failure_rate=0.0, seed=10)

    print(f"{Ansi.DIM}-- Scenario: failure injection --{Ansi.RESET}")
    run_scenario(scenario_failure(), failure_rate=0.35, seed=99)


if __name__ == "__main__":
    main()

