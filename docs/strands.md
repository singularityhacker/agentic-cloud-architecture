# Strands Agents local examples

Strands is an open-source agent framework. It runs the reasoning/tool loop in
Python; it is neither a model nor a cloud deployment target. This repository
supports `custom-python` (the existing default) and `strands` with the same
Ollama, rules and optional Hugging Face chat adapters. See [ADR 003](adr-003.md).

## No inference, actual Strands SDK

From the repository root (Python 3.11+):

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[strands]'
python -m agent_arch.strands_demo
python -m unittest discover -s tests -v
```

Installation requires network access; the rules demo and tests do not. The demo
runs the real Strands Agent with real local tools and a deterministic rules
provider. It returns the refund threshold and tool trace. It is **synthetic
plumbing evidence, not an LLM evaluation**. The temporary memory database is
removed when the demo finishes. No AWS credentials or model downloads required.
The optional SDK is pinned to `strands-agents==1.61.1`; pip resolves its transitive
dependencies. The base installation remains dependency-free. No broad prebuilt
tool collection is installed; only the repository's four tools are exposed.

## Local Ollama model

With Ollama running on your machine and a tool-capable model already pulled:

```bash
AGENT_MODEL=llama3.2:3b python -m agent_arch.strands_demo --provider ollama
```

The demo uses `http://localhost:11434` by default. `OLLAMA_BASE_URL` can select your
own server. This performs real model inference on that server; hardware, model
quality and availability are your responsibility. This path is runnable but was
not used to claim model-quality results in the offline tests.

## HTTP service and existing benchmark

Terminal 1:

```bash
AGENT_SPEC=architectures/portable-research-strands.json \
AGENT_MODEL_PROVIDER=rules python -m agent_arch.local_service
```

Terminal 2:

```bash
agent-arch --spec architectures/portable-research-strands.json plan --target local
agent-arch --spec architectures/portable-research-strands.json benchmark \
  --target local --output reports/strands-rules.json
```

Remove `AGENT_MODEL_PROVIDER=rules` to use the manifest's Ollama binding. For
Docker Compose, use `agent-arch --spec architectures/portable-research-strands.json
deploy --target local`, pull the model as in [local runtime](local-runtime.md),
and stop with the same spec and `stop --target local`. The image includes the
optional SDK. `AGENT_FRAMEWORK=strands` also overrides any existing manifest;
`AGENT_FRAMEWORK=custom-python` selects the baseline. Omitted framework fields
preserve existing behavior. Model provider and model ID environment overrides
remain separate from framework selection.

Hugging Face remains optional (`pip install -e '.[hf,strands]'`) and hosted;
its benchmark requires the existing `--allow-paid` opt-in. A local deployment
does not imply local model inference. No hosted inference is needed for these
rules examples or CI.

## Contracts and limitations

Both frameworks return `answer`, `completed`, `provider`, `model`, `usage`,
`tool_calls`, `model_turns`, `trace`, and `framework`. Strands also reports its
SDK version. The HTTP benchmark retains framework/version and tool traces and
keeps the rules evidence label. Pin the model, prompt, tools, fixture, hardware
and deployment when comparing frameworks; record repeated trials before drawing
performance conclusions. Reported tokens are not reconciled billing.

Each request gets a fresh Strands conversation; explicit SQLite memory is scoped
by session ID and persists in the service. This is not Strands SessionManager
or AgentCore semantic memory. Model turns and attempted tool calls are bounded;
a batch exceeding the remaining tool budget is rejected before any of its tools
execute. Invalid and unknown calls count toward that budget. Policy checks still
run inside each registered tool. SDK-level schema/unknown-tool rejections can
produce fewer application trace entries than attempted calls.

The bridge supports text and function calls, not multimodal or structured output.
It uses existing HTTP/provider clients rather than native Strands model clients;
Strands still owns the actual orchestration. AWS Runtime deployment, managed
Harness configuration, native Bedrock adapters, MCP, and distributed telemetry
are planned. No cloud parity or real-model benchmark result is implied.
