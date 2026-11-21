"""SQS worker for CPU-heavy video jobs. API and worker must share the EFS work volume."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import time
import threading

import boto3
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Project, Clip
from app.services.pipeline import run_project_pipeline
from app.services.aws_storage import enabled, upload_file, AWS_REGION
from app.services.job_runner import run_export_job

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger("autoclip.worker")

QUEUE_URL = os.environ.get("SQS_QUEUE_URL", "").strip()
POLL_SECONDS = 20
STOP = False


def stop_worker(*_):
    global STOP
    STOP = True


def persist_project_media(project_id: str) -> None:
    if not enabled():
        return
    db: Session = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project or project.processing_status != "completed":
            return
        prefix = f"users/{project.user_id}/projects/{project.id}"
        if project.thumbnail_path and os.path.isfile(project.thumbnail_path):
            project.thumbnail_path = upload_file(project.thumbnail_path, f"{prefix}/project-thumbnail.jpg", "image/jpeg")
        for clip in db.query(Clip).filter(Clip.project_id == project.id).all():
            if clip.output_file_path and os.path.isfile(clip.output_file_path):
                clip.output_file_path = upload_file(clip.output_file_path, f"{prefix}/clips/{clip.id}.mp4", "video/mp4")
            if clip.thumbnail_path and os.path.isfile(clip.thumbnail_path):
                clip.thumbnail_path = upload_file(clip.thumbnail_path, f"{prefix}/clips/{clip.id}-thumbnail.jpg", "image/jpeg")
            if clip.subtitle_file_path and os.path.isfile(clip.subtitle_file_path):
                clip.subtitle_file_path = upload_file(clip.subtitle_file_path, f"{prefix}/clips/{clip.id}.ass", "text/plain")
        db.commit()
    finally:
        db.close()


def visibility_heartbeat(sqs, receipt_handle: str, stop_event: threading.Event) -> None:
    while not stop_event.wait(240):
        try:
            sqs.change_message_visibility(
                QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle, VisibilityTimeout=900
            )
        except Exception:
            logger.exception("Could not extend SQS job visibility timeout")
            return

def main():
    if not QUEUE_URL:
        raise RuntimeError("SQS_QUEUE_URL must be configured for the worker.")
    sqs = boto3.client("sqs", region_name=AWS_REGION)
    signal.signal(signal.SIGTERM, stop_worker)
    signal.signal(signal.SIGINT, stop_worker)
    logger.info("AutoClip worker polling SQS in %s", AWS_REGION)

    while not STOP:
        response = sqs.receive_message(
            QueueUrl=QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=POLL_SECONDS,
            VisibilityTimeout=int(os.environ.get("SQS_VISIBILITY_TIMEOUT", "900")),
        )
        for message in response.get("Messages", []):
            stop_heartbeat = threading.Event()
            heartbeat = threading.Thread(
                target=visibility_heartbeat,
                args=(sqs, message["ReceiptHandle"], stop_heartbeat),
                daemon=True,
            )
            heartbeat.start()
            try:
                payload = json.loads(message["Body"])
                if payload.get("type") == "process_project":
                    project_id = str(payload["project_id"])
                    asyncio.run(run_project_pipeline(project_id))
                    persist_project_media(project_id)
                elif payload.get("type") == "process_export":
                    run_export_job(str(payload["export_job_id"]))
                else:
                    logger.warning("Ignoring unsupported SQS message type")
                sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=message["ReceiptHandle"])
            except Exception:
                logger.exception("Project job failed; leaving message for SQS retry/DLQ")
                time.sleep(2)
            finally:
                stop_heartbeat.set()
                heartbeat.join(timeout=2)


if __name__ == "__main__":
    main()
