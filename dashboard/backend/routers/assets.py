"""Asset endpoints — reference images, clips, usage history."""

import asyncio
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from config import ASSETS_DIR, REF_IMAGES_DIR, MEMORY_DIR, PERSONAS, PROJECT_ROOT

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("/reference-images")
def list_reference_images():
    """List all reference images grouped by persona."""
    if not REF_IMAGES_DIR.exists():
        return []
    images = []
    for f in sorted(REF_IMAGES_DIR.iterdir()):
        if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg"):
            # Infer persona from filename
            persona = None
            for p in PERSONAS:
                if f.name.startswith(p):
                    persona = p
                    break
            images.append({
                "name": f.name,
                "path": f"reference-images/{f.name}",
                "persona": persona,
            })
    return images


@router.get("/clips")
def list_clips():
    """List all generated clips by persona and type."""
    clips = []
    for persona in PERSONAS:
        for clip_type in ["hook", "reaction"]:
            clip_dir = ASSETS_DIR / persona / clip_type
            if not clip_dir.exists():
                continue
            for f in sorted(clip_dir.iterdir()):
                if f.is_file() and f.suffix.lower() in (".mp4", ".mov"):
                    clips.append({
                        "name": f.name,
                        "path": f"{persona}/{clip_type}/{f.name}",
                        "persona": persona,
                        "type": clip_type,
                    })
    return clips


@router.get("/usage")
def get_asset_usage():
    """Parse asset-usage.md and return structured usage data."""
    usage_path = MEMORY_DIR / "asset-usage.md"
    if not usage_path.exists():
        return []
    content = usage_path.read_text()
    rows = []
    in_table = False
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("|") and "Date" in line and "Account" in line:
            in_table = True
            continue
        if line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 5:
                rows.append({
                    "date": parts[0],
                    "account": parts[1],
                    "hook_clip": parts[2],
                    "reaction_clip": parts[3],
                    "screen_recording": parts[4],
                })
        elif in_table and not line.startswith("|"):
            in_table = False
    return rows


@router.get("/file/{file_path:path}")
def serve_asset(file_path: str):
    """Serve an asset file (image or video)."""
    full_path = ASSETS_DIR / file_path
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    # Security check
    try:
        full_path.resolve().relative_to(ASSETS_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    media_types = {
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    media_type = media_types.get(full_path.suffix.lower(), "application/octet-stream")
    return FileResponse(full_path, media_type=media_type)


def _validate_persona(persona: str):
    if persona not in PERSONAS:
        raise HTTPException(status_code=400, detail=f"Unknown persona: {persona}")


def _validate_clip_name(name: str):
    if not name.lower().endswith((".mp4", ".mov")):
        raise HTTPException(status_code=400, detail="Filename must end with .mp4 or .mov")


@router.post("/upload-clip")
async def upload_clip(
    file: UploadFile = File(...),
    persona: str = Form(...),
    clip_name: str = Form(...),
):
    """Upload a hook clip for a persona."""
    _validate_persona(persona)
    _validate_clip_name(clip_name)

    dest_dir = ASSETS_DIR / persona / "hook"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / clip_name

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"ok": True, "path": f"{persona}/hook/{clip_name}"}


@router.post("/upload-reaction")
async def upload_reaction(
    file: UploadFile | None = File(None),
    persona: str = Form(...),
    clip_name: str = Form(...),
    auto_generate: bool = Form(False),
):
    """Upload a reaction clip, or auto-generate one from the last 2.5s of the matching hook."""
    _validate_persona(persona)
    _validate_clip_name(clip_name)

    dest_dir = ASSETS_DIR / persona / "reaction"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / clip_name

    if file is not None:
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
    elif auto_generate:
        hook_path = ASSETS_DIR / persona / "hook" / clip_name
        if not hook_path.exists():
            raise HTTPException(status_code=404, detail=f"Hook clip not found: {clip_name}")
        # Clip last 2.5s — same pattern as assemble_video.py
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-sseof", "-2.5", "-i", str(hook_path),
            "-c:v", "libx264", "-c:a", "aac", str(dest),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise HTTPException(status_code=500, detail=f"FFmpeg failed: {stderr.decode()[-500:]}")
    else:
        raise HTTPException(status_code=400, detail="Provide either a file or set auto_generate=true")

    return {"ok": True, "path": f"{persona}/reaction/{clip_name}"}


@router.delete("/clip/{persona}/{clip_type}/{filename}")
async def delete_clip(persona: str, clip_type: str, filename: str):
    """Delete a clip and its paired counterpart (hook↔reaction)."""
    if clip_type not in ("hook", "reaction"):
        raise HTTPException(status_code=400, detail="clip_type must be hook or reaction")
    _validate_persona(persona)

    target = ASSETS_DIR / persona / clip_type / filename
    # Path traversal protection
    try:
        target.resolve().relative_to(ASSETS_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if not target.exists():
        raise HTTPException(status_code=404, detail="Clip not found")

    deleted = []
    target.unlink()
    deleted.append(f"{persona}/{clip_type}/{filename}")

    # Delete paired clip if it exists
    paired_type = "reaction" if clip_type == "hook" else "hook"
    paired = ASSETS_DIR / persona / paired_type / filename
    if paired.exists():
        paired.unlink()
        deleted.append(f"{persona}/{paired_type}/{filename}")

    return {"ok": True, "deleted": deleted}
