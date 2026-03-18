# Comparison: Workflow vs Event-Driven (Loan Application)

This document compares two implementations of the same business problem in this repo:

- **Workflow/orchestration**: `[workflow_approach/](workflow_approach/)`
- **Event-driven choreography**: `[event_driven_approach/](event_driven_approach/)`

Both implement the same conceptual steps:

1. Submit application
2. Identity verification
3. Credit check
4. Risk assessment
5. Decision (approve/reject)
6. Notification

## Side-by-side summary

| Dimension | Workflow (Orchestrator) | Event-Driven (Choreography) |
|---|---|---|
| **Primary unit of design** | The **process** (a sequence of steps) | The **events** (a contract) and **reactions** |
| **Control flow** | Explicit in one place (`LoanWorkflowOrchestrator.process()`) | Distributed across handlers; flow emerges from subscriptions |
| **Coupling** | Higher: orchestrator must know all steps | Lower: handlers only need event contracts |
| **Adding a new step** | Usually requires changing orchestrator | Often add a new subscriber (or new event + subscriber) |
| **Observability needs** | Moderate (call chain already shows order) | High (need tracing/correlation IDs to rebuild a timeline) |
| **Error handling** | Centralized (try/except in orchestrator) | Distributed; needs conventions (dead-letter/failure router) |
| **Scaling** | Often scales the whole process together | Scales per handler (in real systems, per consumer group) |
| **Testing** | End-to-end tests feel natural; unit tests may require orchestration setup | Unit testing handlers is easy; E2E requires event trace assertions |
| **Debugging** | Straight stack traces | Requires event logs, traces, and sometimes replay tooling |
| **Change management** | Change the flow by editing orchestrator | Change by evolving event contracts + handlers (versioning matters) |

## Concrete example in this repo

### Workflow flow visibility

In the workflow implementation, the step order is directly readable:

- Identity -> Credit -> Risk -> Decision -> Notify
- A single failure can be caught centrally and handled consistently

Where to see it:
- `workflow_approach/orchestrator.py`
- `workflow_approach/services.py`

### Event-driven flow visibility

In the event-driven implementation, you must “follow the events”:

`ApplicationSubmitted` -> `IdentityVerified` -> `CreditChecked` -> `RiskAssessed` -> (`LoanApproved` or `LoanRejected`) -> `NotifyApplicant`

Where to see it:
- `event_driven_approach/events.py`
- `event_driven_approach/handlers.py`
- `event_driven_approach/event_bus.py` (trace)

## Lessons learned (practical)

1. **A workflow can be the simplest correct answer** when:
   - the process is stable
   - correctness depends on a strict step order
   - you want a single place to enforce policy and invariants

2. **Event-driven shines when change and extension are the “default”**:
   - new requirements often mean “also do X when Y happens”
   - multiple teams/services need to react independently
   - you expect to scale or deploy steps separately

3. **Event-driven does not remove orchestration—it relocates it**:
   - without care, choreography becomes implicit orchestration spread across handlers
   - you still need shared conventions (correlation IDs, retries, DLQ)

4. **Error handling is the most underestimated cost in event-driven systems**:
   - transient failures, retries, deduplication, idempotency
   - “what happens if handler B fails after handler A succeeded?”

5. **Observability is architecture**:
   - in workflow, the call stack gives you a timeline “for free”
   - in event-driven, you must build/standardize tracing from day 1

## Decision framework (how to choose)

Use **workflow/orchestration** if:
- you have a clear end-to-end business process
- step order and centralized policy are crucial
- you want faster iteration with fewer moving parts

Use **event-driven** if:
- independent capabilities must react to the same business facts
- you expect frequent additions of new reactions/features
- you want to scale and deploy parts independently (eventually with a broker)

Hybrid is common:
- workflow orchestrates the critical path
- events broadcast outcomes and side-effects (notifications, analytics, audit)

## What this demo intentionally omits (production realities)

To keep the code conceptual, we do **not** implement:
- a message broker (Kafka/RabbitMQ/SQS)
- retries with backoff, DLQ, and idempotency keys
- persistence/transactions across steps
- exactly-once processing guarantees
- event schema versioning

Those topics are the natural “next lessons” after this repo.

