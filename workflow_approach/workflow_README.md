# Workflow approach (Orchestrator) — Loan Application

This folder demonstrates a **workflow/orchestration** style: a central **orchestrator** explicitly controls the business process by calling each step in order.

## What this approach looks like

- A single component (`LoanWorkflowOrchestrator`) knows:
  - the **order of steps**
  - **decision points** (approve/reject)
  - **error handling** strategy (fail fast, best-effort notification)
- Each step is a synchronous call to a service-like class:
  - `IdentityService.verify()`
  - `CreditService.check()`
  - `RiskService.assess()`
  - `NotificationService.send()`

## How to run

From the repository root:

```bash
python -m workflow_approach.main
```

You will see 3 scenarios:

- Approved
- Rejected (credit score too low)
- Failure injection (random service failures)

## Flow diagram

```mermaid
flowchart TD
    Start[Start] --> Submit[Application submitted]
    Submit --> Identity[Identity verification]
    Identity --> Credit[Credit check]
    Credit --> Risk[Risk assessment]
    Risk --> Decision{Decision}
    Decision -->|Approve| Approved[APPROVED]
    Decision -->|Reject| Rejected[REJECTED]
    Approved --> Notify[Notify applicant]
    Rejected --> Notify
    Notify --> End[End]
```

## Sequence diagram (conceptual)

```mermaid
sequenceDiagram
    participant Orch as Orchestrator
    participant Identity as IdentityService
    participant Credit as CreditService
    participant Risk as RiskService
    participant Notify as NotificationService

    Orch->>Identity: verify(app)
    Identity-->>Orch: ok / error
    Orch->>Credit: check(app)
    Credit-->>Orch: ok / error
    Orch->>Risk: assess(app)
    Risk-->>Orch: ok / error
    Orch->>Orch: decide(credit_score, risk_score)
    Orch->>Notify: send(app, message)
    Notify-->>Orch: ok / error
```

## Strengths

- **Clear control flow**: easy to see the whole process in one place.
- **Simple debugging**: single call chain, straightforward stack traces.
- **Centralized policy**: decisions and thresholds live in one place.

## Trade-offs

- **Tight coupling**: orchestrator must know every step and when to call it.
- **Harder to extend**: adding a new step often requires changing the orchestrator.
- **Scaling by step**: to scale individual steps independently, you typically need to split services and add async messaging later.

## Where to look in code

- `workflow_approach/orchestrator.py`: `LoanWorkflowOrchestrator.process()` is the “single source of truth” for the flow.
- `workflow_approach/services.py`: step implementations + failure injection.