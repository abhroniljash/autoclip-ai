import asyncio
import logging
import traceback
from pathlib import Path
from typing import Dict, Any

from app.database import SessionLocal
from app.models import Project, VideoAnalysis, Clip, ClipMetadata
from app.config import (
    UPLOAD_DIR, AUDIO_DIR, CLIPS_DIR, SUBTITLES_DIR
)
from app.services.video_service import (
    probe_video, extract_audio, render_clip, generate_thumbnail
)
from app.services.face_tracking import analyze_speaker_framing
from app.services.subtitle_service import generate_ass_subtitles
from app.services.audio_service import process_audio_transcription
from app.services.ai_scoring import generate_clip_candidates

logger = logging.getLogger("autoclip.pipeline")

async def run_project_pipeline(project_id: str):
    """
    Main asynchronous background pipeline that coordinates:
    Audio Extraction -> Speech Transcription -> AI Analysis & Scoring ->
    Smart Reframing & Face Tracking -> Subtitle Generation -> Clip Rendering.
    """
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            logger.error("Pipeline failed: Project %s not found in DB", project_id)
            return

        if project.processing_status == "failed":
            logger.info("Resetting partial artifacts before retry for Project %s", project_id)
            for old_clip in list(project.clips):
                for old_path in (old_clip.output_file_path, old_clip.thumbnail_path, old_clip.subtitle_file_path):
                    if old_path and not old_path.startswith("s3://") and Path(old_path).is_file():
                        Path(old_path).unlink(missing_ok=True)
                db.delete(old_clip)
            if project.analysis is not None:
                db.delete(project.analysis)
            db.commit()

        logger.info("Starting processing pipeline for Project %s ('%s')", project_id, project.project_name)
        
        project.error_message = None
        project.processing_status = "pending"
        project.progress = 0
        db.commit()

        # Step 1: Probe Video
        project.processing_status = "extracting_audio"
        project.progress = 10
        db.commit()

        video_path = project.source_reference
        probe_info = probe_video(video_path)
        project.video_duration = probe_info["duration"]
        project.video_resolution = probe_info["resolution"]
        project.fps = probe_info["fps"]
        
        # Generate project thumbnail
        thumb_path = UPLOAD_DIR / f"{project_id}_thumb.jpg"
        generate_thumbnail(video_path, str(thumb_path), timestamp=min(2.0, probe_info["duration"] * 0.1))
        project.thumbnail_path = str(thumb_path)
        db.commit()

        # Step 2: Audio Extraction
        audio_path = AUDIO_DIR / f"{project_id}.wav"
        extract_audio(video_path, str(audio_path))
        
        project.processing_status = "transcribing"
        project.progress = 30
        db.commit()

        # Step 3: Transcription
        transcript_segments = await process_audio_transcription(
            audio_path=str(audio_path),
            total_duration=project.video_duration,
            language=project.language or "en"
        )
        
        raw_text = " ".join([s.get("text", "") for s in transcript_segments])
        analysis_record = VideoAnalysis(
            project_id=project_id,
            transcript=transcript_segments,
            raw_transcript_text=raw_text,
            video_summary=f"Analysis of {project.project_name} ({probe_info['duration']:.1f}s, {probe_info['resolution']})",
            detected_topics=["High-Retention Discussion", "Key Insights", "Story Arc"]
        )
        db.add(analysis_record)
        db.commit()

        # Step 4: AI Virality Analysis & Moment Selection
        project.processing_status = "analyzing"
        project.progress = 55
        db.commit()

        candidates = await generate_clip_candidates(
            transcript=transcript_segments,
            total_video_duration=project.video_duration,
            target_count=project.target_clip_count or 5,
            duration_pref=project.duration_preference or "30-60"
        )

        # Step 5: Video Reframing, Subtitling, and Rendering
        project.processing_status = "generating_clips"
        project.progress = 70
        db.commit()

        total_candidates = len(candidates)
        for idx, cand in enumerate(candidates):
            # 5a. Smart Speaker Tracking
            framing = analyze_speaker_framing(
                video_path=video_path,
                start_time=cand["start_time"],
                end_time=cand["end_time"]
            )
            
            crop_mode = framing.get("recommended_mode", "auto_face")
            crop_x = framing.get("optimal_crop_x", 0.5)

            # 5b. Generate ASS Subtitles
            sub_path = SUBTITLES_DIR / f"{project_id}_clip_{idx+1}.ass"
            generate_ass_subtitles(
                transcript_segments=transcript_segments,
                output_ass_path=str(sub_path),
                style_key=project.default_style or "bold_viral",
                clip_start_time=cand["start_time"],
                clip_end_time=cand["end_time"]
            )

            # 5c. Render Vertical 9:16 Video Clip
            clip_output_path = CLIPS_DIR / f"{project_id}_clip_{idx+1}.mp4"
            render_clip(
                input_video=video_path,
                output_clip_path=str(clip_output_path),
                start_time=cand["start_time"],
                end_time=cand["end_time"],
                crop_mode=crop_mode,
                crop_x_offset=crop_x,
                subtitle_file_path=str(sub_path),
                normalize_audio=True,
                target_width=1080,
                target_height=1920
            )

            # 5d. Clip Thumbnail
            clip_thumb_path = CLIPS_DIR / f"{project_id}_clip_{idx+1}_thumb.jpg"
            generate_thumbnail(
                str(clip_output_path),
                str(clip_thumb_path),
                timestamp=min(1.5, cand["duration"] * 0.2)
            )

            # 5e. Save Clip to Database
            clip_record = Clip(
                project_id=project_id,
                title=cand["title"],
                start_time=cand["start_time"],
                end_time=cand["end_time"],
                duration=cand["duration"],
                potential_score=cand["potential_score"],
                potential_category=cand["potential_category"],
                scoring_breakdown=cand["scoring_breakdown"],
                selection_reason=cand["selection_reason"],
                suggested_hook=cand["suggested_hook"],
                key_moments=cand["key_moments"],
                crop_mode=crop_mode,
                crop_x_offset=crop_x,
                subtitle_style=project.default_style or "bold_viral",
                output_file_path=str(clip_output_path),
                thumbnail_path=str(clip_thumb_path),
                subtitle_file_path=str(sub_path),
                clip_status="ready",
                is_selected=True
            )
            db.add(clip_record)
            db.flush()

            # 5f. Save Social Media Metadata
            social = cand.get("social_kit", {})
            meta_record = ClipMetadata(
                clip_id=clip_record.id,
                suggested_titles=social.get("suggested_titles", []),
                instagram_caption=social.get("instagram_caption", ""),
                shorts_description=social.get("shorts_description", ""),
                hashtags=social.get("hashtags", []),
                opening_hook_text=cand["suggested_hook"],
                thumbnail_text_suggestions=social.get("thumbnail_text_suggestions", []),
                clip_summary=social.get("clip_summary", "")
            )
            db.add(meta_record)
            db.commit()

            # Update progress
            project.progress = int(70 + (idx + 1) / total_candidates * 28)
            db.commit()

        # Step 6: Completion
        project.processing_status = "completed"
        project.progress = 100
        db.commit()
        logger.info("Pipeline completed successfully for Project %s", project_id)

    except Exception as e:
        logger.error("Error in project pipeline: %s\n%s", e, traceback.format_exc())
        project.processing_status = "failed"
        project.error_message = str(e)
        db.commit()
    finally:
        db.close()
