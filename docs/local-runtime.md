# Running the enterprise research agent locally

The local target is a genuine tool-using agent process with an optional local model. It is not an AgentCore emulator.

## Prerequisites

- Docker Engine with Compose v2; enough storage/RAM to run Ollama and download a model.
- Python 3.11+ to install the `agent-arch` CLI, or use `python -m agent_arch.workbench`.
- No AWS credentials or billing account.

## Start

~~~bash
python -m pip install -e .
agent-arch plan --target local
agent-arch deploy --target local
docker compose -f deploy/local/compose.yaml exec ollama ollama pull llama3.2:3b
curl http://127.0.0.1:8000/health
agent-arch benchmark --target local --output reports/local-research.json
agent-arch stop --target local
~~~

Models aren't automatically downloaded because the size/choice is a meaningful user decision. Change `AGENT_MODEL` in Compose or through your local environment as desired. Ollama can run independently on your Mac if preferred, with `OLLAMA_BASE_URL` pointing to it.

Try a task directly:

~~~bash
curl -s http://127.0.0.1:8000/agent -H 'Content-Type: application/json' \
  -d '{"task_id":"research-1","input":"What refund approval threshold applies to Northstar?","context":{"session_id":"demo"}}'
~~~

**Components actually exercised:** model -> tool selection -> default-deny tool dispatch -> lexical document/customer lookup -> bounded model loop; SQLite persists scoped key/value memories; JSON responses include tool traces and model usage. Synthetic corporate records are under `knowledge/`. The service is bound to localhost on the host; do not expose it to untrusted networks. This is a prototype, not a hardened, authenticated multitenant API.

For a model-free deterministic smoke test, skip Docker entirely and start the HTTP service in terminal one:

~~~bash
AGENT_MODEL_PROVIDER=rules python -m agent_arch.local_service
~~~

Run `agent-arch benchmark --target local` in terminal two. The benchmark tags rule-mode results as deterministic; this exercises protocol, tools, memory, retrieval and scoring **but not model reasoning**.

## Why it is not literally AgentCore

AgentCore Memory, Gateway, Identity, Policy and Browser are AWS managed services with their own control/data planes. Local provider modules reproduce *selected capability contracts*, not the full AWS binaries, isolation or scale characteristics. An AWS deployment needs real service integrations and separate conformance tests. See [capability-parity.md](capability-parity.md).

## Cost and performance

Local inference avoids AWS metering but uses hardware and power. Record model/quantization/hardware, fixture revision, prompt version, concurrency, task success and P50/P95 latency. Exact-match scoring is often too strict for prose; the research fixture uses required-answer substrings rather than accepting every plausible answer.


## Hosted inference without local model weights

Choose `architectures/portable-research-hf.json` for an agent executed in local Docker while its **chat model is served by Hugging Face Inference Providers**. This runs no local Ollama container or model weights (though Docker and the Python agent container remain necessary).

~~~bash
export HF_TOKEN=your_token_here
agent-arch --spec architectures/portable-research-hf.json plan --target local
agent-arch --spec architectures/portable-research-hf.json deploy --target local
agent-arch --spec architectures/portable-research-hf.json benchmark --target local
agent-arch --spec architectures/portable-research-hf.json stop --target local
~~~

The Dockerfile installs the optional Hugging Face SDK. Keep the access token in an environment variable rather than storing it in Git; remember that environment variables may be visible to anyone with access to the Docker host. The hosted model and its inference provider must **actually support chat completion and function calling**. The example ID is illustrative, not a live availability guarantee.

This workflow may incur provider charges; `agent-arch benchmark --target local` does not itself enforce a spending cap for external hosted models. For bounded specialist-model experiments, use `agent-arch model-benchmark --max-tasks N --allow-paid`. Do not send confidential datasets to hosted models without an approved data-processing agreement.
