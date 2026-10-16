# Instructions for coding agents

This repository is an **agent architecture workbench**, not just an AWS infrastructure sample.

## Mission

Take a business scenario and define its agent capabilities, build a working **local** version, verify measurable business outcomes, then provision the corresponding **managed AWS** variant only when authorized. Explain trade-offs with evidence and a transparent cost model.

## Non-negotiable rules

1. Separate *portable behavior contracts* from cloud-specific provider implementations. Never claim a SQLite memory table is identical to AgentCore Memory, lexical retrieval equals Knowledge Bases, or a local allowlist equals Cedar policy evaluation.
2. Keep a precise status table: **implemented / partial / planned**, and distinguish rule-based synthetic plumbing from real-model evaluation.
3. Do not deploy AWS automatically or configure limitless execution. Require explicit, audited cloud opt-in, bounded invocation counts, cleanup plans and budget review.
4. Keep fixtures independent of model prompts. Never send answer keys to agent endpoints.
5. Use realistic scenarios with verifiable outcomes and repeat trials. Publish model versions, hardware, prompts, tool traces, costs and conditions for comparison.
6. Keep CI free of AWS credentials, model downloads and cloud deployment.
7. Protect the README from self-promotional copy; lead with architecture, engineering and empirical evidence.

## Development commands

~~~bash
python -m unittest discover -s tests -v
python -m agent_arch estimate architectures/aws-queue-worker.json
python -m pip install -e .
agent-arch plan --target local
agent-arch plan --target aws
agent-arch deploy --target local
agent-arch benchmark --target local
agent-arch stop --target local
~~~

See [README](README.md), [capability parity](docs/capability-parity.md) and [roadmap](docs/roadmap.md). Extend one scenario and one contract at a time; write a design decision before substantial new providers.
