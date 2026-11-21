# AutoClip AI – Intelligent Long-to-Short Video Repurposing Platform

> **One Video. Multiple Clips. Powered by AI.**  
> *Intelligent Analysis + Explainable Scoring + Automatic Editing + Professional Output.*

---

## 1. Overview

**AutoClip AI** is an intelligent video repurposing platform designed to transform long-form content (podcasts, interviews, webinars, tutorials, YouTube videos) into multiple engaging, vertical (9:16) short-form videos ready for TikTok, Instagram Reels, and YouTube Shorts.

Instead of basic linear trimming, AutoClip AI analyzes video narrative structure, evaluates virality potential across 8 weighted factors, intelligently reframes landscape footage around active speakers, generates animated karaoke-style subtitles, and generates a complete social media kit (titles, captions, hashtags, hooks) for each clip.

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

## 5. Technology Stack & Dependencies

### Core Python Dependencies (Python 3.13 Compatible)
All dependencies are enumerated in `requirements.txt`:
- **`fastapi>=0.115.0`**: Modern, asynchronous web API framework.
- **`uvicorn[standard]>=0.30.0`**: High-performance ASGI web server.
- **`python-multipart>=0.0.12`**: Multipart form data & file streaming support for video uploads.
- **`SQLAlchemy>=2.0.30`**: ORM and database engine (SQLite by default, PostgreSQL ready).
- **`pydantic>=2.8.0`**: Type validation and structured schemas.
- **`httpx>=0.27.0`**: Async HTTP client for multimodal AI API communication.
- **`numpy>=2.1.0`**: Numerical computation and audio/frame array operations.
- **`opencv-python>=4.10.0`**: Computer vision for facial saliency, motion tracking, and 9:16 reframing.
- **`yt-dlp>=2024.10.0`**: Authorized video stream analysis and metadata retrieval.

### Optional AI Integrations
AutoClip AI works out-of-the-box with its built-in acoustic speech chunker and heuristic scoring engine. If you wish to extend it with additional external models:
- **`google-genai>=0.1.0`**: Google Gemini API official Python SDK (AutoClip AI already natively supports direct REST calls to Gemini 2.5 Flash via `httpx`).
- **`openai>=1.50.0`**: Optional cloud Whisper speech-to-text API fallback.
- **`faster-whisper>=1.0.0`**: Optional local high-speed speech recognition using CTranslate2.

### System Requirements: FFmpeg & FFprobe
AutoClip AI relies on **FFmpeg** and **FFprobe** (version 6.0+ or 8.0+) compiled with `libass` (for subtitle burning) and `libx264` (for H.264 video encoding).

#### Windows Installation Methods:
- **Method 1: Using Windows Package Manager (Winget - Recommended)**
  ```powershell
  winget install Gyan.FFmpeg
  ```
- **Method 2: Using Chocolatey**
  ```powershell
  choco install ffmpeg
  ```
- **Method 3: Manual Download**
  1. Download the full release build from [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/).
  2. Extract to `C:\ffmpeg`.
  3. Add `C:\ffmpeg\bin` to your Windows System `PATH`.

#### Auto-Discovery Logic:
AutoClip AI automatically checks:
1. `FFMPEG_PATH` and `FFPROBE_PATH` environment variables (set in `.env`).
2. System `PATH`.
3. Standard Windows installation directories (including `C:\Program Files\kdenlive\bin\`, `C:\Program Files (x86)\YouTube Playlist Downloader\`, and `C:\ffmpeg\bin\`).

---

## 6. Windows Setup & Quick Start Guide

### Step 1: Navigate to Project Directory
```powershell
cd D:\clip
```

### Step 2: Create and Activate a Fresh Virtual Environment
```powershell
# Create Python 3.13 virtual environment
python -m venv .venv

# Activate on Windows PowerShell
.\.venv\Scripts\Activate.ps1

# (If PowerShell script execution is restricted, run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser)
```

### Step 3: Install Core Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy the template and configure your keys:
```powershell
Copy-Item .env.example .env
```
Edit `.env` to add your Google Gemini API key:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
```
*(AutoClip AI also operates completely offline with its algorithmic analysis engine if no API key is provided).*

### Step 5: Verify the Installation
Run the automated test suite to verify scoring, FFmpeg video processing, and API handlers:
```powershell
python run_tests.py
```
Expected output:
```text
==================================================
  AutoClip AI – Automated Test Suite Execution   
==================================================
--- 1. Virality Scoring Engine (8-Factor Model) ---
  [PASS] Weights strictly sum to 100%
  [PASS] Perfect factors yield 100 score
  [PASS] Zero factors yield 0 score
  [PASS] Category threshold boundaries (High >=80, Med 60-79, Low <60)
  [PASS] Heuristic 8-factor evaluation & breakdown
--- 2. FFmpeg 8.0.1 Video & Subtitle Processing Pipeline ---
  [PASS] End-to-End 9:16 Video Cutting, Subtitling & Encoding
--- 3. FastAPI Service Handlers & Database Persistence ---
  [PASS] list_bgm_tracks()
  [PASS] list_subtitle_presets() (all 5 presets present)
  [PASS] get_dashboard_stats()
  [PASS] list_projects()
  [PASS] FastAPI Endpoints, Subtitle Presets & Dashboard Stats
==================================================
  RESULTS: 7 PASSED, 0 FAILED
==================================================
```

### Step 6: Launch AutoClip AI
```powershell
python run.py
```
Open your browser and navigate to: **`http://localhost:8000`**

---

## 7. Security and Authorized Media Policy
- AutoClip AI strictly adheres to platform terms: it checks authorized video streams and never bypasses DRM. If an authorized video stream is restricted by YouTube, the user is politely guided to upload their original video file directly.
- Secrets and API keys are read from environment variables and never exposed to the frontend client.
- Local databases (`*.db`) and `.env` credentials are automatically excluded by `.gitignore`.
