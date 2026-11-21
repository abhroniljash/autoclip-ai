import logging
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.models import Clip, Project
from app.schemas import ClipResponse, ClipUpdate
from app.config import CLIPS_DIR, SUBTITLES_DIR, BGM_DIR, SUBTITLE_PRESETS
from app.services.video_service import render_clip, generate_thumbnail
from app.services.subtitle_service import generate_ass_subtitles

router = APIRouter(prefix="/api/clips", tags=["Clips"])
logger = logging.getLogger("autoclip.clips")

@router.get("/bgm/tracks", response_model=List[Dict[str, str]])
def list_bgm_tracks():
    """Returns available royalty-free background music tracks."""
    tracks = [
        {"id": "lofi_chill", "name": "Lo-Fi Midnight Chill", "category": "Relaxed & Story", "duration": "2:15"},
        {"id": "upbeat_energy", "name": "Dynamic Tech Pulse", "category": "Energetic & Fast", "duration": "1:45"},
        {"id": "cinematic_ambient", "name": "Cinematic Storyteller", "category": "Emotional & Deep", "duration": "2:30"},
        {"id": "corporate_groove", "name": "Modern Creator Groove", "category": "Educational & Podcast", "duration": "2:05"}
    ]
    return tracks

@router.get("/subtitles/presets")
def list_subtitle_presets():
    """Returns the 5 subtitle styling presets with their visual configuration."""
    return SUBTITLE_PRESETS

@router.get("/{clip_id}/media")
def get_clip_media(clip_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    clip = db.query(Clip).join(Project).filter(Clip.id == clip_id, Project.user_id == user.id).first()
    if not clip or not clip.output_file_path:
        raise HTTPException(status_code=404, detail="Rendered clip not found.")
    if clip.output_file_path.startswith("s3://"):
        from app.services.aws_storage import presigned_url
        return RedirectResponse(presigned_url(clip.output_file_path), status_code=307)
    if not Path(clip.output_file_path).is_file():
        raise HTTPException(status_code=404, detail="Rendered clip not found.")
    return FileResponse(clip.output_file_path, media_type="video/mp4")

@router.get("/{clip_id}/thumbnail")
def get_clip_thumbnail(clip_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    clip = db.query(Clip).join(Project).filter(Clip.id == clip_id, Project.user_id == user.id).first()
    if not clip or not clip.thumbnail_path:
        raise HTTPException(status_code=404, detail="Clip thumbnail not found.")
    if clip.thumbnail_path.startswith("s3://"):
        from app.services.aws_storage import presigned_url
        return RedirectResponse(presigned_url(clip.thumbnail_path), status_code=307)
    if not Path(clip.thumbnail_path).is_file():
        raise HTTPException(status_code=404, detail="Clip thumbnail not found.")
    return FileResponse(clip.thumbnail_path, media_type="image/jpeg")
@router.get("/{clip_id}", response_model=ClipResponse)
def get_clip(clip_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetch clip details by ID."""
    clip = db.query(Clip).join(Project).filter(Clip.id == clip_id, Project.user_id == user.id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    return ClipResponse.model_validate(clip)

@router.patch("/{clip_id}", response_model=ClipResponse)
def update_clip_settings(clip_id: str, payload: ClipUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update clip parameters (trim start/end, crop mode, subtitle style, audio settings)."""
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(clip, field, value)

    # Recalculate duration if start or end changed
    if payload.start_time is not None or payload.end_time is not None:
        clip.duration = max(1.0, clip.end_time - clip.start_time)

    db.commit()
    db.refresh(clip)
    return ClipResponse.model_validate(clip)

@router.post("/{clip_id}/render", response_model=ClipResponse)
def trigger_clip_re_render(clip_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Re-renders the vertical 9:16 clip using FFmpeg with latest trim, crop,
    subtitle style, and audio normalization settings.
    """
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
        
    project = clip.project
    if not project or not Path(project.source_reference).exists():
        raise HTTPException(status_code=400, detail="Source video is missing or invalid")

    clip.clip_status = "rendering"
    db.commit()

    try:
        # 1. Regenerate ASS Subtitles if enabled
        sub_path = None
        if clip.enable_subtitles and project.analysis:
            sub_file = SUBTITLES_DIR / f"{clip.id}_rendered.ass"
            generate_ass_subtitles(
                transcript_segments=project.analysis.transcript or [],
                output_ass_path=str(sub_file),
                style_key=clip.subtitle_style or "bold_viral",
                clip_start_time=clip.start_time,
                clip_end_time=clip.end_time
            )
            sub_path = str(sub_file)
            clip.subtitle_file_path = sub_path

        # 2. Render Vertical 9:16 Video
        output_file = CLIPS_DIR / f"{clip.id}_edited.mp4"
        render_clip(
            input_video=project.source_reference,
            output_clip_path=str(output_file),
            start_time=clip.start_time,
            end_time=clip.end_time,
            crop_mode=clip.crop_mode,
            crop_x_offset=clip.crop_x_offset,
            subtitle_file_path=sub_path,
            bgm_file_path=clip.bgm_track if clip.enable_music else None,
            bgm_volume=clip.bgm_volume,
            normalize_audio=clip.normalize_audio,
            target_width=1080,
            target_height=1920
        )

        # 3. Update Thumbnail
        thumb_file = CLIPS_DIR / f"{clip.id}_thumb.jpg"
        generate_thumbnail(
            str(output_file),
            str(thumb_file),
            timestamp=min(1.5, clip.duration * 0.2)
        )

        clip.output_file_path = str(output_file)
        clip.thumbnail_path = str(thumb_file)
        clip.clip_status = "ready"
        db.commit()
        db.refresh(clip)
        return ClipResponse.model_validate(clip)

    except Exception as e:
        logger.error("Failed to re-render clip %s: %s", clip_id, e)
        clip.clip_status = "error"
        clip.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Rendering failed: {e}")
