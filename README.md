# Agentic Cloud Architecture

**Design agentic systems once; exercise their capabilities locally; deploy equivalent systems using managed cloud services; measure the trade-offs.**

A scenario-driven workbench for **production AI-agent architecture**, with AWS Bedrock and AgentCore as the principal enterprise target. It combines declarative specifications, capability adapters, repeatable evaluations, AWS infrastructure-as-code, and transparent cost analysis.

This is **not** a course or a cloud emulator. It is a collection of reference patterns and an evolving executable architecture toolchain. The aim is architectural fluency: given a business problem, rapidly construct defensible agent designs and demonstrate *why* one is preferable.

## The central abstraction: capabilities, not vendors

An agent needs intelligence, memory, knowledge retrieval, tools, identity/policy, execution, and observability. **Model inference is independent of agent hosting**: a laptop-hosted agent can use a Hugging Face hosted model, while an agent hosted on AWS may call a non-Bedrock provider. Whether those capabilities are provided by a laptop or AWS should be a deployment choice, not a complete rewrite.

~~~text
                 BUSINESS SCENARIO + ACCEPTANCE TESTS
                                 │
                      DECLARATIVE SPECIFICATION
                  (capabilities, limits, workload)
                                 │
                     AGENT APPLICATION / TOOL CONTRACTS
                           ┌─────┴─────┐
                       LOCAL         AWS
                  ┌────────────┐ ┌──────────────────┐
  model           │ Ollama     │ │ Bedrock          │
  runtime         │ Python     │ │ AgentCore Runtime│
  memory          │ SQLite     │ │ AgentCore Memory │
  knowledge       │ local text │ │ Knowledge Bases  │
  tools           │ tool calls │ │ AgentCore Gateway│
  authorization   │ allowlist  │ │ AgentCore Policy │
  observability   │ JSON traces│ │ CloudWatch/X-Ray │
                  └─────┬──────┘ └────────┬─────────┘
                        └────────┬────────┘
                    COMMON EVALUATION WORKLOAD
            correctness · latency · recovery · cost · safety
~~~

**Functional portability is not operational parity.** Local tools can establish correctness of prompts, business logic, retrieval, permissions, memory, and error handling. They cannot prove AWS autoscaling behavior, billing, cold starts, multi-tenant isolation, managed quotas, or security controls. Some AWS offerings are proprietary; a local adapter performs a comparable *role*, not the identical implementation.

### Agent-specific service parity

| Agent capability | Local analogue | Enterprise AWS counterpart | Important mismatch |
|---|---|---|---|
| Inference | Ollama / local model | Bedrock | Different models can change results dramatically |
| Agent hosting | Python container | AgentCore Runtime | Sessions, isolation, IAM, managed scaling |
| Tool connectivity | Built-in tools; MCP integration planned | AgentCore Gateway (MCP) | Tool schemas may align, authorization/routing differs |
| Long-term memory | SQLite key/value; vector memory planned | AgentCore Memory | Extraction, semantics, retention differ |
| Enterprise retrieval | Local lexical corpus; vector RAG planned | Bedrock Knowledge Bases | Ingestion pipelines and index freshness differ |
| Authorization | Deterministic allowlist | AgentCore Policy (Cedar/Dogwood) | Current local enforcement **does not** execute Cedar |
| Browser | Playwright planned | AgentCore Browser | Browser isolation/session quotas differ |
| Sandboxed code | Containers planned | AgentCore Code Interpreter | Sandbox boundaries and operational behavior differ |
| Evaluation | Fixture/HTTP runner | AgentCore Evaluations | Graders/tracing/managed integrations differ |
| Telemetry | Structured local traces | CloudWatch, X-Ray, OTEL | Collection/retention and backend semantics differ |

**Current status:** A real local Ollama-backed agent service, basic local memory/retrieval/tools/policy, a Docker Compose target, and benchmark integration are available alongside an older synthetic harness and AWS queue CDK skeleton. The AWS **AgentCore application deployment is not yet implemented**. The AWS target currently produces a mapping/plan and refuses to pretend that the existing queue stack deploys this agent. See [capability contracts and parity](docs/capability-parity.md).

## Three levels of evidence

| Level | Question answered | What runs | AWS spend |
|---|---|---|---|
| **Local** | Does the agent *work*? | Actual local model, agent loop, tool implementations, memory, evaluation | None; hardware and power are not free |
| **Hybrid** (planned) | Is a given managed component integration-compatible? | Local agent + one selected Bedrock/AgentCore service | Potential model/service charges |
| **AWS** (planned) | Does enterprise infrastructure *scale and operate* as claimed? | AgentCore/Bedrock and managed services | Real usage charges; controlled experiment |

A synthetic rule-based driver is available for smoke tests without downloading models. It **does not count as an LLM benchmark**. For fair infrastructure comparisons, pin model/version, prompts, tools, dataset and evaluation rubric across targets. Treat differing local/AWS models as a **model + infrastructure comparison**, not an apples-to-apples hosting result.

## Getting started

**Offline analysis (Python 3.11+, no credentials):**

~~~bash
python -m agent_arch catalog
python -m agent_arch validate architectures/aws-queue-worker.json
python -m agent_arch estimate architectures/aws-queue-worker.json
python -m agent_arch guard architectures/aws-queue-worker.json
python -m agent_arch compare architectures/local-direct.json architectures/local-retry.json
python -m unittest discover -s tests -v
~~~

These commands are the original, standard-library-only analysis and synthetic evaluation harness. Its fixture comparison tests retry mechanics, not LLM performance.

**The workbench (no additional Python dependencies):**

~~~bash
python -m pip install -e .
agent-arch plan --target local
agent-arch plan --target aws          # Mapping only; no AWS calls
agent-arch deploy --target local      # Docker Compose: local agent and Ollama
docker compose -f deploy/local/compose.yaml exec ollama ollama pull llama3.2:3b
agent-arch benchmark --target local   # Real local-model endpoint, not a synthetic fixture
agent-arch stop --target local
~~~

The first model pull downloads weights and needs local RAM/disk capacity; the benchmark requires Docker and a pulled model. See [local runtime](docs/local-runtime.md). For a **no-model smoke test**, run `AGENT_MODEL_PROVIDER=rules python -m agent_arch.local_service` directly, then run `agent-arch benchmark --target local` in another terminal. The report labels rule-based execution as deterministic, not agent intelligence.

### Declare an architecture

[Portable enterprise research example](architectures/portable-research.json) (abridged excerpt; the linked file is the complete executable specification):

~~~json
{
  "name": "enterprise-research",
  "capabilities": {
    "model": {"kind": "tool-chat", "bindings": {"local": {"provider": "ollama", "model": "llama3.2:3b"}, "aws": {"provider": "bedrock", "model_id": null}}},
    "memory": {"type": "persistent"},
    "retrieval": {"type": "document_search"},
    "tools": ["search_docs", "lookup_customer", "remember", "recall"],
    "policy": {"default": "deny", "allowed_tools": ["search_docs", "lookup_customer", "remember", "recall"]},
    "observability": {"traces": true}
  },
  "limits": {"max_model_turns": 6, "max_tool_calls": 12},
  "evaluation": {"fixture": "fixtures/enterprise_research.json"}
}
~~~

The model binding is explicit per target: no AWS model is selected yet, so the AWS deployment cannot silently pick a different one. For an infrastructure comparison, verify model/version parity; otherwise label it a combined model-and-infrastructure comparison.

This capability specification is separate from the older `architectures/*.json` **cost/benchmark profiles**. The local runtime implements the named subset. AWS mappings are specified but not a universal CDK compiler. Details: [schema and contracts](docs/capability-parity.md).

## Model specialization and Hugging Face

**Specialized models are components, not necessarily chatbots.** A FinBERT sentiment classifier may offer valuable finance-specific signal without being capable of executing tools. A biomedical NER model, embedding model or reranker likewise needs a task-specific contract. This repository distinguishes:

- **Agent chat inference:** Ollama locally or Hugging Face Inference Providers through a hosted chat adapter. The existing Python agent, tool schemas and task evaluator stay the same; hosted calls can incur charges.
- **Task-specific inference:** Specialist text classifiers versus a generalist LLM prompted to emit the same labels, evaluated against exactly the same labeled examples.
- **Hosting and cloud architecture:** Separate axes. AWS Bedrock/SageMaker/AgentCore are enterprise targets; no assumption that arbitrary Hub models are available through Bedrock.

### Try Hugging Face hosted inference (opt-in)

~~~bash
python -m pip install -e '.[hf]'
# Export HF_TOKEN from your Hugging Face account (do not commit it).
agent-arch model-search --task text-classification --search finbert --limit 10
agent-arch model-search --task text-classification --hosted-only --limit 10
agent-arch model-benchmark --candidate majority                   # Offline, free baseline
agent-arch model-benchmark --candidate finbert --max-tasks 15 --allow-paid
agent-arch model-benchmark --candidate generalist --max-tasks 15 --allow-paid
~~~

These are *different* inference workloads with the same finance sentiment labels. Check that the selected models are actually served by the provider; the Hub catalog is much larger than the set currently hosted by Inference Providers. Models may be gated, differently licensed, or unavailable. `--allow-paid` explicitly opts into API charges and `--max-tasks` bounds requests. The included finance set contains only **15 synthetic hand-labeled examples** and cannot support authoritative performance conclusions. There are **no published model performance results** yet.

To use a hosted conversational model inside the **same local tool-using research agent** instead of downloading Ollama weights:

~~~bash
export HF_TOKEN=your_token_here
python -m pip install -e '.[hf]'
agent-arch --spec architectures/portable-research-hf.json plan --target local
agent-arch --spec architectures/portable-research-hf.json deploy --target local
agent-arch --spec architectures/portable-research-hf.json benchmark --target local
agent-arch --spec architectures/portable-research-hf.json stop --target local
~~~

The hosted example assumes a Hugging Face provider supports the selected chat model **and tool calling**. If it does not, change the model/provider or use a dedicated endpoint. Hosted calls are not free by default, regardless of where the agent container runs. Keep prompts, models, providers and revisions as stable as possible between comparison runs; report unpinned details as limitations.

See **[Domain-specific model strategy](docs/model-strategy.md)**, the [curated niche-model candidates](models/candidates.json), and the [finance sentiment experiment](experiments/finance-sentiment.json).

## Architecture development workflow

1. **Describe a business scenario.** Workload, latency, state, authorization boundaries, deployment constraints, correctness criteria and failure cases.
2. **Sketch 2–3 candidate architectures.** Choose single agent vs multi-agent, memory strategy, retrieval approach, queues, orchestration and deployment substrate.
3. **Run locally.** Stand up real services, evaluate business outcomes, inspect tool traces, inject failures, and repeat trials.
4. **Model cloud costs before provisioning.** Use the service rate card; label omitted meters and pricing uncertainty. See [AWS agent-service catalog](docs/aws-services.md) and [cost guardrails](docs/cost-guardrails.md).
5. **Move to a managed target when justified.** Generate/review infrastructure changes, provision under a controlled budget, run the *same* scenario and capture AWS observability.
6. **Publish a decision record.** Show task success, P50/P95 latency, failure modes, security behavior, throughput, cost per successful task, and limitations.

Do not claim AWS scale characteristics from local Docker benchmarks. Do not claim strong policy parity from a local allowlist. Do not equate an LLM's plausible response with verified business task completion.

## Reference patterns

Browse [scenario-driven patterns](patterns/README.md): bursty document triage, durable approvals, enterprise RAG, and long-running research agents. Each pattern should eventually have a deployment topology, cost model, benchmark suite and architectural decision record. [ADR-001](docs/adr-001.md) explains why evaluation is isolated from deployment.

## Repository map

~~~text
agent_arch/          Workbench, local agent capability providers, CLI and evals
architectures/       Cost/benchmark profiles and portable agent specifications
deploy/local/        Docker Compose local reference target
knowledge/           Synthetic enterprise documents and customer records
fixtures/            Evaluation workloads / expected business outcomes
infrastructure/      Existing AWS CDK queue-worker reference (NOT AgentCore)
catalog/             Approximate pricing meters and assumptions
patterns/            Scenario -> architecture -> alternatives -> trade-offs
docs/                Service catalog, parity matrix, design and roadmap
tests/               Offline unit and smoke tests
reports/             Local result artifacts (ignored by git)
~~~

## Current scope, boundaries and roadmap

- **Implemented:** AWS service catalog; transparent partial cost estimation and guard preflight; synthetic retry harness; real-agent HTTP benchmarking; local Ollama-backed tool-using research agent with SQLite memory and local document search; Compose runner and CLI; a separate SQS/Lambda/DynamoDB/S3 CDK reference; offline CI.
- **Next:** full MCP-compatible tool adapter, pgvector RAG, semantic memory, proper Cedar policy parity, browser/tool isolation, richer task-outcome scoring and observability traces.
- **Then:** selected portable specification-to-CDK transforms, AgentCore Runtime/Gateway/Memory/Policy integration, hybrid deployment, controlled AWS benchmarking, billed-cost reconciliation and verified teardown.

No AWS deployment is automatic. AWS Budgets are alerts and partial controls, **not guaranteed hard spending caps**. Review all resources and costs before cloud provisioning.

Authoritative platform references: [Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/), [AgentCore Runtime local development](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-cli.html), [AgentCore Gateway & MCP](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-using.html), [AWS Pricing Calculator](https://calculator.aws/).
