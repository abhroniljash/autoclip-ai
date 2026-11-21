import subprocess
from pathlib import Path
from app.config import FFMPEG_PATH, STORAGE_DIR
from app.services.video_service import probe_video, extract_audio, render_clip
from app.services.subtitle_service import generate_ass_subtitles, generate_srt_subtitles

def test_video_pipeline_end_to_end(tmp_path):
    """Generates synthetic test video, probes it, extracts audio, builds subtitles, and renders 9:16 clip."""
    test_video = tmp_path / "synthetic_test.mp4"
    test_audio = tmp_path / "synthetic_audio.wav"
    test_ass = tmp_path / "test.ass"
    test_srt = tmp_path / "test.srt"
    test_916_clip = tmp_path / "output_916.mp4"

    # 1. Create a 3-second 16:9 video with tone using FFmpeg
    cmd = [
        FFMPEG_PATH,
        "-y",
        "-f", "lavfi", "-i", "testsrc=duration=3:size=1280x720:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-c:v", "libx264", "-c:a", "aac",
        str(test_video)
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert res.returncode == 0
    assert test_video.exists()

    # 2. Probe video
    info = probe_video(str(test_video))
    assert info["duration"] > 2.5
    assert info["width"] == 1280
    assert info["height"] == 720
    assert info["fps"] == 30.0

    # 3. Extract audio
    extract_audio(str(test_video), str(test_audio))
    assert test_audio.exists()
    assert test_audio.stat().st_size > 1000

    # 4. Generate Subtitles
    sample_segments = [
        {"start": 0.5, "end": 2.5, "text": "Testing AutoClip AI intelligent video repurposing."}
    ]
    generate_ass_subtitles(sample_segments, str(test_ass), style_key="bold_viral", clip_start_time=0.0, clip_end_time=3.0)
    assert test_ass.exists()
    assert "[Script Info]" in test_ass.read_text(encoding="utf-8")

    generate_srt_subtitles(sample_segments, str(test_srt), clip_start_time=0.0, clip_end_time=3.0)
    assert test_srt.exists()
    assert "-->" in test_srt.read_text(encoding="utf-8")

    # 5. Render 9:16 vertical clip
    render_clip(
        input_video=str(test_video),
        output_clip_path=str(test_916_clip),
        start_time=0.0,
        end_time=2.5,
        crop_mode="center",
        crop_x_offset=0.5,
        subtitle_file_path=str(test_ass),
        target_width=720,
        target_height=1280
    )
    assert test_916_clip.exists()

    # Probe 9:16 rendered output
    rendered_info = probe_video(str(test_916_clip))
    assert rendered_info["width"] == 720
    assert rendered_info["height"] == 1280
    assert rendered_info["duration"] > 2.0
