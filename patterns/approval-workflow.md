# Approval-gated agent actions

**Scenario:** An agent can draft a refund or payment but may not execute it without human authorization.

**Invariant:** No transfer before authorization; no duplicate transfer on retries; auditable decisions.

**Architectures:** An agent-only loop is simpler but not an authorization system. Step Functions Standard with explicit approval gate + narrow IAM execution Lambda + idempotency state enforces a deterministic workflow.

**Benchmark:** Inject duplicate callbacks, expired approvals, timeouts and worker restarts; count unauthorized and duplicate executions, recovery success, latency and workflow cost.

**Security:** The model must never be the sole authorization gate.
