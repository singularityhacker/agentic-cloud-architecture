# AWS services for AI agent architecture

**Updated 2026-10-15; price examples assume US East (N. Virginia), public on-demand rates, before taxes, free-tier effects, and tier discounts.** Numbers are indicative only, not guarantees. Network transfer, logging, vector stores and other attached services are often separately billed.

| Service | Purpose | Approximate billing model | Scalability and critical limitations |
|---|---|---|---|
| Bedrock inference | Model and embedding APIs | Input/output tokens, model/modality-specific | Managed model fleet; per-model quotas, throttling, regional differences |
| Bedrock AgentCore Runtime | Host agent sessions | v2 consumption ~$0.1276/vCPU-hour + $0.0169/GB-hour; model calls extra | Isolated sessions and elastic capacity; quotas, runtime version and startup matter |
| AgentCore Gateway | MCP/tool gateway for enterprise APIs | ~$0.005/1k tool API invocations; search/indexing separately priced | Tool target rates and authentication are bottlenecks |
| AgentCore Memory | Short/long-term agent memory | Ingestion, storage, retrieval and record meters | Relevance, retention and tenant access isolation matter |
| AgentCore Identity / Policy | Agent auth and policy enforcement | Usage-dependent; Identity can be included when used with Runtime/Gateway | Complements IAM, not a replacement for application authorization |
| AgentCore Browser / Code Interpreter | Browser and sandbox execution | Billed for CPU/memory and associated storage/network | Session quotas, cold starts, timeouts |
| Bedrock Knowledge Bases | Managed retrieval-augmented generation | Ingestion/embedding/model costs plus vector store and retrieval | Data freshness, per-tenant permissions, vector-index baseline cost |
| SageMaker AI | Custom inference/training | Endpoint/instance/job/storage rates | Full model-control, but idle endpoints cost money |
| Lambda | Tool functions, event workers | ~$0.20/1M requests + $0.0000166667/GB-second x86 | Serverless concurrency; 15-minute invocation limit, cold starts |
| ECS / Fargate | Persistent container workers | Linux x86 ~$0.04048/vCPU-hour + $0.004445/GB-hour | Predictable worker capacity; container, ALB and network charges |
| SQS | Durable tasks and retries | Standard ~$0.40/1M API requests, before free tier | High throughput, at-least-once delivery, DLQs/idempotency needed |
| EventBridge | Event routing | Pay per published/matched/delivered event depending on feature | Eventual processing, target throttling, retry configuration |
| Step Functions | Deterministic durable orchestration | Standard ~$0.025/1,000 state transitions; Express differs | Transitions/workflow quotas, explicit state and callbacks |
| DynamoDB | Task/agent state, idempotency keys | Read/write operations, storage and optional indexes | Elastic on-demand scaling, partitions/hot keys |
| RDS/Aurora | SQL state and transactions | Instance/ACU hours, storage, I/O, backup | Easier relational semantics; instance baseline/connection pressure |
| S3 | Documents, traces, artifacts | Standard ~$0.023/GB-month; PUT ~$0.005/1k; GET ~$0.0004/1k | Virtually unlimited storage; request/egress costs |
| OpenSearch Serverless | Search/vector indexing | OCU capacity, storage, transfer | Retrieval at scale; minimum capacity can be expensive for demos |
| API Gateway | Expose tools and app APIs | Requests and transferred data | Quotas, auth and throttling; REST vs HTTP pricing differs |
| IAM | Identity, permission boundary | No typical direct policy fee | Least privilege, cross-account trust and credential lifecycle |
| Secrets Manager | Provider keys and sensitive settings | ~$0.40/secret-month + $0.05/10k API calls | Per-secret overhead, rotation, avoid unnecessary secret calls |
| CloudWatch / X-Ray | Logs, traces, alerts | Ingested bytes, retained logs, traces, custom metrics | Observability itself can become a major cost |
| VPC / NAT Gateway | Private networking | NAT ~$0.045/hour plus ~$0.045/GB processed | Always-on baseline even at zero traffic, plus egress |
| CDK / CloudFormation | Versioned resource composition | Deployed resources bill separately | Infrastructure drift, permissions, rollback and teardown |
| AWS Budgets / Cost Explorer | Estimate/observe AWS spend | Feature-dependent | Budget alert != absolute cap; billing signals have delay |

**Top 12 to learn deeply:** Bedrock, AgentCore, IAM, Lambda, S3, DynamoDB, SQS, Step Functions, ECS/Fargate, Knowledge Bases, CloudWatch, CDK.

### Primary source pricing pages

[AgentCore](https://aws.amazon.com/bedrock/agentcore/pricing/) · [Bedrock](https://aws.amazon.com/bedrock/pricing/) · [Lambda](https://aws.amazon.com/lambda/pricing/) · [Fargate](https://aws.amazon.com/fargate/pricing/) · [S3](https://aws.amazon.com/s3/pricing/) · [SQS](https://aws.amazon.com/sqs/pricing/) · [Step Functions](https://aws.amazon.com/step-functions/pricing/) · [Secrets Manager](https://aws.amazon.com/secrets-manager/pricing/) · [NAT](https://aws.amazon.com/vpc/pricing/) · [CloudWatch](https://aws.amazon.com/cloudwatch/pricing/) · [DynamoDB](https://aws.amazon.com/dynamodb/pricing/) · [AWS calculator](https://calculator.aws/).

The [machine-readable catalog](../catalog/rates.json) covers **only** meters with an explicit approximation. A service missing from the offline estimator is an **unknown cost**, not a free service.
