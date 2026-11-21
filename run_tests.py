import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

print("==================================================")
print("  AutoClip AI – Automated Test Suite Execution   ")
print("==================================================")

passed = 0
failed = 0

def run_test(name, func):
    global passed, failed
    try:
        func()
        print(f"  [PASS] {name}")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        import traceback
        traceback.print_exc()
        failed += 1

# 1. Virality Scoring Tests
from tests.test_scoring import (
    test_scoring_weights_sum_to_one,
    test_calculate_weighted_score_perfect,
    test_calculate_weighted_score_minimum,
    test_potential_category_boundaries,
    test_heuristic_evaluation
)

print("\n--- 1. Virality Scoring Engine (8-Factor Model) ---")
run_test("Weights strictly sum to 100%", test_scoring_weights_sum_to_one)
run_test("Perfect factors yield 100 score", test_calculate_weighted_score_perfect)
run_test("Zero factors yield 0 score", test_calculate_weighted_score_minimum)
run_test("Category threshold boundaries (High >=80, Med 60-79, Low <60)", test_potential_category_boundaries)
run_test("Heuristic 8-factor evaluation & breakdown", test_heuristic_evaluation)

# 2. Video Pipeline Tests
from tests.test_video import test_video_pipeline_end_to_end

print("\n--- 2. FFmpeg 8.0.1 Video & Subtitle Processing Pipeline ---")
with tempfile.TemporaryDirectory() as tmp_dir:
    run_test("End-to-End 9:16 Video Cutting, Subtitling & Encoding", lambda: test_video_pipeline_end_to_end(Path(tmp_dir)))

# 3. Direct API Handlers Tests
from tests.test_api_direct import test_api_handlers_direct

print("\n--- 3. FastAPI Service Handlers & Database Persistence ---")
run_test("FastAPI Endpoints, Subtitle Presets & Dashboard Stats", test_api_handlers_direct)

from tests.test_security import (
    test_accepts_mp4_signature,
    test_accepts_webm_and_matroska_signature,
    test_rejects_unknown_or_short_signature,
)

print("\n--- 4. Upload Security Checks ---")
run_test("Accept supported MP4 container signature", test_accepts_mp4_signature)
run_test("Accept WebM/Matroska container signature", test_accepts_webm_and_matroska_signature)
run_test("Reject unknown and truncated container signatures", test_rejects_unknown_or_short_signature)

from tests.test_auth import (
    test_password_hash_round_trip,
    test_password_minimum_length,
    test_jwt_token_contains_required_claims,
)

print("\n--- 5. Authentication Checks ---")
run_test("Password hashing and verification", test_password_hash_round_trip)
run_test("Reject short passwords", test_password_minimum_length)
run_test("JWT token claims and signature", test_jwt_token_contains_required_claims)

print("\n==================================================")
print(f"  RESULTS: {passed} PASSED, {failed} FAILED")
print("==================================================")

if failed > 0:
    sys.exit(1)
