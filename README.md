# AutoClip AI – Intelligent Long-to-Short Video Repurposing Platform

> **One Video. Multiple Clips. Powered by AI.**  
> *Intelligent Analysis + Explainable Scoring + Automatic Editing + Professional Output.*

---

## 1. Overview

**AutoClip AI** is a video repurposing platform designed to transform long-form content (podcasts, interviews, webinars, tutorials, YouTube videos) into multiple engaging, vertical (9:16) short-form videos ready for TikTok, Instagram Reels, and YouTube Shorts.

Instead of basic linear trimming, AutoClip AI analyzes video narrative structure, evaluates virality potential across 8 weighted factors, intelligently reframes landscape footage around active speakers, generates animated karaoke-style subtitles, and generates a social media kit (titles, captions, hashtags, hooks) for each clip.

---

## 2. Core Application Workflow

```
Long Video Input (Upload / Authorized Source)
       │
       ▼
Audio Extraction & Speech Boundary Detection
       │
       ▼
Word-Level Transcription (Gemini / Whisper / Acoustic Segmenter)
       │
       ▼
AI Narrative Analysis & 8-Factor Virality Scoring
       │
       ▼
Intelligent Moment Selection (20–60s clips)
       │
       ▼
Computer Vision Framing (OpenCV Face & Motion Tracking / Split-Screen)
       │
       ▼
Animated Karaoke Subtitles (5 Styles: Bold Viral, Minimal, Podcast, Cinematic, Highlight)
       │
       ▼
Audio Normalization (EBU R128) & Royalty-Free BGM Mixing
       │
       ▼
Interactive Studio Preview & Timeline Trimmer
       │
       ▼
Export Center: Single 1080p MP4 or Complete ZIP Archive with SRTs & Social Kit
```

---

## 3. The 8-Factor Virality Scoring Model

Each clip candidate is evaluated on an objective 0 to 100 scale using the following weighted parameters:

| Evaluation Factor | Weight | Description |
| :--- | :---: | :--- |
| **Opening Hook Strength** | **20%** | Curiosity gap, question patterns, emotional intrigue in first 3–5 seconds. |
| **Emotional Impact & Curiosity** | **15%** | Empathy, humor, controversy, or surprising revelations. |
| **Information Value & Novelty** | **15%** | Actionable takeaways, counter-intuitive facts, or educational value. |
| **Context Completeness** | **15%** | Standalone narrative coherence without requiring external context. |
| **Shareability** | **10%** | Likelihood of viewers bookmarking or forwarding to friends. |
| **Content Pacing** | **10%** | Optimal conversational rhythm (~130–180 WPM), eliminating dead air. |
| **Audio Clarity** | **10%** | Background noise suppression and acoustic presence. |
| **Visual Engagement** | **5%** | Dynamic facial expressions, movement, and visual energy. |

### Potential Categories
- **High Potential (80 – 100)**: Prime candidate for immediate publishing.
- **Medium Potential (60 – 79)**: Good secondary clip; benefits from subtle manual trimming.
- **Low Potential (< 60)**: Not recommended for standalone short-form posting.

---

## 4. Web Application Pages

AutoClip AI provides a responsive, light-first modern web interface with optional dark mode:

1. **Landing Page (`#/`)**: Product introduction, interactive 16:9 to 9:16 workflow demonstration, feature cards, and pricing tiers.
2. **Dashboard (`#/dashboard`)**: Live counters (Total Projects, Videos Processed, Clips Generated) and recent project cards with progress bars and status badges.
3. **New Video Project (`#/projects/new`)**: Drag-and-drop video uploader, authorized YouTube source input with compliance notices, clip duration selector (20-40s, 30-60s, 60-90s, auto), target clip count, subtitle language selector (English, Bengali, Hindi), and style presets.
4. **AI Analysis Results (`#/projects/:id/analysis`)**: Video virality timeline map, detected moments grid, 0–100 potential scores with 8-factor breakdown progress bars, selection reasoning quotes, and opening hook callout boxes.
5. **Interactive Video Editor (`#/projects/:id/editor/:clipId`)**: 9:16 vertical smartphone preview player, start/end trimming sliders, crop mode selector (Auto Face Track, Center, Left Focus, Right Focus, Split-Screen), 5 subtitle preset switcher, audio normalization, BGM volume ducking, and one-click re-render.
6. **Export Center (`#/projects/:id/export`)**: Batch export all clips as a structured ZIP archive (including 1080p MP4s, SRT subtitle files, and social media text kits), individual clip downloads, and one-click copy buttons for suggested titles, Instagram captions, Shorts descriptions, and hashtags.

---

## 5. Technology Stack

- **Backend**: Python 3.13, FastAPI, Uvicorn, SQLAlchemy, SQLite
- **Video & Audio**: FFmpeg 8.0.1 64-bit (with `libass`, `libx264`, `loudnorm`), OpenCV 5.0 (facial saliency and motion tracking)
- **AI Intelligence**: Google Gemini API (`gemini-2.5-flash`), acoustic speech chunking, and heuristic evaluation engine
- **Frontend**: Single-Page Application (HTML5, Tailwind CSS, Lucide Icons, Vanilla ES Modules)
- **Subtitles**: Advanced SubStation Alpha (`.ass`) with karaoke keyword highlights and standard `.srt` generator

---

## 6. Quick Start Guide

### Step 1: Clone or Navigate to Project
```bash
cd D:\clip
```

### Step 2: Configure Environment (Optional)
Copy `.env.example` to `.env` and insert your Google Gemini API key if available:
```bash
cp .env.example .env
```
*(Note: AutoClip AI features an offline acoustic & heuristic analysis engine that operates out of the box even before an external API key is added!)*

### Step 3: Run the Application
```bash
python run.py
```
Open your browser to: **`http://localhost:8000`**

### Step 4: Run Automated Tests
```bash
python run_tests.py
```

---

## 7. Security and Authorized Media Policy
- AutoClip AI strictly adheres to platform terms: it checks authorized video streams and never bypasses DRM. If an authorized video stream is restricted by YouTube, the user is politely guided to upload their original video file directly.
- Secrets and API keys are read from environment variables and never exposed to the frontend client.
