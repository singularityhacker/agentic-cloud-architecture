# Agentic Cloud Architecture

Reference architectures, AWS service economics, infrastructure as code and reproducible evaluations for production AI agents.

## Start here

- [AWS service catalog](docs/aws-services.md) — purpose, pricing model, scalability and gotchas.
- [Architecture patterns](patterns/README.md) — choose designs from business scenarios and document trade-offs.
- [Benchmark methodology](docs/evaluations.md) — synthetic versus real agent versus live AWS tests.
- [Cost controls](docs/cost-guardrails.md) — local estimation, budget alerts and teardown.
- [Roadmap](docs/roadmap.md) — what's implemented versus proposed.

## Local usage: no AWS account needed

Requires Python 3.11+; the profiler and benchmark runner use the standard library.

~~~bash
python -m agent_arch catalog
python -m agent_arch validate architectures/aws-queue-worker.json
python -m agent_arch estimate architectures/aws-queue-worker.json
python -m agent_arch guard architectures/aws-queue-worker.json
python -m agent_arch compare architectures/local-direct.json architectures/local-retry.json
python -m unittest discover -s tests -v
~~~

Declarative scenario profiles are JSON files under architectures/. AWS prices are **approximate US East assumptions**, not a bill quote. A budget threshold here is a local preflight check, not a true AWS spending cap.

### Benchmarks: be precise about evidence

The included fixture runner simulates transient tool errors and tests the runner's retry/scoring mechanism. It does **not** call an LLM or measure AWS performance. Run real agents by pointing the HTTP adapter at your own agent endpoint; its request never contains the expected answer.

~~~bash
python -m agent_arch bench architectures/local-direct.json --driver http --endpoint http://127.0.0.1:8000/agent --output reports/real-agent.json
~~~

POST request body: `{"task_id":"t1","input":"...","context":{}}`. Response body: `{"answer":"billing","usage":{"input_tokens":100,"output_tokens":10}}`. Token-priced costs require truthful usage from the endpoint.

### Optional AWS reference stack

The CDK example in [infrastructure/](infrastructure/) is a **deployable SQS → Lambda** worker plus DynamoDB task state and S3 artifacts. It deliberately does not invoke a model, deploy AgentCore, or promise complete profile-to-CDK compilation.

~~~bash
cd infrastructure
python -m pip install -r requirements.txt
npm install -g aws-cdk
cdk synth        # No resources provisioned
# With your own AWS account, credentials, budget controls and reviewed costs:
cdk diff
cdk deploy       # May incur charges
cdk destroy      # Then verify no leftover resources
~~~

No automatic deployment is configured. CI performs offline validation only.

## Layout

~~~text
agent_arch/         Architecture, cost and evaluation CLI
architectures/      Declarative scenario profiles
catalog/            Price-meter snapshot
fixtures/           Deterministic synthetic tasks
infrastructure/     Optional AWS CDK reference implementation
patterns/           Scenario-led decisions and alternatives
docs/               Service catalog, evaluation rigor, cost controls
tests/              Offline tests
reports/            Local benchmark outputs (gitignored)
~~~

Principle: design → estimate → validate → measure → compare → explain. Do not present simulations as real agent performance or estimates as actual AWS spend.
