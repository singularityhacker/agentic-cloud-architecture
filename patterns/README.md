# Scenario-first reference patterns

| Scenario | Reference starting point | Principal trade-off |
|---|---|---|
| [Bursty document triage](document-triage.md) | S3 → SQS → Lambda → DynamoDB (+ optional Bedrock) | Buffered reliability vs increased latency/complexity |
| [Approval-gated financial action](approval-workflow.md) | Step Functions + narrow IAM tool + immutable audit | Deterministic authorization vs flexibility |
| [Enterprise knowledge assistant](enterprise-rag.md) | Bedrock Knowledge Bases or self-hosted RAG | Grounded retrieval vs indexing, latency and vector-storage cost |
| [Long-running research agent](long-running-research.md) | AgentCore Runtime or ECS/Fargate | Agent isolation vs idle cost and portability |

Every pattern should eventually have a profile, deployable implementation, benchmark fixture, assumptions, measured results and an architecture-decision record.
