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


## Stage 1b — Model independence and specialized model evaluation

- [x] Hugging Face hosted chat adapter for the existing local tool-using agent (optional SDK)
- [x] Explicit model/provider binding per target; Ollama not required for hosted-model workflow
- [x] Task-specific finance sentiment benchmark: majority baseline, hosted specialist classifier, hosted chat classifier
- [x] Hugging Face Hub discovery CLI for candidate search (including hosted-only filter)
- [x] CI using mocked inference only; no automatic paid calls or downloaded weights
- [ ] Run real paid inference on candidate models with explicit operator permission
- [ ] Provider pinning, live revision metadata and billing reconciliation
- [ ] Additional specialization tasks: biomedical entity recognition, reranking, OCR, risk flags and domain embeddings
- [ ] Pluggable evaluation adapters for classification, token tagging, ranking, retrieval, ASR and multimodal workloads
- [ ] Compare specialized-model pipeline against generalist-only end-to-end agent on realistic business outcomes

## Stage 1c — Framework independence

- [x] Independent framework selection: custom Python (backward-compatible default) and Strands
- [x] Optional pinned Strands SDK; real SDK rules demo and local Ollama example
- [x] Shared provider, tool, memory and policy contracts with bounded Strands execution
- [x] HTTP benchmark compatibility with observed framework/version and tool traces
- [x] Offline mocks testing actual SDK, limits, failure paths and session isolation
- [ ] Repeated real-model framework comparisons with fixed inputs and recorded conditions
- [ ] Native Strands providers and MCP integrations with conformance tests
- [ ] AgentCore Runtime deployment adapter for either framework
- [ ] Separate managed AgentCore Harness configuration path and comparison

The available Strands examples do not establish real-model quality or cloud parity.
