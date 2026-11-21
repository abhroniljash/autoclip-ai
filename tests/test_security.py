from app.security import has_supported_video_signature


def test_accepts_mp4_signature():
    assert has_supported_video_signature(b"\x00\x00\x00\x18ftypisom")


def test_accepts_webm_and_matroska_signature():
    assert has_supported_video_signature(b"\x1a\x45\xdf\xa3" + b"\x00" * 8)


def test_rejects_unknown_or_short_signature():
    assert not has_supported_video_signature(b"")
    assert not has_supported_video_signature(b"not a video file")
