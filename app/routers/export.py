import os
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.models import Project, Clip, ExportJob
from app.schemas import ExportRequest, ExportJobResponse
from app.services.export_service import build_project_zip_archive
from app.services.subtitle_service import generate_srt_subtitles
from app.config import SUBTITLES_DIR

router = APIRouter(prefix="/api", tags=["Export"])
logger = logging.getLogger("autoclip.export")

@router.post("/projects/{project_id}/export", response_model=ExportJobResponse)
def create_export_job(
    project_id: str,
    payload: ExportRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiates batch export job for selected clips in a ZIP archive."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    job = ExportJob(
        project_id=project_id,
        export_status="pending",
        progress=0,
        resolution=payload.resolution or "1080x1920",
        quality=payload.quality or "high",
        aspect_ratio=payload.aspect_ratio or "9:16"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Launch ZIP creation in background
    background_tasks.add_task(build_project_zip_archive, db, job.id)
    return ExportJobResponse.model_validate(job)

@router.get("/export/{job_id}/status", response_model=ExportJobResponse)
def get_export_job_status(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Check progress of a batch export job."""
    job = db.query(ExportJob).join(Project).filter(ExportJob.id == job_id, Project.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    return ExportJobResponse.model_validate(job)

@router.get("/export/{job_id}/download")
def download_export_zip(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Download consolidated ZIP archive containing clips, subtitles, and metadata."""
    job = db.query(ExportJob).join(Project).filter(ExportJob.id == job_id, Project.user_id == user.id).first()
    if not job or not job.zip_path or not Path(job.zip_path).exists():
        raise HTTPException(status_code=404, detail="Export ZIP archive is not ready or missing.")

    filename = Path(job.zip_path).name
    return FileResponse(
        path=job.zip_path,
        media_type="application/zip",
        filename=filename
    )

@router.get("/clips/{clip_id}/download")
def download_single_clip(clip_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Download single rendered 9:16 vertical video clip."""
    clip = db.query(Clip).join(Project).filter(Clip.id == clip_id, Project.user_id == user.id).first()
    if not clip or not clip.output_file_path or not Path(clip.output_file_path).exists():
        raise HTTPException(status_code=404, detail="Rendered clip not found. Please render the clip first.")

    safe_title = "".join(c for c in clip.title if c.isalnum() or c in (" ", "-", "_")).strip()
    return FileResponse(
        path=clip.output_file_path,
        media_type="video/mp4",
        filename=f"{safe_title[:30]}.mp4"
    )

@router.get("/clips/{clip_id}/subtitles")
def download_clip_subtitles(clip_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Download synchronized .srt subtitle file for this clip."""
    clip = db.query(Clip).join(Project).filter(Clip.id == clip_id, Project.user_id == user.id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    project = clip.project
    transcript = project.analysis.transcript if project and project.analysis else []
    
    srt_path = SUBTITLES_DIR / f"{clip.id}_download.srt"
    generate_srt_subtitles(
        transcript_segments=transcript or [],
        output_srt_path=str(srt_path),
        clip_start_time=clip.start_time,
        clip_end_time=clip.end_time
    )

    return FileResponse(
        path=str(srt_path),
        media_type="text/plain",
        filename=f"subtitles_{clip.id[:8]}.srt"
    )
