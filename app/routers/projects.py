import os
import shutil
import logging
from pathlib import Path
from urllib.parse import urlsplit
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.models import Project, Clip, VideoAnalysis
from app.schemas import (
    ProjectResponse, ProjectDetailResponse, ProjectCreateURL, DashboardStatsResponse
)
from app.config import UPLOAD_DIR, ALLOWED_VIDEO_EXTENSIONS, MAX_FILE_SIZE_MB
from app.services.pipeline import run_project_pipeline

router = APIRouter(prefix="/api", tags=["Projects"])
logger = logging.getLogger("autoclip.projects")

@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetch dashboard statistics and recent projects."""
    total_projects = db.query(Project).filter(Project.user_id == user.id).count()
    completed_projects = db.query(Project).filter(Project.user_id == user.id, Project.processing_status == "completed").count()
    total_clips = db.query(Clip).join(Project).filter(Project.user_id == user.id).count()
    
    recent = db.query(Project).filter(Project.user_id == user.id).order_by(Project.created_at.desc()).limit(8).all()
    
    # Calculate clip counts
    recent_responses = []
    for p in recent:
        p_resp = ProjectResponse.model_validate(p)
        p_resp.clip_count = len(p.clips)
        recent_responses.append(p_resp)
        
    return {
        "total_projects": total_projects,
        "total_videos_processed": completed_projects,
        "total_clips_generated": total_clips,
        "recent_projects": recent_responses
    }

@router.get("/projects", response_model=List[ProjectResponse])
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all projects ordered by newest first."""
    projects = db.query(Project).filter(Project.user_id == user.id).order_by(Project.created_at.desc()).all()
    results = []
    for p in projects:
        resp = ProjectResponse.model_validate(p)
        resp.clip_count = len(p.clips)
        results.append(resp)
    return results

@router.get("/projects/{project_id}", response_model=ProjectDetailResponse)
def get_project_detail(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetch complete project details including AI analysis results and clips."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    resp = ProjectDetailResponse.model_validate(project)
    resp.clip_count = len(project.clips)
    return resp

@router.get("/projects/{project_id}/thumbnail")
def get_project_thumbnail(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project or not project.thumbnail_path or not Path(project.thumbnail_path).is_file():
        raise HTTPException(status_code=404, detail="Project thumbnail not found.")
    return FileResponse(project.thumbnail_path, media_type="image/jpeg")
@router.post("/projects/upload", response_model=ProjectResponse)
async def upload_video_project(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_name: Optional[str] = Form(None),
    target_clip_count: int = Form(5),
    duration_preference: str = Form("30-60"),
    language: str = Form("en"),
    default_style: str = Form("bold_viral"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a video file (MP4, MOV, WebM), validate file type and size,
    and trigger the autonomous AI repurposing pipeline in the background.
    """
    original_name = Path(file.filename or "video").name
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}"
        )

    if not 1 <= target_clip_count <= 20:
        raise HTTPException(status_code=422, detail="Target clip count must be between 1 and 20.")
    if duration_preference not in {"20-40", "30-60", "60-90", "auto"}:
        raise HTTPException(status_code=422, detail="Unsupported clip duration preference.")
    if language not in {"en", "bn", "hi"}:
        raise HTTPException(status_code=422, detail="Unsupported subtitle language.")
    if default_style not in {"bold_viral", "clean_minimal", "podcast", "cinematic", "highlight_keyword"}:
        raise HTTPException(status_code=422, detail="Unsupported subtitle style.")

    p_name = (project_name or Path(original_name).stem or "Untitled Video Project").strip()[:255]
    project = Project(
        project_name=p_name,
        source_type="upload",
        source_reference="",
        user_id=user.id,
        target_clip_count=target_clip_count,
        duration_preference=duration_preference,
        language=language,
        default_style=default_style,
        processing_status="pending",
        progress=0
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Never use the client-provided filename as a filesystem path.
    target_file = UPLOAD_DIR / f"{project.id}{ext}"
    try:
        from app.security import save_video_upload
        await save_video_upload(file, target_file, MAX_FILE_SIZE_MB * 1024 * 1024)
    except HTTPException:
        db.delete(project)
        db.commit()
        raise
    except Exception:
        logger.exception("Failed to store uploaded video for project %s", project.id)
        db.delete(project)
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to store uploaded video.")

    project.source_reference = str(target_file)
    db.commit()

    # Trigger asynchronous background processing pipeline
    background_tasks.add_task(run_project_pipeline, project.id)

    resp = ProjectResponse.model_validate(project)
    resp.clip_count = 0
    return resp

@router.post("/projects/youtube", response_model=ProjectResponse)
async def import_youtube_project(
    background_tasks: BackgroundTasks,
    payload: ProjectCreateURL,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Import video from an authorized YouTube URL.
    Validates permissions and compliance. If direct download is restricted by YouTube,
    guides the user to upload the original video file.
    """
    url = payload.youtube_url.strip()
    parsed_url = urlsplit(url)
    allowed_hosts = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname not in allowed_hosts
        or parsed_url.username is not None
        or parsed_url.password is not None
        or parsed_url.port not in (None, 443)
    ):
        raise HTTPException(status_code=400, detail="Only valid HTTPS YouTube video URLs are supported.")

    # 1. Inspect YouTube URL using authorized oEmbed / metadata inspection
    import urllib.request
    import json
    
    video_title = payload.project_name
    try:
        oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
        req = urllib.request.Request(oembed_url, headers={"User-Agent": "AutoClipAI/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            video_title = data.get("title", payload.project_name)
    except Exception as e:
        logger.info("oEmbed fetch failed or skipped: %s", e)

    # 2. Check if authorized media stream is accessible via yt-dlp
    import subprocess
    target_file = UPLOAD_DIR / f"yt_import_{uuid.uuid4().hex}.mp4"
    
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--max-filesize", f"{MAX_FILE_SIZE_MB}M",
        "--no-playlist",
        "-o", str(target_file),
        url
    ]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=180)
        if proc.returncode != 0 or not target_file.exists():
            raise HTTPException(
                status_code=400,
                detail=(
                    "Could not retrieve media stream from YouTube URL under current access policies. "
                    "Please upload your original MP4/MOV file directly using the Video Upload option."
                )
            )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="YouTube stream download timed out.")
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=(
                f"YouTube import restricted: {e}. "
                "Please upload the video file directly."
            )
        )

    # Create Project Record
    project = Project(
        project_name=video_title or payload.project_name,
        source_type="youtube",
        source_reference=str(target_file),
        user_id=user.id,
        source_title=video_title,
        target_clip_count=payload.target_clip_count or 5,
        duration_preference=payload.duration_preference or "30-60",
        language=payload.language or "en",
        default_style=payload.default_style or "bold_viral",
        processing_status="pending",
        progress=0
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Launch Pipeline
    background_tasks.add_task(run_project_pipeline, project.id)

    resp = ProjectResponse.model_validate(project)
    resp.clip_count = 0
    return resp

@router.delete("/projects/{project_id}")
def delete_project(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a project and remove associated files."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Clean up files
    try:
        if project.source_reference and Path(project.source_reference).exists():
            Path(project.source_reference).unlink(missing_ok=True)
        if project.thumbnail_path and Path(project.thumbnail_path).exists():
            Path(project.thumbnail_path).unlink(missing_ok=True)
        for clip in project.clips:
            if clip.output_file_path and Path(clip.output_file_path).exists():
                Path(clip.output_file_path).unlink(missing_ok=True)
            if clip.thumbnail_path and Path(clip.thumbnail_path).exists():
                Path(clip.thumbnail_path).unlink(missing_ok=True)
            if clip.subtitle_file_path and Path(clip.subtitle_file_path).exists():
                Path(clip.subtitle_file_path).unlink(missing_ok=True)
    except Exception as e:
        logger.warning("Error deleting files for project %s: %s", project_id, e)

    db.delete(project)
    db.commit()
    return {"status": "success", "message": f"Project {project_id} deleted"}
