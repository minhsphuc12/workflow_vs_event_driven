# Evolution stages: make both stacks robust & scalable (workflow vs event-driven)

This document proposes **evolution stages** to upgrade both implementations in this repo into **production-grade reference architectures**.

- **Workflow stack**: from in-process orchestrator to a durable workflow/orchestration platform.
- **Event-driven stack**: from in-process pub/sub to broker-backed event choreography with strong delivery semantics.

The scope is intentionally **not limited** to the current code constraints (standard library + in-memory). Instead, it outlines a realistic path to:
- **Resilience** (retries, timeouts, circuit breaking, DLQ, backpressure)
- **Scalability** (horizontal scaling, consumer groups, partitioning, multi-region options)
- **Operability** (observability, traceability, SLOs, runbooks)
- **Security** (authn/z, mTLS, least privilege)
- **Platform integration**: **API Gateway** and **Service Mesh**

---

## 1) Context and goals

### Business process
Loan application processing steps (from `problem_statement.md`):
Submit → Identity → Credit → Risk → Decision → Notify.

### Non-goals (for now)
- Implementing a full production system in this repo.
- Picking a single “best” vendor/tool. The plan lists viable options and decision points.

### Guiding principles
- **Business invariants first**: correctness + compliance over throughput.
- **Make failure modes explicit**: define what can fail, how it retries, and how it is observed.
- **Idempotency everywhere**: any side-effect must be safe to retry.
- **Contracts are APIs**: workflow inputs/outputs and event schemas are versioned products.
- **Hybrid is normal**: workflows for the critical path; events for fan-out and secondary reactions.

---

## 2) Reference architecture (hybrid)

The most common production shape is **hybrid**:
- A synchronous entrypoint accepts requests (via **API Gateway**) and starts work.
- The critical path is executed by either:
  - a durable **Workflow Orchestrator** (workflow stack), or
  - an event-driven **Choreography** (event-driven stack) with strong operational conventions.
- Side effects and independent reactions are emitted as events.
- **Service Mesh** handles east-west concerns (mTLS, retries, traffic policy, telemetry), without replacing application-level correctness mechanisms.

### North-south: API Gateway
Use cases:
- Request authentication/authorization (OIDC/JWT), rate limiting, WAF, request validation.
- Routing and API versioning.
- Consistent client-facing error handling and request IDs.

### East-west: Service Mesh
Use cases:
- mTLS between services, identity-based policies (SPIFFE/SPIRE or platform identity).
- Traffic shifting (canary), outlier detection, circuit breaking at network edge.
- Standard telemetry (metrics/traces/log correlation).

> Mesh does **not** solve app-level semantics: idempotency, deduplication, ordering, workflow state, exactly-once-like behavior still requires application patterns.

---

## 3) Two evolution tracks (what changes as you scale)

### Track A — Workflow / Orchestration
Evolution direction:
1. In-process orchestrator (this repo)
2. Orchestrator as a service + persistent state
3. Durable workflow engine (Temporal/Cadence, Camunda/Zeebe, AWS Step Functions, Azure Durable Functions, etc.)

Why:
- Clear end-to-end state machine
- Central policy + compliance
- Better human debugging for business processes

### Track B — Event-driven / Choreography
Evolution direction:
1. In-process event bus (this repo)
2. Broker-backed pub/sub (Kafka/RabbitMQ/NATS/SQS+SNS, etc.)
3. Consumer groups + partitions + DLQ + replay tooling
4. Schema governance + compatibility + streaming analytics

Why:
- Easy to add independent reactions
- Scales per capability team/service
- Enables event replay, audit trails, and async decoupling

---

## 4) Stages (incremental, with exit criteria)

Each stage includes outcomes for both tracks.

### Stage 0 — Baseline (current repo)
**State**: single process, in-memory, simulated failures.

**Exit criteria**
- Document current flow and failure injection behavior (already present).

---

### Stage 1 — Engineering hygiene + observability foundations (applies to both)
**Goal**: make behavior explainable and testable before adding distributed complexity.

**Add**
- **Correlation IDs** end-to-end (request → workflow/events → logs/traces).
- Structured logging conventions (JSON logs recommended).
- Metrics naming conventions (latency, success/failure counts per step/handler).
- Deterministic failure injection for tests (seeded randomness).
- Clear error taxonomy: transient vs permanent vs validation vs dependency failure.

**Workflow track**
- Standardize step interface:
  - input/output contracts
  - timeouts per step
  - retries policy per step
- Separate “decision policy” from step execution (configurable thresholds/rules).

**Event-driven track**
- Standardize event envelope:
  - `event_id`, `type`, `schema_version`, `occurred_at`
  - `correlation_id`, `causation_id`
  - `producer`, `trace_context`
- Introduce idempotency rules:
  - dedupe by `event_id` (consumer-side) and/or idempotency key (side effects).

**Exit criteria**
- Ability to reconstruct a full timeline for one application ID from logs alone.
- Unit tests cover core decision logic + handler behavior (including retries/idempotency simulation).

---

### Stage 2 — Persistence + durable state (correctness under restart)
**Goal**: a restart must not lose progress or create duplicates.

**Add**
- Persistent store for application state (PostgreSQL is the default baseline).
- A “state machine” model:
  - current status
  - step results
  - timestamps and audit fields
- Idempotency store:
  - processed message IDs
  - external call idempotency keys

**Workflow track**
- Persist workflow state transitions.
- Implement compensations where needed (Saga-like), at minimum for side effects.

**Event-driven track**
- Persist “processed event offsets/ids” for exactly-once-like processing at business level.
- Store event payloads if you need full audit/replay (event log table or broker retention).

**Exit criteria**
- Kill/restart any service and verify:
  - no lost applications
  - no duplicate notifications
  - no “stuck forever” without visibility (timeouts + retry exhaustion are observable)

---

### Stage 3 — Real asynchronous transport (message broker + delivery semantics)
**Goal**: move from in-process calls to distributed, independently scalable components.

**Add**
- Broker (choose one):
  - Kafka (high throughput, partitions, replay)
  - RabbitMQ (routing patterns, per-queue semantics)
  - NATS JetStream (simplicity + performance)
  - Cloud managed (SQS/SNS, Pub/Sub, Event Hubs)
- Retry policy with backoff + jitter.
- **DLQ** (dead-letter) strategy:
  - poison messages
  - max attempts
  - quarantine + alert + manual replay
- Backpressure controls.

**Workflow track**
- If using a workflow engine, workers poll tasks; the engine persists state + retries.
- If still “custom orchestrator”, introduce a task queue per step.

**Event-driven track**
- Consumers in **consumer groups** (scale horizontally).
- Partitioning/ordering rules:
  - order by `application_id` (if required)
  - document what is and is not ordered

**Exit criteria**
- Demonstrate horizontal scale by increasing consumers/workers.
- Prove at-least-once delivery is safe via idempotency (no duplicate business side effects).

---

### Stage 4 — Production operations (SRE-grade)
**Goal**: run it reliably day 2+.

**Add**
- **OpenTelemetry** tracing, metrics, log correlation.
- SLOs/SLIs (success rate, end-to-end latency, step latency, DLQ rate).
- Alerting with runbooks.
- Load testing + capacity planning.
- Feature flags for risky changes (especially decision policy).

**Workflow track**
- Workflow visibility UI (engine-provided or custom):
  - search by application ID
  - view current step, retries, and history

**Event-driven track**
- Event trace search:
  - query by `correlation_id`
  - visualize causation chain (who published what)
- Replay tooling for selected event types (with safety gates).

**Exit criteria**
- On-call can answer:
  - “Where is application X stuck?”
  - “Why was it rejected?”
  - “Which dependency caused the outage?”

---

### Stage 5 — Platform integration: API Gateway + Service Mesh
**Goal**: integrate with company platform primitives while keeping app semantics correct.

**API Gateway (north-south)**
- AuthN/AuthZ:
  - OAuth2/OIDC, JWT validation
  - fine-grained scopes/roles for operations
- Rate limiting and abuse protection.
- Request/response transformation (careful: do not hide domain errors).
- Consistent request ID propagation.

**Service Mesh (east-west)**
- mTLS between all internal services.
- Service identity-based policies (allow/deny).
- Traffic policy:
  - timeouts, retries (network-level)
  - circuit breaking/outlier detection
  - gradual rollouts (canary)
- Telemetry: standardize traces/metrics tags across services.

**Important boundaries**
- Keep **application-level retries** for business operations separate from mesh retries:
  - mesh retry can amplify duplicates if not aligned
  - document which operations are safe for mesh retries

**Exit criteria**
- Security posture improved (mTLS + least privilege + audited ingress policies).
- Operational guardrails (rate limit + canary + observability) proven in staging.

---

### Stage 6 — Advanced scalability + governance
**Goal**: multi-team, high throughput, frequent change without breaking clients.

**Add**
- Event schema governance:
  - schema registry (Kafka ecosystem) or versioned contracts in repo
  - compatibility checks in CI
- Contract tests (producer/consumer) for events and workflow APIs.
- Data products:
  - CDC (Debezium) or event streaming to analytics
  - audit trails and compliance retention policies

**Workflow track**
- Multi-workflow support (different products/regions/policies).
- Human-in-the-loop steps (manual review) if business requires.

**Event-driven track**
- Stream processing for derived views (fraud signals, monitoring, analytics).
- Exactly-once *effect* patterns (outbox/inbox, transactional producer).

**Exit criteria**
- You can evolve schemas safely with backward compatibility guarantees.
- Teams can add new reactions without coordinating deployments tightly.

---

## 5) Decision points: when to choose which track (or both)

### Prefer workflow/orchestration when
- Strict ordering and centralized policy dominate.
- You need a “single pane of glass” for process state and compliance.
- Compensations are complex and must be managed centrally.

### Prefer event-driven choreography when
- The system grows by “also do X when Y happens”.
- Multiple independent teams/services must react to business facts.
- You need scalable fan-out, replay, and independent deployments.

### Hybrid recommendation (most common)
- Use a workflow engine for the critical path state machine.
- Emit domain events for side effects, notifications, audit, analytics, and downstream integrations.

---

## 6) Implementation patterns to bake in early (non-negotiables)

- **Idempotency keys** for all side effects (notifications, external calls).
- **Outbox pattern** for publishing events from DB transactions.
- **Inbox/dedup store** for consumers.
- **Timeouts** and **retry budgets** (bounded retries).
- **Poison message handling**: DLQ + alert + replay tooling.
- **Backpressure**: bounded queues and overload behavior.
- **Versioning** for events and APIs: explicit compatibility policy.

---

## 7) Suggested “next docs” (optional)

If you want to deepen this repo further, consider adding:
- A dedicated doc: “Event envelope + schema versioning policy”
- A dedicated doc: “Idempotency and deduplication strategy”
- A dedicated doc: “Mesh + Gateway: responsibility boundaries and retry policy”

