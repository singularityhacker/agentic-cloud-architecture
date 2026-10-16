# Capability contracts, portability and parity

The platform should **specify intent once** and use provider-specific adapters for execution. A capability is an interface with explicit semantics, permissions and limits—not the name of an AWS product.

A model capability declares target-specific provider bindings rather than requiring the local Ollama model name to be treated as an AWS Bedrock model ID. An unset AWS model ID is an intentionally incomplete deployment prerequisite.\n\n## Contract map

| Capability | Portable contract | Local baseline | Enterprise mapping | Current status |
|---|---|---|---|---|
| Model | messages + tool schemas -> text/tool calls + usage | Ollama native chat | Bedrock Converse / supported models | local: working; AWS: planned |
| Agent lifecycle | run(task,session_id,limits) -> result/trace | Python HTTP worker | AgentCore Runtime | local: working; AWS: planned |
| Tools | list/call(name,arguments) | built-in read and memory tools | AgentCore Gateway MCP targets | local: working; MCP: planned |
| Memory | get/put(session,key,value) | SQLite keyed records | AgentCore Memory | local: working; AWS: planned |
| Knowledge | search(query,top_k) -> sourced hits | local document corpus (token overlap) | Bedrock Knowledge Bases | local: **lexical**; AWS: planned |
| Policy | authorize(principal,tool,args) -> permit/deny | deterministic default-deny allowlist | AgentCore Policy with Cedar/Dogwood | local: simple allowlist; true Cedar parity planned |
| Browser | navigate/extract | Playwright (planned) | AgentCore Browser | not implemented |
| Code runner | execute(sandbox,code) | containers (planned) | AgentCore Code Interpreter | not implemented |
| Tracing | spans/usage/error/cost | structured HTTP response tool trace | OpenTelemetry/CloudWatch | basic trace local; distributed tracing planned |
| Grading | evaluate(task,response,state) | exact-match and contains checks | AgentCore Evaluations/custom | local: partial |

### Limits of fidelity

**Same open-source code:** an agent container and its prompts/tool schemas can be portable, although dependencies and runtime constraints may vary.

**Protocol compatibility:** MCP, JSON tool schemas and OpenTelemetry can enable the same interfaces; they do not guarantee identical auth/session behavior.

**Functional substitutes:** SQLite memory, lexical search, Keycloak identity, Playwright browser or deterministic policy checks can solve the same user-visible task, but **are not** the corresponding proprietary AgentCore implementations. In particular, the starter local authorization implementation is *not Cedar* and should never be presented as production authorization equivalence.

**Cloud-only properties:** quotas, managed isolation, tenant boundaries, regional networking, scaling, managed retries and actual charges cannot be inferred from local tests.

### Contract evolution

Maintain a mapping registry, versioned agent specs, provider conformance tests and per-target compatibility checks. Do not silently fall back to a substitute when a spec explicitly requires AWS security semantics. Fail fast and explain unsupported capabilities.

The runtime uses bounded tool calls/model iterations and a default-deny allowlist; local tracing is a transparency aid, not an enterprise audit guarantee.

### Architecture profile types

- `architectures/portable-research.json`: **portable capability manifest** for workbench plan/deploy/benchmark.
- `architectures/aws-queue-worker.json` and `local-*.json`: **metered scenario profiles** for the original offline estimator and retry-fixture benchmark.

These deliberately coexist while the new specification-to-infrastructure compiler is developed; do not assume one schema can be passed into every older command.
