# Observing *actual* AWS spending

Profiles and rates.json produce approximate **predictions**. For deployments, use recorded Cost Explorer spend and detailed infrastructure telemetry.

## Read-only snapshot

Requires AWS CLI, an authorized profile with Cost Explorer read permission, and an account with Cost Explorer data. The utility invokes one real Cost Explorer API operation; some API usage has a charge.

~~~bash
python scripts/aws_cost_snapshot.py --profile my-sandbox
python scripts/aws_cost_snapshot.py --profile my-sandbox --warn-usd 25
python scripts/aws_cost_snapshot.py --profile my-sandbox --tag-key project --tag-value agentic-cloud-architecture
~~~

Note that custom tags need activation as cost-allocation tags and historical tagged usage may not be available. The script outputs unblended recorded cost by service and an exit status; **it does not stop resources or billing**. Do not mistake a missing/unavailable cost record for zero incurred spend. Billing data may be delayed.

## Pair spending with engineering metrics

- CloudWatch: Lambda invocation count, throttles, duration, error and concurrency.
- SQS: queue age, visible/dead-letter messages and retries.
- DynamoDB: reads/writes, throttled requests and utilization.
- AgentCore / Bedrock: token consumption, model-specific rates, session resource use and eval outcomes.
- Cost Explorer / CUR: realized AWS bill, tag-filtered experiments after tags are activated.

Use AWS Budgets and anomaly alerts for monitoring, and evaluate **Budget Actions** as a separate safety measure. They can restrict some usage but cannot universally guarantee a stop at a dollar threshold.

References: [Cost Explorer docs](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html), [AWS Budgets controls](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-controls.html).
