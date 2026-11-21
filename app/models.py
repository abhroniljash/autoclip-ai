import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, ForeignKey, DateTime, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    project_name = Column(String(255), nullable=False)
    source_type = Column(String(50), default="upload")  # "upload" or "youtube"
    source_reference = Column(Text, nullable=False)     # File path or YouTube URL
    source_title = Column(String(255), nullable=True)
    video_duration = Column(Float, default=0.0)
    video_resolution = Column(String(50), nullable=True)
    fps = Column(Float, default=30.0)
    thumbnail_path = Column(String(500), nullable=True)
    
    # Workflow preferences
    target_clip_count = Column(Integer, default=5)
    duration_preference = Column(String(50), default="30-60") # "20-40", "30-60", "60-90", "auto"
    language = Column(String(10), default="en")                # "en", "bn", "hi"
    default_style = Column(String(50), default="bold_viral")
    
    # Processing state
    processing_status = Column(String(50), default="pending") 
    # "pending", "extracting_audio", "transcribing", "analyzing", "generating_clips", "completed", "failed"
    progress = Column(Integer, default=0) # 0 to 100
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="projects")
    analysis = relationship("VideoAnalysis", back_populates="project", uselist=False, cascade="all, delete-orphan")
    clips = relationship("Clip", back_populates="project", cascade="all, delete-orphan", order_by="desc(Clip.potential_score)")
    export_jobs = relationship("ExportJob", back_populates="project", cascade="all, delete-orphan")


class VideoAnalysis(Base):
    __tablename__ = "video_analyses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, unique=True)
    transcript = Column(JSON, nullable=True)  # List of {text, start, end, words: [{word, start, end}]}
    raw_transcript_text = Column(Text, nullable=True)
    video_summary = Column(Text, nullable=True)
    detected_topics = Column(JSON, nullable=True)
    analysis_result = Column(JSON, nullable=True)  # Raw full AI response
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="analysis")


class Clip(Base):
    __tablename__ = "clips"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)
    
    # Virality & Scoring
    potential_score = Column(Float, nullable=False)  # 0.0 to 100.0
    potential_category = Column(String(20), nullable=False) # "High", "Medium", "Low"
    scoring_breakdown = Column(JSON, nullable=True)
    # {
    #   "hook_strength": 92, "emotional_impact": 85, "information_value": 90,
    #   "context_completeness": 95, "shareability": 88, "content_pacing": 82,
    #   "audio_clarity": 90, "visual_engagement": 85
    # }
    selection_reason = Column(Text, nullable=True)
    suggested_hook = Column(String(255), nullable=True)
    key_moments = Column(JSON, nullable=True) # list of highlight timestamp descriptions

    # Editing configurations
    crop_mode = Column(String(50), default="auto_face") # "auto_face", "center", "left", "right", "split_screen"
    crop_x_offset = Column(Float, default=0.5)          # Manual override center ratio (0.0 to 1.0)
    subtitle_style = Column(String(50), default="bold_viral")
    font_size = Column(Integer, default=44)
    primary_color = Column(String(20), default="#FFFFFF")
    highlight_color = Column(String(20), default="#FFFF00")
    enable_subtitles = Column(Boolean, default=True)
    enable_music = Column(Boolean, default=False)
    bgm_track = Column(String(100), nullable=True)
    bgm_volume = Column(Float, default=0.15)            # 0.0 to 1.0
    normalize_audio = Column(Boolean, default=True)
    
    # State & File Outputs
    is_selected = Column(Boolean, default=True)
    clip_status = Column(String(50), default="ready")   # "pending", "rendering", "ready", "error"
    output_file_path = Column(String(500), nullable=True)
    thumbnail_path = Column(String(500), nullable=True)
    subtitle_file_path = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="clips")
    metadata_info = relationship("ClipMetadata", back_populates="clip", uselist=False, cascade="all, delete-orphan")


class ClipMetadata(Base):
    __tablename__ = "clip_metadata"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    clip_id = Column(String(36), ForeignKey("clips.id"), nullable=False, unique=True)
    suggested_titles = Column(JSON, nullable=True) # List of 3 catchy titles
    instagram_caption = Column(Text, nullable=True)
    shorts_description = Column(Text, nullable=True)
    hashtags = Column(JSON, nullable=True)         # List of strings
    opening_hook_text = Column(String(255), nullable=True)
    thumbnail_text_suggestions = Column(JSON, nullable=True)
    clip_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    clip = relationship("Clip", back_populates="metadata_info")


class ExportJob(Base):
    __tablename__ = "export_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    export_status = Column(String(50), default="pending") # "pending", "processing", "completed", "failed"
    progress = Column(Integer, default=0)
    resolution = Column(String(20), default="1080x1920") # "1080x1920" or "720x1280"
    quality = Column(String(20), default="high")
    aspect_ratio = Column(String(20), default="9:16")
    output_path = Column(String(500), nullable=True)
    zip_path = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="export_jobs")
