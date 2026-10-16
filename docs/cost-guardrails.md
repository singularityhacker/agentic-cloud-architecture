# Cost controls and observability

1. Use the offline estimator and explicit monthly threshold in each architecture profile. The guard command exits nonzero if estimated costs exceed that **local** threshold.
2. Run fixtures first (zero AWS API calls). Never confuse synthetic success rates or forecast prices with production measurements.
3. For paid experiments, use a separate sandbox AWS account, restricted IAM permissions, tags, budgets and anomaly alerts. Review quotas, concurrency and Bedrock token limits.
4. Check CDK synthesis/diff before deployment. Cloud costs can begin upon provisioning; start with minimal capacities.
5. Inspect Cost Explorer / Cost and Usage Reports, CloudWatch usage, model token volumes and runtime minutes; billing can lag.
6. Tear down experiments explicitly; verify S3 contents, log groups and dangling dependent resources.

**Important:** AWS Budgets notifications are not a hard cap. [Budget actions](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-controls.html) can apply restrictive policies or stop some instance types, but they are delayed and not an all-service spending cutoff. The repo currently **does not provision** AWS Budgets or automatically shut down spending. Its local threshold is preflight only.

### Scope of estimator

The rate card is approximate us-east-1 on-demand and incomplete: no free tier, discount tiers, egress, DynamoDB, logging, RDS, vector-store minimums, taxes or per-model Bedrock differences unless explicitly supplied. Treat the result as a transparent *partial estimate*; use [AWS Pricing Calculator](https://calculator.aws/) for full designs.

The sample model costs in aws-queue-worker.json are explicit hypothetical assumptions ($3 per million input and $15 per million output tokens), *not* pricing for any named model.
