# Engineering instructions for coding agents

Goal: turn business scenarios into reproducible agent infrastructure decisions and empirical comparisons, AWS-first but cloud-neutral at the evaluation boundary.

## Working sequence

1. Begin with a business scenario, invariants, threat model, success criteria and expected usage.
2. Choose a [pattern](patterns/README.md) and create a JSON profile in architectures/ modeled on aws-queue-worker.json.
3. Estimate spend with python -m agent_arch estimate PROFILE; run guard; document which services are omitted.
4. For an AWS topology, modify/add CDK constructs in infrastructure/ and run cdk synth. Profiles are currently scenario and estimate specifications, **not** an automatic arbitrary-profile-to-CDK compiler.
5. Build test fixtures with verifiable outcomes, not just LLM-as-judge prose.
6. Run local validations and baseline evaluations. Clearly classify output as synthetic, real-agent, or live AWS. Never claim local fixture success is evidence of LLM quality.
7. Compare alternatives at fixed model/version, prompts, tools and workload. Write down trade-offs, failure modes, limits and teardown steps.
8. When touching paid infrastructure, do not deploy unless directly instructed to. Never commit keys, data or billing credentials.

## Commands

- python -m unittest discover -s tests -v
- python -m agent_arch catalog
- python -m agent_arch compare architectures/local-direct.json architectures/local-retry.json
- python -m agent_arch estimate architectures/aws-queue-worker.json
- python -m agent_arch guard architectures/aws-queue-worker.json
- python scripts/aws_cost_snapshot.py --help
- cd infrastructure && cdk synth (requires extra CDK dependencies; does not provision resources)

## Design principles

Evidence over vendor claims. Explicit assumptions over synthetic cost precision. Deterministic policy gates over model-based authorization. Small blast radius and bounded concurrency. Every new architecture pattern should be tied to a realistic business scenario and measurable success conditions.
