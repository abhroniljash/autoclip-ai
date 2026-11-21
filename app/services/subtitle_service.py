import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.config import SUBTITLE_PRESETS

# High-impact keywords for dynamic highlighting
VIRAL_KEYWORDS = {
    "money", "rich", "millionaire", "billionaire", "dollar", "wealth", "secret", "hack",
    "mistake", "crazy", "insane", "truth", "never", "always", "rule", "power", "win",
    "fail", "loss", "fast", "easy", "danger", "shocking", "ai", "future", "magic", "best"
}

KEYWORD_EMOJIS = {
    "money": "💰",
    "rich": "🤑",
    "dollar": "💵",
    "fire": "🔥",
    "secret": "🤫",
    "mind": "🧠",
    "crazy": "🤯",
    "rocket": "🚀",
    "danger": "⚠️",
    "win": "🏆",
    "target": "🎯",
    "love": "❤️"
}

def seconds_to_ass_time(seconds: float) -> str:
    """Format seconds into ASS timestamp: H:MM:SS.cs"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis == 100:
        secs += 1
        centis = 0
    return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"

def seconds_to_srt_time(seconds: float) -> str:
    """Format seconds into SRT timestamp: HH:MM:SS,mmm"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis == 1000:
        secs += 1
        millis = 0
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

def generate_ass_subtitles(
    transcript_segments: List[Dict[str, Any]],
    output_ass_path: str,
    style_key: str = "bold_viral",
    clip_start_time: float = 0.0,
    clip_end_time: float = 60.0
) -> str:
    """
    Generate an ASS subtitle file configured for 1080x1920 vertical video,
    with custom styles, positioning, and highlighted keyword tags.
    """
    preset = SUBTITLE_PRESETS.get(style_key, SUBTITLE_PRESETS["bold_viral"])
    
    font_name = preset.get("font_name", "Arial")
    font_size = preset.get("font_size", 44)
    primary_col = preset.get("primary_color", "&H00FFFFFF")
    secondary_col = preset.get("secondary_color", "&H0000FFFF")
    outline_col = preset.get("outline_color", "&H00000000")
    outline_width = preset.get("outline_width", 3.0)
    shadow = preset.get("shadow", 1.5)
    alignment = preset.get("alignment", 2)
    margin_v = preset.get("margin_v", 100)
    uppercase = preset.get("uppercase", False)

    # ASS Header
    header = f"""[Script Info]
Title: AutoClip AI Dynamic Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_col},{secondary_col},{outline_col},&H80000000,-1,0,0,0,100,100,0,0,1,{outline_width},{shadow},{alignment},60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []
    
    for seg in transcript_segments:
        seg_start = seg.get("start", 0.0)
        seg_end = seg.get("end", seg_start + 2.0)
        
        # Only include segments overlapping with the clip interval
        if seg_end < clip_start_time or seg_start > clip_end_time:
            continue
            
        # Adjust timestamps relative to clip start
        rel_start = max(0.0, seg_start - clip_start_time)
        rel_end = max(rel_start + 0.3, seg_end - clip_start_time)
        
        ass_start = seconds_to_ass_time(rel_start)
        ass_end = seconds_to_ass_time(rel_end)
        
        text = seg.get("text", "").strip()
        if not text:
            continue
            
        if uppercase:
            text = text.upper()

        words = text.split()
        styled_words = []
        for w in words:
            clean_w = re.sub(r"[^\w\s]", "", w).lower()
            if clean_w in VIRAL_KEYWORDS:
                # Add highlight tag and emoji if available
                emoji = KEYWORD_EMOJIS.get(clean_w, "")
                styled_words.append(f"{{\\c{secondary_col}&\\b1}}{w}{emoji}{{\\c{primary_col}&\\b0}}")
            else:
                styled_words.append(w)
                
        final_line = " ".join(styled_words)
        events.append(f"Dialogue: 0,{ass_start},{ass_end},Default,,0,0,0,,{final_line}")

    out_file = Path(output_ass_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return str(output_ass_path)

def generate_srt_subtitles(
    transcript_segments: List[Dict[str, Any]],
    output_srt_path: str,
    clip_start_time: float = 0.0,
    clip_end_time: float = 60.0
) -> str:
    """Generate standard .srt subtitle file for export and download."""
    lines = []
    index = 1
    
    for seg in transcript_segments:
        seg_start = seg.get("start", 0.0)
        seg_end = seg.get("end", seg_start + 2.0)
        
        if seg_end < clip_start_time or seg_start > clip_end_time:
            continue
            
        rel_start = max(0.0, seg_start - clip_start_time)
        rel_end = max(rel_start + 0.3, seg_end - clip_start_time)
        
        text = seg.get("text", "").strip()
        if not text:
            continue
            
        lines.append(str(index))
        lines.append(f"{seconds_to_srt_time(rel_start)} --> {seconds_to_srt_time(rel_end)}")
        lines.append(text)
        lines.append("")
        index += 1
        
    out_file = Path(output_srt_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n".join(lines), encoding="utf-8")
    return str(output_srt_path)
