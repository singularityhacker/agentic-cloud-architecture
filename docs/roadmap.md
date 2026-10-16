# Roadmap

## Stage 0 — Baseline: DONE
AWS agent-service catalog, indicative rate card, local preflight spending threshold, deterministic synthetic retry harness, HTTP evaluator, AWS CDK queue-worker reference, scenario pattern briefs and offline CI.

## Stage 1 — Local **agentic** reference implementation: IN PROGRESS
- [x] Architecture capability manifest and local/AWS mapping/plan
- [x] Docker Compose agent + Ollama
- [x] Local model inference, bounded tool calls, deterministic default-deny policy
- [x] SQLite persistent session memory, lexical knowledge retrieval, synthetic customer data
- [x] Workbench CLI: `plan`, `deploy local`, `benchmark local`, `stop local`
- [x] Unit tests and CI for provider logic / schema
- [ ] True MCP local tool gateway
- [ ] pgvector/Qdrant semantic retrieval and richer memory extraction
- [ ] Browser with sandbox and auditable policy controls
- [ ] Stateful business-outcome graders and cross-session test sets

## Stage 2 — AWS parity: PLANNED
- [ ] Bedrock Converse model adapter with same agent prompts/tool schemas
- [ ] AgentCore Runtime CDK / Toolkit integration
- [ ] AgentCore Gateway, Memory and Policy integration with conformance tests
- [ ] Knowledge Bases indexing, authorization and retrieval comparison
- [ ] Hybrid local-agent/selected-AWS-service target
- [ ] Deploy/teardown protection and resource inventory

## Stage 3 — Enterprise benchmarks: PLANNED
- [ ] Comparable model endpoint pinned across local/hybrid/AWS
- [ ] Repeated trials, concurrency/load tests and confidence intervals
- [ ] OpenTelemetry traces and policy violation graders
- [ ] Cost Explorer/CUR reconciliation and cost per successful task
- [ ] Scenario decision reports explaining security, correctness, latency and economics

Research priorities: agent vs workflow determinism; persistent memory value; retrieval strategy; specialized multi-agent overhead; AgentCore vs ECS vs Lambda.
