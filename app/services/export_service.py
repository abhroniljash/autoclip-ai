import json
import logging
import zipfile
from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import Project, Clip, ExportJob
from app.config import EXPORTS_DIR, SUBTITLES_DIR
from app.services.video_service import render_clip
from app.services.subtitle_service import generate_srt_subtitles

logger = logging.getLogger("autoclip.export_service")

def build_project_zip_archive(
    db: Session,
    export_job_id: str
) -> str:
    """
    Renders selected clips (if not already rendered), generates subtitles and metadata,
    and consolidates them into a single downloadable ZIP archive.
    """
    job = db.query(ExportJob).filter(ExportJob.id == export_job_id).first()
    if not job:
        raise ValueError(f"Export job {export_job_id} not found")

    project = db.query(Project).filter(Project.id == job.project_id).first()
    if not project:
        raise ValueError(f"Project {job.project_id} not found")

    job.export_status = "processing"
    job.progress = 10
    db.commit()

    selected_clips = [c for c in project.clips if c.is_selected]
    if not selected_clips:
        # Fall back to all clips
        selected_clips = project.clips

    total_clips = len(selected_clips)
    zip_filename = f"{project.project_name.replace(' ', '_')}_clips.zip"
    zip_path = EXPORTS_DIR / f"{job.id}_{zip_filename}"
    
    # Parse requested resolution
    res_str = job.resolution or "1080x1920"
    target_w, target_h = (1080, 1920)
    if "x" in res_str:
        parts = res_str.split("x")
        target_w, target_h = int(parts[0]), int(parts[1])

    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zip_f:
        for idx, clip in enumerate(selected_clips):
            # 1. Ensure clip is rendered
            clip_file = Path(clip.output_file_path) if clip.output_file_path else None
            if not clip_file or not clip_file.exists():
                logger.info("Rendering clip %s before export...", clip.id)
                new_clip_path = EXPORTS_DIR / f"{clip.id}_final.mp4"
                
                # Check subtitle file
                sub_path = clip.subtitle_file_path
                render_clip(
                    input_video=project.source_reference,
                    output_clip_path=str(new_clip_path),
                    start_time=clip.start_time,
                    end_time=clip.end_time,
                    crop_mode=clip.crop_mode,
                    crop_x_offset=clip.crop_x_offset,
                    subtitle_file_path=sub_path,
                    bgm_file_path=clip.bgm_track,
                    bgm_volume=clip.bgm_volume,
                    normalize_audio=clip.normalize_audio,
                    target_width=target_w,
                    target_height=target_h
                )
                clip.output_file_path = str(new_clip_path)
                clip.clip_status = "ready"
                db.commit()
                clip_file = new_clip_path

            # Add MP4 to zip
            clean_title = "".join(c for c in clip.title if c.isalnum() or c in (" ", "-", "_")).strip()
            zip_video_name = f"Clip_{idx+1}_{clean_title[:30]}.mp4"
            zip_f.write(str(clip_file), arcname=f"videos/{zip_video_name}")

            # 2. Add Subtitles (.srt) to zip
            srt_path = SUBTITLES_DIR / f"{clip.id}.srt"
            transcript = project.analysis.transcript if project.analysis else []
            generate_srt_subtitles(
                transcript_segments=transcript or [],
                output_srt_path=str(srt_path),
                clip_start_time=clip.start_time,
                clip_end_time=clip.end_time
            )
            zip_f.write(str(srt_path), arcname=f"subtitles/Clip_{idx+1}_{clean_title[:30]}.srt")

            # 3. Add Social Media Kit & Captions text file
            meta = clip.metadata_info
            kit_lines = [
                f"=== SOCIAL MEDIA KIT: {clip.title} ===",
                f"Potential Score: {clip.potential_score}/100 ({clip.potential_category})",
                f"Duration: {clip.duration:.1f}s (Start: {clip.start_time:.1f}s | End: {clip.end_time:.1f}s)",
                "",
                "--- SUGGESTED TITLES ---",
            ]
            if meta and meta.suggested_titles:
                for t in meta.suggested_titles:
                    kit_lines.append(f"• {t}")
            
            kit_lines.extend([
                "",
                "--- INSTAGRAM & TIKTOK CAPTION ---",
                meta.instagram_caption if meta and meta.instagram_caption else "Watch till the end! 🔥",
                "",
                "--- YOUTUBE SHORTS DESCRIPTION ---",
                meta.shorts_description if meta and meta.shorts_description else "Viral short clip.",
                "",
                "--- TRENDING HASHTAGS ---",
                " ".join(meta.hashtags) if meta and meta.hashtags else "#shorts #viral #reels",
                "",
                "--- THUMBNAIL TEXT IDEAS ---",
            ])
            if meta and meta.thumbnail_text_suggestions:
                for th in meta.thumbnail_text_suggestions:
                    kit_lines.append(f"• {th}")

            zip_f.writestr(f"metadata/Clip_{idx+1}_social_kit.txt", "\n".join(kit_lines))

            # Update progress
            job.progress = int(10 + (idx + 1) / total_clips * 85)
            db.commit()

    job.zip_path = str(zip_path)
    job.export_status = "completed"
    job.progress = 100
    db.commit()
    
    return str(zip_path)
