"""Knowledge base endpoints — CRUD for skills/ and memory/ files."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from config import SKILLS_DIR, MEMORY_DIR, PROJECT_ROOT
from models import FileContent

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _build_tree(directory: Path, prefix: str = "") -> list[dict]:
    """Recursively build a file tree."""
    if not directory.exists():
        return []
    items = []
    for entry in sorted(directory.iterdir()):
        if entry.name.startswith("."):
            continue
        rel = f"{prefix}/{entry.name}" if prefix else entry.name
        if entry.is_dir():
            items.append({
                "path": rel,
                "name": entry.name,
                "is_dir": True,
                "children": _build_tree(entry, rel),
            })
        elif entry.suffix == ".md":
            items.append({
                "path": rel,
                "name": entry.name,
                "is_dir": False,
            })
    return items


@router.get("/tree")
def get_tree():
    """Get file tree for skills/ and memory/."""
    return {
        "skills": _build_tree(SKILLS_DIR),
        "memory": _build_tree(MEMORY_DIR),
    }


def _resolve_path(section: str, file_path: str) -> Path:
    """Resolve and validate a file path."""
    base = SKILLS_DIR if section == "skills" else MEMORY_DIR
    resolved = (base / file_path).resolve()
    # Security check
    if not str(resolved).startswith(str(base.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    return resolved


@router.get("/file")
def read_file(section: str, path: str):
    """Read a markdown file from skills/ or memory/."""
    resolved = _resolve_path(section, path)
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileContent(path=path, content=resolved.read_text())


@router.put("/file")
def write_file(section: str, path: str, body: FileContent):
    """Update a markdown file."""
    resolved = _resolve_path(section, path)
    if not resolved.parent.exists():
        raise HTTPException(status_code=404, detail="Parent directory not found")
    resolved.write_text(body.content)
    return {"ok": True}
