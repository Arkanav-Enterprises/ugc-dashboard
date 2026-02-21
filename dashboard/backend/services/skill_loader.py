"""Read and walk skills/ and memory/ trees for chat context."""

from config import SKILLS_DIR, MEMORY_DIR

DEFAULT_SKILL_FILES = [
    "INDEX.md",
    "manifest-lock.md",
    "content/content-mix.md",
    "content/hook-architecture.md",
    "content/what-never-works.md",
]

DEFAULT_MEMORY_FILES = [
    "post-performance.md",
    "failure-log.md",
    "x-trends.md",
]


def list_skill_files() -> list[str]:
    """List all .md files in skills/ recursively."""
    if not SKILLS_DIR.exists():
        return []
    return sorted(str(f.relative_to(SKILLS_DIR)) for f in SKILLS_DIR.rglob("*.md"))


def list_memory_files() -> list[str]:
    """List all .md files in memory/."""
    if not MEMORY_DIR.exists():
        return []
    return sorted(str(f.relative_to(MEMORY_DIR)) for f in MEMORY_DIR.rglob("*.md"))


def load_context(skill_files: list[str] | None = None, memory_files: list[str] | None = None) -> str:
    """Load skill + memory files as context string (matching autopilot_video.py pattern)."""
    if skill_files is None:
        skill_files = DEFAULT_SKILL_FILES
    if memory_files is None:
        memory_files = DEFAULT_MEMORY_FILES

    parts = []
    for name in skill_files:
        path = SKILLS_DIR / name
        if path.exists():
            parts.append(f"=== SKILL: {name} ===\n{path.read_text()}")

    for name in memory_files:
        path = MEMORY_DIR / name
        if path.exists():
            content = path.read_text().strip()
            if content:
                parts.append(f"=== MEMORY: {name} ===\n{content}")

    return "\n\n".join(parts)
