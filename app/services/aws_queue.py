"""SQS job publishing for durable video-processing work."""
import json
import os

import boto3

AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL", "").strip()
_client = None


def _send(payload: dict) -> bool:
    """Publish a project job. Returns False when local dev queue mode is disabled."""
    if not SQS_QUEUE_URL:
        return False
    global _client
    if _client is None:
        _client = boto3.client("sqs", region_name=AWS_REGION)
    _client.send_message(
        QueueUrl=SQS_QUEUE_URL,
        MessageBody=json.dumps(payload),
    )
    return True


def enqueue_project(project_id: str) -> bool:
    return _send({"type": "process_project", "project_id": project_id})


def enqueue_export(export_job_id: str) -> bool:
    return _send({"type": "process_export", "export_job_id": export_job_id})
