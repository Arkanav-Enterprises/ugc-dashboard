"""Video stitcher endpoints — upload, poll, download."""

import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from config import VIDEO_OUTPUT_DIR
from services.video_stitcher import get_stitch_job, start_stitch_job

router = APIRouter(prefix="/api/stitcher", tags=["stitcher"])

MAX_SCENES = 10


@router.post("/stitch")
async def stitch(
    files: list[UploadFile] = File(...),
    scenes_json: str = Form(...),
):
    """Accept scene files + metadata, queue a stitch job."""
    scenes = json.loads(scenes_json)

    if len(scenes) != len(files):
        raise HTTPException(400, f"Got {len(files)} files but {len(scenes)} scene entries")
    if len(scenes) > MAX_SCENES:
        raise HTTPException(400, f"Max {MAX_SCENES} scenes allowed")

    for f in files:
        if not f.content_type or not f.content_type.startswith("video/"):
            raise HTTPException(400, f"File '{f.filename}' is not a video ({f.content_type})")

    # Save uploads to a temp directory (stitcher cleans up after job)
    upload_dir = Path(tempfile.mkdtemp(prefix="stitch_upload_"))
    for i, f in enumerate(files):
        dest = upload_dir / f"scene_{i}{Path(f.filename or '.mp4').suffix}"
        with open(dest, "wb") as out:
            out.write(await f.read())
        scenes[i]["filename"] = dest.name

    result = start_stitch_job(scenes, upload_dir)
    return result


@router.get("/job/{job_id}")
async def job_status(job_id: str):
    job = get_stitch_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/download/{filename}")
async def download(filename: str):
    if not filename.startswith("stitch_"):
        raise HTTPException(400, "Invalid filename")
    path = VIDEO_OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(path, media_type="video/mp4", filename=filename)
