# Long-running research agent

**Scenario:** Many tool calls, browser delays, checkpoints and resumability.

**Options:** Lambda + SQS segments (cheap idle, execution limits), ECS/Fargate worker (portable containers, warm capacity), AgentCore Runtime (managed isolated agent execution, its own billing/quota model).

**Benchmark:** identical model, prompts, tools and task suite; compare completion rate, warm/idle spend, cancellation/recovery, P95 and cost per successful research task.
