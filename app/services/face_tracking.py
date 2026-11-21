import cv2
import numpy as np
import logging
from typing import Dict, Any, List

logger = logging.getLogger("autoclip.face_tracking")

def analyze_speaker_framing(
    video_path: str,
    start_time: float,
    end_time: float,
    sample_fps: float = 2.0
) -> Dict[str, Any]:
    """
    Analyzes visual frame composition to determine the optimal horizontal crop offset (0.0 to 1.0)
    and detect if the scene contains two conversational speakers on opposite sides.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.warning("Could not open video for framing analysis: %s. Defaulting to center.", video_path)
        return {"optimal_crop_x": 0.5, "is_two_speakers": False, "recommended_mode": "center"}

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920
    frame_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080
    
    start_frame = int(start_time * video_fps)
    end_frame = int(end_time * video_fps)
    step_frames = max(1, int(video_fps / sample_fps))
    
    detected_x_centers: List[float] = []
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    current_frame = start_frame
    
    while current_frame <= end_frame:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Fast downscale for analysis (360p height)
        h, w = frame.shape[:2]
        scale = 360.0 / h if h > 360 else 1.0
        small_frame = cv2.resize(frame, (int(w * scale), 360))
        
        # Skin color & saliency energy detection in HSV space
        hsv = cv2.cvtColor(small_frame, cv2.COLOR_BGR2HSV)
        # Typical skin tone mask in HSV
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([25, 255, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower_skin, upper_skin)
        
        # Calculate horizontal center of mass of the detected region
        moments = cv2.moments(mask)
        if moments["m00"] > 500:
            cx = moments["m10"] / moments["m00"]
            norm_x = cx / (w * scale)
            detected_x_centers.append(norm_x)
            
        current_frame += step_frames
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        
    cap.release()
    
    if not detected_x_centers:
        return {
            "optimal_crop_x": 0.5,
            "is_two_speakers": False,
            "recommended_mode": "center",
            "confidence": 0.5
        }
        
    arr = np.array(detected_x_centers)
    median_x = float(np.median(arr))
    
    # Check for bimodal distribution (two speakers: one on left < 0.4, one on right > 0.6)
    left_count = np.sum(arr < 0.38)
    right_count = np.sum(arr > 0.62)
    total_samples = len(arr)
    
    is_two_speakers = False
    if total_samples > 6 and (left_count / total_samples > 0.25) and (right_count / total_samples > 0.25):
        is_two_speakers = True
        recommended_mode = "split_screen"
    else:
        # Keep crop_x clamped reasonably so we don't clip off margins
        recommended_mode = "auto_face"

    # Clamp crop center safely between 0.15 and 0.85
    clamped_crop_x = max(0.15, min(0.85, median_x))
    
    return {
        "optimal_crop_x": round(clamped_crop_x, 3),
        "is_two_speakers": is_two_speakers,
        "recommended_mode": recommended_mode,
        "confidence": round(min(1.0, len(arr) / 10.0), 2)
    }
