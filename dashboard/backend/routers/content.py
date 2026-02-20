"""Content endpoints — reel metadata and video serving."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import VIDEO_OUTPUT_DIR, PROJECT_ROOT
from services.log_reader import read_all_runs

router = APIRouter(prefix="/api/content", tags=["content"])


@router.get("/reels")
def get_reels(persona: str | None = None, video_type: str | None = None):
    """Get all reels with metadata, optionally filtered."""
    runs = read_all_runs()
    # Only include runs that produced a reel
    reels = [r for r in runs if r.reel_path]

    if persona:
        reels = [r for r in reels if r.persona == persona]
    if video_type:
        reels = [r for r in reels if r.video_type == video_type]

    # Sort newest first
    reels.sort(key=lambda r: r.timestamp, reverse=True)
    return reels


@router.get("/video/{filename}")
def serve_video(filename: str):
    """Serve a video file from video_output/."""
    path = VIDEO_OUTPUT_DIR / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(path, media_type="video/mp4")


@router.get("/video-by-path")
def serve_video_by_path(path: str):
    """Serve a video by its full reel_path (normalized)."""
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Video not found")
    # Security: ensure the file is within project root
    try:
        file_path.resolve().relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    return FileResponse(file_path, media_type="video/mp4")
