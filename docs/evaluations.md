# Evaluation methodology

| Tier | Workload | Evidence | AWS price |
|---|---|---|---|
| 0: fixture | Deterministic mock plus injected errors | Harness scoring, retry mechanics, reproducibility | $0 |
| 1: real agent | User-supplied local/HTTPS HTTP endpoint | Task success, elapsed time and reported token use | $0 AWS (external model usage may cost) |
| 2: deployed agent | Same workload targeting AWS service | Observed cloud latency and reliability | Often paid; planned |
| 3: load test | Concurrent runs and accounting reconciliation | Throughput, scaling, P95, cost per successful task | Potentially significant; planned |

**Rules:** Use the same dataset, model version and scoring across architectures. Vary one architectural factor. Record task success, tokens, retries, latency, policy violations, and costs. Reset state and repeat stochastic tasks; report confidence intervals if sample sizes support them. Keep expected answers outside the agent request. Benchmark outcomes must be reproducible and have labels indicating whether they are synthetic, real-agent or AWS-live.

The starter fixture benchmark is *not* a benchmark of AI reasoning. It is a functioning test of the benchmark machinery. The HTTP adapter expects a JSON object with string answer and optional usage.input_tokens / usage.output_tokens. It uses exact-match scoring; complex applications require state/outcome and policy graders.

### Research progression

First establish deterministic enterprise tool environments, then plug in Strands/LangGraph/custom agents, then add OpenTelemetry tracing and live AWS sampling. [Inspect AI](https://inspect.aisi.org.uk/) and [τ²-Bench](https://github.com/sierra-research/tau2-bench) are useful references.

## Framework comparisons

Both custom Python and Strands use the same HTTP evaluator. Results retain the observed framework, SDK version (when provided), provider, model and tool traces. Rules executions remain synthetic smoke tests even when the real Strands SDK runs. Hold models, prompts, tools, fixtures and deployment fixed; see [Strands examples](strands.md).
