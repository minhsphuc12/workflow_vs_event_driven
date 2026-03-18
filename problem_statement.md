# Problem statement: Loan Application processing

We want to process a loan application through a series of steps:

1. **Submit application**
2. **Identity verification**
3. **Credit check**
4. **Risk assessment**
5. **Decision** (approve/reject)
6. **Notification** to applicant

## Why this problem is useful for learning architecture

It contains:

- **A clear business process** (good for workflow/orchestration)
- **Multiple capability boundaries** (good for event-driven systems)
- **Branching outcomes** (approve vs reject)
- **Failures and partial success** (what if a service fails? what if notification fails?)
- A natural need for **observability** (reconstructing what happened)

## Constraints for this demo

- Pure Python standard library (no broker, no database)
- In-memory models and simulated delays/failures
- Keep business logic the same between approaches for fair comparison

