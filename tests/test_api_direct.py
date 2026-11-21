import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db
from app.models import Project, Clip
from app.routers.projects import get_dashboard_stats, list_projects
from app.routers.clips import list_bgm_tracks, list_subtitle_presets
from app.schemas import ProjectCreateURL

def test_api_handlers_direct():
    init_db()
    db = SessionLocal()
    try:
        # 1. Test BGM tracks
        tracks = list_bgm_tracks()
        assert len(tracks) >= 3
        assert tracks[0]["id"] == "lofi_chill"
        print("  [PASS] list_bgm_tracks()")

        # 2. Test Subtitle Presets
        presets = list_subtitle_presets()
        assert "bold_viral" in presets
        assert "clean_minimal" in presets
        assert "podcast" in presets
        assert "cinematic" in presets
        assert "highlight_keyword" in presets
        print("  [PASS] list_subtitle_presets() (all 5 presets present)")

        # 3. Test Dashboard Stats handler
        stats = get_dashboard_stats(db=db)
        assert "total_projects" in stats
        assert "total_videos_processed" in stats
        assert "total_clips_generated" in stats
        assert "recent_projects" in stats
        print("  [PASS] get_dashboard_stats()")

        # 4. Test List Projects handler
        projects = list_projects(db=db)
        assert isinstance(projects, list)
        print("  [PASS] list_projects()")

    finally:
        db.close()

if __name__ == "__main__":
    test_api_handlers_direct()
    print("\nALL DIRECT API HANDLER TESTS PASSED!")
