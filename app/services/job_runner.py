"""Durable export job runner using a fresh database session."""
import logging
from pathlib import Path

from app.database import SessionLocal
from app.models import ExportJob
from app.services.export_service import build_project_zip_archive
from app.services.aws_storage import enabled as s3_enabled, upload_file as s3_upload

logger = logging.getLogger("autoclip.jobs")


def run_export_job(export_job_id: str) -> None:
    db = SessionLocal()
    try:
        path = build_project_zip_archive(db, export_job_id)
        job = db.query(ExportJob).filter(ExportJob.id == export_job_id).first()
        if job and s3_enabled() and Path(path).is_file():
            job.zip_path = s3_upload(path, f"users/{job.project.user_id}/exports/{job.id}.zip", "application/zip")
            db.commit()
    except Exception as exc:
        logger.exception("Export job %s failed", export_job_id)
        job = db.query(ExportJob).filter(ExportJob.id == export_job_id).first()
        if job:
            job.export_status = "failed"
            job.error_message = "Export processing failed. Please retry."
            db.commit()
        raise
    finally:
        db.close()
