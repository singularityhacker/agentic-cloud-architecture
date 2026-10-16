"""Reference implementation: queue + worker + state + artifacts.

No model calls, AgentCore or production-grade infrastructure claim.
CDK synth is local; deployment requires AWS credentials and incurs charges.
"""
from pathlib import Path

from aws_cdk import (
    App, CfnOutput, Duration, RemovalPolicy, Stack, Tags,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_lambda_event_sources as event_sources,
    aws_s3 as s3,
    aws_sqs as sqs,
)
from constructs import Construct


class ServerlessQueueStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        dlq = sqs.Queue(self, "DeadLetters", retention_period=Duration.days(4))
        queue = sqs.Queue(self, "TaskQueue",
                          visibility_timeout=Duration.seconds(90),
                          dead_letter_queue=sqs.DeadLetterQueue(queue=dlq, max_receive_count=3))
        table = dynamodb.Table(
            self, "TaskState",
            partition_key=dynamodb.Attribute(name="pk", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )
        bucket = s3.Bucket(
            self, "Artifacts",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
        )
        worker = lambda_.Function(
            self, "Worker",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset(str(Path(__file__).parent / "worker")),
            memory_size=256,
            timeout=Duration.seconds(20),
            reserved_concurrent_executions=2,
        )
        worker.add_event_source(event_sources.SqsEventSource(queue, batch_size=1, max_concurrency=2))
        table.grant_read_write_data(worker)
        bucket.grant_read_write(worker)
        Tags.of(self).add("project", "agentic-cloud-architecture")
        Tags.of(self).add("env", "study")
        CfnOutput(self, "QueueUrl", value=queue.queue_url)


app = App()
ServerlessQueueStack(app, "AgenticQueueReference")
app.synth()
