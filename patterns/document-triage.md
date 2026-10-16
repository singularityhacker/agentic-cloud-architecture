# Document triage under burst load

**Scenario:** Process 10,000+ incoming files/month, including unpredictable bursts, with verifiable structured output.

**Constraints:** At-least-once events, model quotas, retry safety, no duplicate side effects.

**A (minimal):** S3 notification → Lambda → model. Low idle spend; limited runtime and burst resilience.

**B (resilient):** S3 → SQS (DLQ) → bounded Lambda → model → DynamoDB task state. Better smoothing/backpressure; more moving parts and queue latency.

**Trade-off experiment:** Hold documents/model fixed, inject timeouts at different rates, compare success, P95, DLQ depth, requests and cost per successfully processed file. The current CDK stack covers the queue/worker/state skeleton, not inference.
