from app.services.ai_scoring import (
    calculate_weighted_score,
    get_potential_category,
    evaluate_clip_heuristically
)
from app.config import SCORING_WEIGHTS

def test_scoring_weights_sum_to_one():
    """Verify that the 8 factor weights strictly sum to 1.0 (100%)."""
    total_weight = sum(SCORING_WEIGHTS.values())
    assert abs(total_weight - 1.0) < 1e-6

def test_calculate_weighted_score_perfect():
    """Verify 100 on all factors yields 100."""
    perfect_factors = {factor: 100.0 for factor in SCORING_WEIGHTS}
    score = calculate_weighted_score(perfect_factors)
    assert score == 100.0

def test_calculate_weighted_score_minimum():
    """Verify 0 on all factors yields 0."""
    zero_factors = {factor: 0.0 for factor in SCORING_WEIGHTS}
    score = calculate_weighted_score(zero_factors)
    assert score == 0.0

def test_potential_category_boundaries():
    """Verify High (>=80), Medium (60-79), Low (<60) classification."""
    assert get_potential_category(95.0) == "High"
    assert get_potential_category(80.0) == "High"
    assert get_potential_category(79.9) == "Medium"
    assert get_potential_category(60.0) == "Medium"
    assert get_potential_category(59.9) == "Low"
    assert get_potential_category(10.0) == "Low"

def test_heuristic_evaluation():
    """Verify heuristic evaluation generates all 8 factors and valid ranges."""
    sample_text = "Here is the single biggest mistake creators make when publishing shorts. Notice how retention drops."
    eval_result = evaluate_clip_heuristically(
        text_content=sample_text,
        duration=35.0,
        start_time=10.0,
        end_time=45.0,
        total_video_duration=120.0
    )

    assert "potential_score" in eval_result
    assert 0 <= eval_result["potential_score"] <= 100
    assert eval_result["potential_category"] in ["High", "Medium", "Low"]
    
    breakdown = eval_result["scoring_breakdown"]
    assert len(breakdown) == 8
    for factor in SCORING_WEIGHTS:
        assert factor in breakdown
        assert 0 <= breakdown[factor] <= 100
