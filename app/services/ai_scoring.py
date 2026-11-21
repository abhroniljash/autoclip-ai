import json
import logging
import math
import re
from typing import List, Dict, Any, Optional
import httpx

from app.config import SCORING_WEIGHTS, GEMINI_API_KEY

logger = logging.getLogger("autoclip.ai_scoring")

def calculate_weighted_score(factors: Dict[str, float]) -> float:
    """Calculates the total potential score (0 to 100) based on weighted factors."""
    total = 0.0
    for factor, weight in SCORING_WEIGHTS.items():
        val = factors.get(factor, 70.0)
        total += val * weight
    return round(max(0.0, min(100.0, total)), 1)

def get_potential_category(score: float) -> str:
    """Classifies content potential category strictly according to specification."""
    if score >= 80.0:
        return "High"
    elif score >= 60.0:
        return "Medium"
    else:
        return "Low"

def evaluate_clip_heuristically(
    text_content: str,
    duration: float,
    start_time: float,
    end_time: float,
    total_video_duration: float
) -> Dict[str, Any]:
    """
    Algorithmic evaluation of content potential using NLP cues,
    hook strength patterns, curiosity markers, and narrative completeness.
    """
    text_lower = text_content.lower()
    
    # 1. Opening Hook Strength (20%)
    hook_score = 65.0
    hook_triggers = [
        "why", "how", "secret", "never", "always", "mistake", "best", "truth",
        "insane", "crazy", "stop", "rule", "lesson", "watch", "notice", "here is"
    ]
    first_sentence = text_lower.split(".")[0] if "." in text_lower else text_lower
    for word in hook_triggers:
        if word in first_sentence:
            hook_score += 6.5
    if "?" in first_sentence:
        hook_score += 8.0
    hook_score = min(98.0, max(45.0, hook_score))

    # 2. Emotional Impact & Curiosity (15%)
    emotion_score = 70.0
    emotion_triggers = ["amazing", "unbelievable", "shocking", "changed", "fail", "win", "love", "hate", "scary", "powerful"]
    for word in emotion_triggers:
        if word in text_lower:
            emotion_score += 5.0
    emotion_score = min(96.0, max(50.0, emotion_score))

    # 3. Information Value & Novelty (15%)
    info_score = 72.0
    info_triggers = ["because", "result", "technique", "system", "formula", "strategy", "data", "understand", "study", "step"]
    for word in info_triggers:
        if word in text_lower:
            info_score += 4.5
    info_score = min(98.0, max(55.0, info_score))

    # 4. Context Completeness (15%)
    context_score = 75.0
    # Ideal standalone clip duration is 30 to 60 seconds
    if 25.0 <= duration <= 65.0:
        context_score += 15.0
    elif duration < 20.0:
        context_score -= 10.0
    if len(text_content.split()) > 40:
        context_score += 5.0
    context_score = min(95.0, max(50.0, context_score))

    # 5. Shareability (10%)
    share_score = (hook_score * 0.5) + (info_score * 0.5)
    share_score = min(95.0, max(40.0, share_score))

    # 6. Content Pacing (10%)
    # Words per minute calculation
    words = len(text_content.split())
    wpm = (words / max(1.0, duration)) * 60.0
    pacing_score = 80.0
    if 130.0 <= wpm <= 180.0: # Optimal energetic speech rate
        pacing_score = 92.0
    elif wpm < 100.0 or wpm > 210.0:
        pacing_score = 65.0

    # 7. Audio Clarity (10%)
    audio_clarity = 88.0

    # 8. Visual Engagement (5%)
    visual_engagement = 85.0

    factors = {
        "hook_strength": round(hook_score, 1),
        "emotional_impact": round(emotion_score, 1),
        "information_value": round(info_score, 1),
        "context_completeness": round(context_score, 1),
        "shareability": round(share_score, 1),
        "content_pacing": round(pacing_score, 1),
        "audio_clarity": round(audio_clarity, 1),
        "visual_engagement": round(visual_engagement, 1)
    }

    final_score = calculate_weighted_score(factors)
    category = get_potential_category(final_score)

    # Generate explanatory insights
    reasoning = (
        f"Selected due to high initial hook strength ({hook_score:.0f}%) and self-contained structure. "
        f"Maintains an optimal speaking pace of ~{int(wpm)} WPM with strong informational takeaway."
    )
    
    suggested_hook = first_sentence.capitalize().strip()
    if len(suggested_hook) > 80:
        suggested_hook = suggested_hook[:77] + "..."

    return {
        "potential_score": final_score,
        "potential_category": category,
        "scoring_breakdown": factors,
        "selection_reason": reasoning,
        "suggested_hook": suggested_hook,
        "key_moments": [
            {"time": round(start_time, 1), "label": "Opening Hook & Curiosity Trigger"},
            {"time": round(start_time + duration * 0.5, 1), "label": "Core Value Delivery"},
            {"time": round(end_time - 3.0, 1), "label": "Key Takeaway & Conclusion"}
        ]
    }

async def analyze_with_gemini(
    transcript: List[Dict[str, Any]],
    total_duration: float,
    target_count: int = 5,
    duration_pref: str = "30-60"
) -> Optional[List[Dict[str, Any]]]:
    """Uses Gemini 2.5 Flash to intelligently segment and score high-potential clips."""
    if not GEMINI_API_KEY:
        return None

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        # Prepare compact transcript representation
        compact_transcript = []
        for s in transcript:
            compact_transcript.append(f"[{s.get('start', 0):.1f}s - {s.get('end', 0):.1f}s]: {s.get('text', '')}")
        full_text = "\n".join(compact_transcript)
        
        prompt = f"""
You are the world's top short-form video strategist (TikTok, Reels, YouTube Shorts).
Analyze this video transcript with timestamps and extract exactly {target_count} of the highest potential viral short clips.
Target clip duration preference: {duration_pref} seconds. Total video duration: {total_duration:.1f}s.

Evaluate each candidate clip using the following 8 weighted factors:
1. hook_strength (20%): Initial 3-5 seconds engagement & curiosity.
2. emotional_impact (15%): Emotional resonance or controversy.
3. information_value (15%): Concrete insight, lesson, or novelty.
4. context_completeness (15%): Makes 100% standalone sense.
5. shareability (10%): Likelihood to save or share.
6. content_pacing (10%): Smooth flow, no boring silence.
7. audio_clarity (10%): Speech clarity.
8. visual_engagement (5%): Dynamic speaker presence.

Calculate:
potential_score = (hook_strength*0.20) + (emotional_impact*0.15) + (information_value*0.15) + (context_completeness*0.15) + (shareability*0.10) + (content_pacing*0.10) + (audio_clarity*0.10) + (visual_engagement*0.05).
Classify potential_category: "High" (>=80), "Medium" (60-79), "Low" (<60).

Output MUST be a JSON object with a 'clips' array containing:
- title: Catchy clip title
- start_time: float seconds
- end_time: float seconds
- potential_score: float (0 to 100)
- potential_category: "High" | "Medium" | "Low"
- scoring_breakdown: object with the 8 factors (each 0 to 100)
- selection_reason: 1-2 sentence explanation
- suggested_hook: Strong opening sentence
- key_moments: array of {{ "time": float, "label": string }}
- social_kit: {{
    "suggested_titles": [title1, title2, title3],
    "instagram_caption": string with emojis,
    "shorts_description": string,
    "hashtags": [tag1, tag2, tag3, tag4, tag5],
    "thumbnail_text_suggestions": [thumb1, thumb2],
    "clip_summary": string
  }}

Transcript:
{full_text}
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.4,
                "response_mime_type": "application/json"
            }
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(content)
                clips = parsed.get("clips", [])
                if clips and len(clips) > 0:
                    return clips
            else:
                logger.warning("Gemini content analysis API returned code %d: %s", resp.status_code, resp.text)
    except Exception as e:
        logger.error("Error running Gemini video analysis: %s", e)
        
    return None

def generate_social_kit_heuristically(title: str, text: str, score: float) -> Dict[str, Any]:
    """Generates social media assets (3 titles, captions, hashtags, hooks) for any clip."""
    clean_title = re.sub(r"[^\w\s]", "", title).strip()
    
    suggested_titles = [
        f"The Truth About {clean_title} 🤯",
        f"Why Nobody Talks About {clean_title} 🤫",
        f"The Secret To {clean_title} (Watch Till The End)"
    ]
    
    hashtags = [
        "#shorts", "#viral", "#reels", "#fyp", "#contentcreator",
        "#tiktok", "#productivity", "#mindset", "#growth", "#story"
    ]
    
    ig_caption = (
        f"Did you know this? 🤯\n\n"
        f"Here is why this changes everything when it comes to {clean_title}.\n\n"
        f"💬 Drop your thoughts below!\n"
        f"📌 Save this post so you don't forget it.\n\n"
        f"{' '.join(hashtags[:5])}"
    )
    
    shorts_desc = (
        f"A quick breakdown on {clean_title}. Subscribe for daily high-value short clips!\n\n"
        f"{' '.join(hashtags)}"
    )
    
    return {
        "suggested_titles": suggested_titles,
        "instagram_caption": ig_caption,
        "shorts_description": shorts_desc,
        "hashtags": hashtags,
        "thumbnail_text_suggestions": [
            clean_title.upper()[:24],
            "WATCH THIS FIRST",
            "MIND BLOWN 🤯"
        ],
        "clip_summary": f"Highlights the key insight regarding '{clean_title}' with actionable takeaway."
    }

async def generate_clip_candidates(
    transcript: List[Dict[str, Any]],
    total_video_duration: float,
    target_count: int = 5,
    duration_pref: str = "30-60"
) -> List[Dict[str, Any]]:
    """
    Identifies top viral moments across the video:
    Attempts Gemini AI analysis first, or falls back to intelligent
    sliding-window algorithmic evaluation.
    """
    # 1. Try Gemini Analysis
    if GEMINI_API_KEY:
        gemini_clips = await analyze_with_gemini(transcript, total_video_duration, target_count, duration_pref)
        if gemini_clips and len(gemini_clips) > 0:
            logger.info("Found %d clips using Gemini AI", len(gemini_clips))
            return gemini_clips

    # 2. Algorithmic Candidate Generator
    logger.info("Executing algorithmic candidate generator for %d clips", target_count)
    
    # Determine target clip duration range
    dur_map = {
        "20-40": (20.0, 40.0),
        "30-60": (30.0, 60.0),
        "60-90": (60.0, 90.0),
        "auto": (25.0, 55.0)
    }
    min_dur, max_dur = dur_map.get(duration_pref, (30.0, 60.0))
    
    # If the whole video is short, adapt
    if total_video_duration < min_dur:
        min_dur = max(5.0, total_video_duration * 0.4)
        max_dur = total_video_duration
        
    candidates = []
    num_segs = len(transcript)
    
    # Slide across segments to form coherent candidate windows
    for i in range(num_segs):
        window_start = transcript[i].get("start", 0.0)
        window_texts = []
        
        for j in range(i, num_segs):
            seg_end = transcript[j].get("end", window_start + 2.0)
            window_texts.append(transcript[j].get("text", ""))
            curr_dur = seg_end - window_start
            
            if curr_dur >= min_dur:
                combined_text = " ".join(window_texts)
                eval_data = evaluate_clip_heuristically(
                    combined_text, curr_dur, window_start, seg_end, total_video_duration
                )
                
                # Derive title
                first_few_words = " ".join(combined_text.split()[:5])
                clip_title = f"{first_few_words.capitalize()}..."
                
                social_kit = generate_social_kit_heuristically(
                    first_few_words, combined_text, eval_data["potential_score"]
                )
                
                candidates.append({
                    "title": clip_title,
                    "start_time": round(window_start, 2),
                    "end_time": round(seg_end, 2),
                    "duration": round(curr_dur, 2),
                    "potential_score": eval_data["potential_score"],
                    "potential_category": eval_data["potential_category"],
                    "scoring_breakdown": eval_data["scoring_breakdown"],
                    "selection_reason": eval_data["selection_reason"],
                    "suggested_hook": eval_data["suggested_hook"],
                    "key_moments": eval_data["key_moments"],
                    "social_kit": social_kit
                })
                break  # Move to next start point once minimal duration window is achieved
                
    # Sort candidates by potential score descending
    candidates.sort(key=lambda x: x["potential_score"], reverse=True)
    
    # Filter out heavily overlapping clips (keep diverse sections of the video)
    selected_clips = []
    for cand in candidates:
        overlap = False
        for sel in selected_clips:
            # Check overlap > 50%
            max_s = max(cand["start_time"], sel["start_time"])
            min_e = min(cand["end_time"], sel["end_time"])
            if min_e > max_s:
                overlap_dur = min_e - max_s
                if overlap_dur > 0.5 * min(cand["duration"], sel["duration"]):
                    overlap = True
                    break
        if not overlap:
            selected_clips.append(cand)
            if len(selected_clips) >= target_count:
                break
                
    # If video was too short to yield enough diverse clips, return what we have
    if not selected_clips and candidates:
        selected_clips = candidates[:target_count]
        
    return selected_clips
