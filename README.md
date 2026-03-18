# Workflow vs Event-Driven Architecture — Loan Application (Python)

This repository is a learning project to compare two ways of solving the **same practical technical problem**:

- **Workflow / Orchestration**: a central controller executes steps in order.
- **Event-Driven / Choreography**: independent handlers react to events and publish new events.

The shared business problem is described in `[problem_statement.md](problem_statement.md)`.

## Quick start

No dependencies (standard library only).

Run the workflow implementation:

```bash
python -m workflow_approach.main
```

Run the event-driven implementation:

```bash
python -m event_driven_approach.main
```

Both demos run 3 scenarios:
- Approved
- Rejected (credit score too low)
- Failure injection (random failures)

## Where to read next

- **Problem definition**: `[problem_statement.md](problem_statement.md)`
- **Workflow approach details**: `[workflow_approach/README.md](workflow_approach/README.md)`
- **Event-driven approach details**: `[event_driven_approach/README.md](event_driven_approach/README.md)`
- **Comparison + lessons learned**: `[comparison.md](comparison.md)`
- **Evolution stages (robust + scalable)**: `[docs/plans/2026-03-18-evolution-stages-workflow-vs-event-driven.md](docs/plans/2026-03-18-evolution-stages-workflow-vs-event-driven.md)`

## Repo map

```
.
├── README.md
├── requirements.txt
├── problem_statement.md
├── comparison.md
├── shared/
│   └── models.py
├── workflow_approach/
│   ├── orchestrator.py
│   ├── services.py
│   └── main.py
└── event_driven_approach/
    ├── event_bus.py
    ├── events.py
    ├── handlers.py
    └── main.py
```

