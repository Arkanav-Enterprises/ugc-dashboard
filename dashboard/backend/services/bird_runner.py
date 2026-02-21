"""Subprocess wrapper for the bird CLI (@steipete/bird) — read-only X/Twitter research."""

import json
import subprocess
from datetime import date

from config import BIRD_CLI, MEMORY_DIR
from models import ResearchResult, SaveInsightRequest, XPost, XTrend

X_TRENDS_PATH = MEMORY_DIR / "x-trends.md"


def check_bird_available() -> dict:
    """Return {"available": True/False, "version": ...}."""
    try:
        proc = subprocess.run(
            [str(BIRD_CLI), "--version"],
            capture_output=True, text=True, timeout=10,
        )
        return {"available": proc.returncode == 0, "version": proc.stdout.strip()}
    except Exception:
        return {"available": False, "version": ""}


def _run_bird(args: list[str]) -> tuple[str, str]:
    """Run bird with the given args and return (stdout, stderr)."""
    cmd = [str(BIRD_CLI)] + args
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"bird exited with code {proc.returncode}")
    return proc.stdout, proc.stderr


def _parse_posts_from_text(raw: str) -> list[XPost]:
    """Best-effort text parsing when JSON is unavailable."""
    posts: list[XPost] = []
    current: dict = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            if current.get("text"):
                posts.append(XPost(**current))
                current = {}
            continue
        if line.startswith("@"):
            current["handle"] = line.split()[0]
        elif not current.get("text"):
            current["text"] = line
        else:
            current["text"] += " " + line
    if current.get("text"):
        posts.append(XPost(**current))
    return posts


def _parse_posts_json(raw: str) -> list[XPost]:
    """Try to parse bird's JSON output into XPost list."""
    data = json.loads(raw)
    items = data if isinstance(data, list) else data.get("posts", data.get("results", [data]))
    posts = []
    for item in items:
        if not isinstance(item, dict):
            continue
        posts.append(XPost(
            handle=item.get("author", {}).get("handle", item.get("handle", item.get("username", ""))),
            text=item.get("text", item.get("content", "")),
            likes=int(item.get("likes", item.get("like_count", 0))),
            retweets=int(item.get("retweets", item.get("retweet_count", 0))),
            replies=int(item.get("replies", item.get("reply_count", 0))),
            url=item.get("url", item.get("link", "")),
            created_at=item.get("created_at", item.get("date", "")),
        ))
    return posts


def search_posts(query: str, count: int = 10) -> ResearchResult:
    """Search X posts by keyword."""
    try:
        raw, _ = _run_bird(["search", query, "--count", str(count)])
    except Exception as e:
        return ResearchResult(error=str(e))

    try:
        posts = _parse_posts_json(raw)
    except (json.JSONDecodeError, Exception):
        posts = _parse_posts_from_text(raw)
    return ResearchResult(posts=posts, raw_output=raw)


def get_user_tweets(handle: str, count: int = 10) -> ResearchResult:
    """Get recent posts from a specific user."""
    handle = handle.lstrip("@")
    try:
        raw, _ = _run_bird(["user", handle, "--count", str(count)])
    except Exception as e:
        return ResearchResult(error=str(e))

    try:
        posts = _parse_posts_json(raw)
    except (json.JSONDecodeError, Exception):
        posts = _parse_posts_from_text(raw)
    return ResearchResult(posts=posts, raw_output=raw)


def get_trending() -> ResearchResult:
    """Get current trending topics."""
    try:
        raw, _ = _run_bird(["trending"])
    except Exception as e:
        return ResearchResult(error=str(e))

    trends: list[XTrend] = []
    try:
        data = json.loads(raw)
        items = data if isinstance(data, list) else data.get("trends", [])
        for item in items:
            if isinstance(item, dict):
                trends.append(XTrend(
                    name=item.get("name", item.get("topic", "")),
                    tweet_count=str(item.get("tweet_count", item.get("volume", ""))),
                ))
            elif isinstance(item, str):
                trends.append(XTrend(name=item))
    except (json.JSONDecodeError, Exception):
        for line in raw.splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "-", "=")):
                trends.append(XTrend(name=line))

    return ResearchResult(trends=trends, raw_output=raw)


def save_insight(req: SaveInsightRequest) -> dict:
    """Append an insight to memory/x-trends.md under the correct section."""
    if not X_TRENDS_PATH.exists():
        return {"ok": False, "error": "memory/x-trends.md not found"}

    content = X_TRENDS_PATH.read_text()
    today = date.today().isoformat()
    # Truncate post text for table readability
    short_text = req.text[:80].replace("|", "/").replace("\n", " ")
    note = req.note.replace("|", "/").replace("\n", " ")

    section_markers = {
        "saved_posts": "## Saved Posts",
        "trending_formats": "## Trending Formats",
        "copy_patterns": "## Copy Patterns",
        "engagement_targets": "## Engagement Targets",
    }

    marker = section_markers.get(req.section)
    if not marker:
        return {"ok": False, "error": f"Unknown section: {req.section}"}

    if req.section == "saved_posts":
        row = f"| {today} | {req.handle} | {short_text} | {req.likes} | {req.retweets} | {note} |"
    elif req.section == "trending_formats":
        row = f"| {today} | {note} | {short_text} | | {req.handle} |"
    elif req.section == "copy_patterns":
        engagement = f"{req.likes}L/{req.retweets}RT"
        row = f"| {today} | {short_text} | {engagement} | {note} |"
    elif req.section == "engagement_targets":
        engagement = f"{req.likes}L/{req.retweets}RT"
        row = f"| {req.handle} | | {engagement} | {note} |"
    else:
        return {"ok": False, "error": "Unknown section"}

    # Find the last row in the section's table and append after it
    lines = content.split("\n")
    insert_idx = None
    in_section = False
    for i, line in enumerate(lines):
        if line.strip().startswith(marker):
            in_section = True
            continue
        if in_section:
            # Hit next section header — insert before it
            if line.strip().startswith("## ") and not line.strip().startswith(marker):
                insert_idx = i
                break
            # Track last non-empty line in section
            if line.strip().startswith("|") or line.strip() == "":
                insert_idx = i + 1

    if insert_idx is None:
        # Append at end of file
        insert_idx = len(lines)

    lines.insert(insert_idx, row)
    X_TRENDS_PATH.write_text("\n".join(lines))
    return {"ok": True}
