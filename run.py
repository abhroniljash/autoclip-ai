#!/usr/bin/env python3
"""
AutoClip AI – Long-to-Short Video Repurposing Platform
Entrypoint script to start the web application and backend API.
"""

import sys
import uvicorn
from pathlib import Path
from app.config import FFMPEG_PATH, FFPROBE_PATH, BASE_DIR

def main():
    print("================================================================")
    print("                     AUTOCLIP AI                                ")
    print("       One Video. Multiple Clips. Powered by AI.                ")
    print("================================================================")
    print(f"  • Base Directory:   {BASE_DIR}")
    print(f"  • FFmpeg Binary:    {FFMPEG_PATH}")
    print(f"  • FFprobe Binary:   {FFPROBE_PATH}")
    print("----------------------------------------------------------------")
    print("  Starting AutoClip AI web server on: http://localhost:8000")
    print("  Open your browser to http://localhost:8000 to access the platform.")
    print("================================================================")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

if __name__ == "__main__":
    main()
