# Roadmap and current status

**Implemented:** scenario-oriented JSON profiles; offline rate-card estimate + cap check; deterministic retry/score benchmark; optional real-agent HTTP adapter; SQS + Lambda + DynamoDB + S3 CDK reference; AWS service catalog and architecture decision briefs; GitHub CI without AWS deployment.

**Next:** richer stateful evaluation fixtures, task-level graders and repeated-run statistics; Bedrock/AgentCore agent adapters; OpenTelemetry traces, cost per success, load generation; profile-to-CDK mapping for supported patterns, real cloud deployments, cost reconciliation and teardown automation; optional Budgets as code.

**Research questions:** When do retries/queues outperform direct tool calls under variable failure rates? When does Step Functions improve correctness enough to justify complexity? When does RAG beat long context after retrieval-store costs? When do AgentCore, ECS and Lambda minimize total cost of successful tasks?

Do not publish simulated retry results as measured agent intelligence or cloud performance.
