import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from app.config import FFMPEG_PATH, FFPROBE_PATH

logger = logging.getLogger("autoclip.video_service")

class VideoServiceError(Exception):
    pass

def run_command(cmd: list, timeout: int = 600) -> subprocess.CompletedProcess:
    """Run an external command safely with timeout and logging."""
    logger.debug("Executing command: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False
        )
        if result.returncode != 0:
            logger.error("Command failed [%d]: %s", result.returncode, result.stderr)
            raise VideoServiceError(f"Command failed with code {result.returncode}: {result.stderr[:500]}")
        return result
    except subprocess.TimeoutExpired:
        raise VideoServiceError(f"Command timed out after {timeout} seconds")
    except FileNotFoundError as e:
        raise VideoServiceError(f"Executable not found: {cmd[0]}. Error: {e}")

def probe_video(video_path: str) -> Dict[str, Any]:
    """Probe video file using ffprobe to obtain metadata (duration, resolution, fps)."""
    p = Path(video_path)
    if not p.exists():
        raise VideoServiceError(f"Video file not found: {video_path}")

    cmd = [
        FFPROBE_PATH,
        "-v", "error",
        "-show_entries", "format=duration,size,bit_rate:stream=width,height,r_frame_rate,codec_name,codec_type",
        "-of", "json",
        str(video_path)
    ]
    result = run_command(cmd, timeout=30)
    data = json.loads(result.stdout)
    
    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    
    duration = float(data.get("format", {}).get("duration", 0.0))
    width = int(video_stream.get("width", 1920)) if video_stream else 1920
    height = int(video_stream.get("height", 1080)) if video_stream else 1080
    
    fps = 30.0
    if video_stream and "r_frame_rate" in video_stream:
        r_rate = video_stream["r_frame_rate"]
        if "/" in r_rate:
            num, den = r_rate.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 30.0
        else:
            fps = float(r_rate)
            
    return {
        "duration": duration,
        "width": width,
        "height": height,
        "resolution": f"{width}x{height}",
        "fps": round(fps, 2),
        "size_bytes": int(data.get("format", {}).get("size", 0))
    }

def generate_thumbnail(video_path: str, output_path: str, timestamp: float = 2.0) -> str:
    """Generate a clean JPG thumbnail from the video at a given timestamp."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        FFMPEG_PATH,
        "-y",
        "-ss", str(max(0.1, timestamp)),
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "2",
        "-vf", "scale=640:-1",
        str(output_path)
    ]
    run_command(cmd, timeout=30)
    return str(output_path)

def extract_audio(video_path: str, audio_path: str) -> str:
    """Extract audio track as 16kHz mono WAV for speech transcription and analysis."""
    out = Path(audio_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        FFMPEG_PATH,
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(audio_path)
    ]
    run_command(cmd, timeout=120)
    return str(audio_path)

def render_clip(
    input_video: str,
    output_clip_path: str,
    start_time: float,
    end_time: float,
    crop_mode: str = "auto_face",
    crop_x_offset: float = 0.5,
    subtitle_file_path: Optional[str] = None,
    bgm_file_path: Optional[str] = None,
    bgm_volume: float = 0.15,
    normalize_audio: bool = True,
    target_width: int = 1080,
    target_height: int = 1920
) -> str:
    """
    Renders a 9:16 vertical video clip with accurate start/end cut,
    intelligent cropping, optional subtitle burn-in, and optional BGM.
    """
    out = Path(output_clip_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    
    duration = max(1.0, end_time - start_time)
    
    # 1. Video Filter Pipeline
    # Default 16:9 -> 9:16 crop logic:
    # Scale so height is target_height, then crop width to target_width
    video_filters = []
    
    if crop_mode == "split_screen":
        # Podcast / dual-speaker split screen:
        # Scale input to fit width, take left half for top, right half for bottom
        # Or take two crops from the original video and stack them vertically!
        half_height = target_height // 2
        # Crop two distinct windows from 16:9
        # Top panel: Left speaker (x=10%), Bottom panel: Right speaker (x=50%)
        # [0:v]split=2[v1][v2];
        # [v1]crop=ih*9/8:ih:0:0,scale=1080:960[top];
        # [v2]crop=ih*9/8:ih:(iw-ih*9/8):0,scale=1080:960[bot];
        # [top][bot]vstack[outv]
        split_filter = (
            f"split=2[v1][v2];"
            f"[v1]crop=ih*9/8:ih:0:0,scale={target_width}:{half_height}:flags=lanczos[top];"
            f"[v2]crop=ih*9/8:ih:(iw-ih*9/8):0,scale={target_width}:{half_height}:flags=lanczos[bot];"
            f"[top][bot]vstack"
        )
        video_filters.append(split_filter)
    else:
        # Standard dynamic single or auto-speaker 9:16 framing
        # Crop ratio 9:16 = 0.5625
        # Calculate horizontal offset based on crop_x_offset (0.0 to 1.0)
        # e.g., if crop_x_offset=0.5 -> center; 0.25 -> left; 0.75 -> right
        offset = max(0.0, min(1.0, crop_x_offset))
        crop_expr = f"crop=ih*9/16:ih:(iw-ih*9/16)*{offset}:0"
        scale_expr = f"scale={target_width}:{target_height}:flags=lanczos"
        video_filters.append(f"{crop_expr},{scale_expr}")

    # Add subtitle burn-in if requested and file exists
    if subtitle_file_path and Path(subtitle_file_path).exists():
        # Escape path for FFmpeg filter on Windows
        escaped_sub_path = str(subtitle_file_path).replace("\\", "/").replace(":", "\\:")
        video_filters.append(f"subtitles='{escaped_sub_path}'")
        
    vf_chain = ",".join(video_filters)
    
    # 2. Audio Pipeline & Command Construction
    cmd = [
        FFMPEG_PATH,
        "-y",
        "-ss", f"{start_time:.3f}",
        "-to", f"{end_time:.3f}",
        "-i", str(input_video)
    ]
    
    # If BGM is enabled, add it as second input
    has_bgm = bool(bgm_file_path and Path(bgm_file_path).exists())
    if has_bgm:
        cmd.extend([
            "-stream_loop", "-1",
            "-i", str(bgm_file_path)
        ])
        
    cmd.extend(["-vf", vf_chain])
    
    # Build Audio Filter
    if has_bgm:
        bgm_vol = max(0.01, min(0.5, bgm_volume))
        if normalize_audio:
            af_filter = f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[a_norm];[1:a]volume={bgm_vol}[a_bgm];[a_norm][a_bgm]amix=inputs=2:duration=first:dropout_transition=2"
        else:
            af_filter = f"[1:a]volume={bgm_vol}[a_bgm];[0:a][a_bgm]amix=inputs=2:duration=first:dropout_transition=2"
        cmd.extend(["-filter_complex", af_filter])
    else:
        if normalize_audio:
            cmd.extend(["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"])
            
    # Output encoding parameters (High quality, fast preset, standard compatibility)
    cmd.extend([
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "21",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-movflags", "+faststart",
        str(output_clip_path)
    ])
    
    run_command(cmd, timeout=300)
    return str(output_clip_path)
