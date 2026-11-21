from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

# Project Schemas
class ProjectBase(BaseModel):
    project_name: str
    target_clip_count: Optional[int] = 5
    duration_preference: Optional[str] = "30-60"
    language: Optional[str] = "en"
    default_style: Optional[str] = "bold_viral"

class ProjectCreateURL(ProjectBase):
    youtube_url: str

class ProjectUpdate(BaseModel):
    project_name: Optional[str] = None
    target_clip_count: Optional[int] = None
    duration_preference: Optional[str] = None
    language: Optional[str] = None
    default_style: Optional[str] = None

class ClipMetadataResponse(BaseModel):
    id: str
    clip_id: str
    suggested_titles: Optional[List[str]] = []
    instagram_caption: Optional[str] = None
    shorts_description: Optional[str] = None
    hashtags: Optional[List[str]] = []
    opening_hook_text: Optional[str] = None
    thumbnail_text_suggestions: Optional[List[str]] = []
    clip_summary: Optional[str] = None

    class Config:
        from_attributes = True

class ClipResponse(BaseModel):
    id: str
    project_id: str
    title: str
    start_time: float
    end_time: float
    duration: float
    potential_score: float
    potential_category: str
    scoring_breakdown: Optional[Dict[str, float]] = None
    selection_reason: Optional[str] = None
    suggested_hook: Optional[str] = None
    key_moments: Optional[List[Dict[str, Any]]] = []
    
    crop_mode: str
    crop_x_offset: float
    subtitle_style: str
    font_size: int
    primary_color: str
    highlight_color: str
    enable_subtitles: bool
    enable_music: bool
    bgm_track: Optional[str] = None
    bgm_volume: float
    normalize_audio: bool
    
    is_selected: bool
    clip_status: str
    output_file_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    subtitle_file_path: Optional[str] = None
    metadata_info: Optional[ClipMetadataResponse] = None

    class Config:
        from_attributes = True

class ClipUpdate(BaseModel):
    title: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    crop_mode: Optional[str] = None
    crop_x_offset: Optional[float] = None
    subtitle_style: Optional[str] = None
    font_size: Optional[int] = None
    primary_color: Optional[str] = None
    highlight_color: Optional[str] = None
    enable_subtitles: Optional[bool] = None
    enable_music: Optional[bool] = None
    bgm_track: Optional[str] = None
    bgm_volume: Optional[float] = None
    normalize_audio: Optional[bool] = None
    is_selected: Optional[bool] = None

class VideoAnalysisResponse(BaseModel):
    id: str
    project_id: str
    video_summary: Optional[str] = None
    detected_topics: Optional[List[str]] = []
    raw_transcript_text: Optional[str] = None

    class Config:
        from_attributes = True

class ProjectResponse(BaseModel):
    id: str
    project_name: str
    source_type: str
    source_reference: str
    source_title: Optional[str] = None
    video_duration: float
    video_resolution: Optional[str] = None
    fps: float
    thumbnail_path: Optional[str] = None
    processing_status: str
    progress: int
    error_message: Optional[str] = None
    clip_count: Optional[int] = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProjectDetailResponse(ProjectResponse):
    analysis: Optional[VideoAnalysisResponse] = None
    clips: List[ClipResponse] = []

class DashboardStatsResponse(BaseModel):
    total_projects: int
    total_videos_processed: int
    total_clips_generated: int
    recent_projects: List[ProjectResponse]

class ExportRequest(BaseModel):
    clip_ids: Optional[List[str]] = None
    resolution: Optional[str] = "1080x1920"
    quality: Optional[str] = "high"
    aspect_ratio: Optional[str] = "9:16"
    include_zip: Optional[bool] = True

class ExportJobResponse(BaseModel):
    id: str
    project_id: str
    export_status: str
    progress: int
    resolution: str
    quality: str
    aspect_ratio: str
    output_path: Optional[str] = None
    zip_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
