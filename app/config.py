import os
import shutil
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file automatically if present
env_file = BASE_DIR / ".env"
if env_file.exists():
    try:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass

STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
AUDIO_DIR = STORAGE_DIR / "audio"
CLIPS_DIR = STORAGE_DIR / "clips"
SUBTITLES_DIR = STORAGE_DIR / "subtitles"
EXPORTS_DIR = STORAGE_DIR / "exports"
BGM_DIR = STORAGE_DIR / "bgm"
STATIC_DIR = BASE_DIR / "app" / "static"

# Ensure all directories exist
for folder in [STORAGE_DIR, UPLOAD_DIR, AUDIO_DIR, CLIPS_DIR, SUBTITLES_DIR, EXPORTS_DIR, BGM_DIR, STATIC_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR}/autoclip.db")

# API Keys
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# FFmpeg Auto-Discovery
def find_ffmpeg_binary(name: str = "ffmpeg") -> str:
    env_key = f"{name.upper()}_PATH"
    if os.environ.get(env_key):
        return os.environ[env_key]
    
    # Check standard PATH
    path = shutil.which(name)
    if path:
        return path
        
    # Check known Windows locations
    exe_name = f"{name}.exe" if not name.endswith(".exe") else name
    known_paths = [
        Path(r"C:\Program Files\kdenlive\bin") / exe_name,
        Path(r"C:\Program Files (x86)\YouTube Playlist Downloader") / exe_name,
        Path(r"C:\ffmpeg\bin") / exe_name,
        Path(r"C:\Program Files\ffmpeg\bin") / exe_name,
    ]
    for p in known_paths:
        if p.exists():
            return str(p)
            
    return name  # fallback to name

FFMPEG_PATH = find_ffmpeg_binary("ffmpeg")
FFPROBE_PATH = find_ffmpeg_binary("ffprobe")

# Virality Evaluation Weights (Strictly following the project specification)
SCORING_WEIGHTS = {
    "hook_strength": 0.20,           # Opening Hook Strength: 20%
    "emotional_impact": 0.15,        # Emotional Impact and Curiosity: 15%
    "information_value": 0.15,       # Information Value and Novelty: 15%
    "context_completeness": 0.15,    # Context Completeness: 15%
    "shareability": 0.10,            # Shareability: 10%
    "content_pacing": 0.10,          # Content Pacing: 10%
    "audio_clarity": 0.10,           # Audio Clarity: 10%
    "visual_engagement": 0.05,       # Visual Engagement: 5%
}

# Subtitle Style Presets
SUBTITLE_PRESETS = {
    "bold_viral": {
        "name": "Bold Viral Caption Style",
        "description": "Bold uppercase font, neon yellow highlight on active keywords, TikTok & Reels favorite",
        "font_name": "Arial",
        "font_size": 46,
        "primary_color": "&H00FFFFFF",      # White in BGR
        "secondary_color": "&H0000FFFF",    # Yellow highlight
        "outline_color": "&H00000000",      # Solid black outline
        "outline_width": 3.5,
        "shadow": 1.5,
        "alignment": 2,                     # Bottom Center (or 5 for middle)
        "margin_v": 110,
        "uppercase": True
    },
    "clean_minimal": {
        "name": "Clean Minimal Style",
        "description": "Understated white typography with subtle drop shadow",
        "font_name": "Helvetica",
        "font_size": 38,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H00CCCCCC",
        "outline_color": "&H40000000",
        "outline_width": 1.5,
        "shadow": 1.0,
        "alignment": 2,
        "margin_v": 90,
        "uppercase": False
    },
    "podcast": {
        "name": "Podcast Caption Style",
        "description": "Readable modern sans-serif enclosed in a subtle contrast frame",
        "font_name": "Segoe UI",
        "font_size": 40,
        "primary_color": "&H00F0F0F0",
        "secondary_color": "&H0000D0FF",    # Orange / gold highlight
        "outline_color": "&H80000000",
        "outline_width": 2.5,
        "shadow": 2.0,
        "alignment": 2,
        "margin_v": 100,
        "uppercase": False
    },
    "cinematic": {
        "name": "Cinematic Subtitle Style",
        "description": "Letter-spaced classical aesthetic for documentary and story clips",
        "font_name": "Georgia",
        "font_size": 36,
        "primary_color": "&H00E0FFFF",      # Soft cream
        "secondary_color": "&H0000FFFF",
        "outline_color": "&H00000000",
        "outline_width": 2.0,
        "shadow": 1.0,
        "alignment": 2,
        "margin_v": 80,
        "uppercase": False
    },
    "highlight_keyword": {
        "name": "Highlighted Keyword Style",
        "description": "High energy style highlighting impactful words in electric yellow and green",
        "font_name": "Impact",
        "font_size": 44,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H0000FF00",    # Electric Green
        "outline_color": "&H00000000",
        "outline_width": 3.8,
        "shadow": 2.0,
        "alignment": 2,
        "margin_v": 115,
        "uppercase": True
    }
}

# Supported Video Import Formats
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}
MAX_FILE_SIZE_MB = max(1, int(os.environ.get("MAX_UPLOAD_SIZE_MB", "1000")))  # hard upload limit in MiB
