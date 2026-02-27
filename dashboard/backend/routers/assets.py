"""Asset endpoints — reference images, clips, usage history."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
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
