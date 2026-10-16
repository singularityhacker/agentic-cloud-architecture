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

For a model-free deterministic smoke test, start the agent container with `AGENT_MODEL_PROVIDER=rules` (through Compose environment configuration) and run the same benchmark. Rule-mode results exercise plumbing only, not LLM reasoning quality.

## Why it is not literally AgentCore

AgentCore Memory, Gateway, Identity, Policy and Browser are AWS managed services with their own control/data planes. Local provider modules reproduce *selected capability contracts*, not the full AWS binaries, isolation or scale characteristics. An AWS deployment needs real service integrations and separate conformance tests. See [capability-parity.md](capability-parity.md).

## Cost and performance

Local inference avoids AWS metering but uses hardware and power. Record model/quantization/hardware, fixture revision, prompt version, concurrency, task success and P50/P95 latency. Exact-match scoring is often too strict for prose; the research fixture uses required-answer substrings rather than accepting every plausible answer.
