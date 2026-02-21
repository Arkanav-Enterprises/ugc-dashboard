"""X/Twitter research — twscrape for search/user-tweets, bird CLI for trending."""

import asyncio
import json
import subprocess
from datetime import date

import os

from config import (
    BIRD_CLI, BIRD_AUTH_TOKEN, BIRD_CT0, MEMORY_DIR, TWSCRAPE_DB,
)
from models import ResearchResult, SaveInsightRequest, XPost, XTrend

X_TRENDS_PATH = MEMORY_DIR / "x-trends.md"

# ---------------------------------------------------------------------------
# twscrape helpers
# ---------------------------------------------------------------------------

_twscrape_api = None


def _get_twscrape_api():
    """Return a reusable twscrape API instance, adding the account on first call."""
    global _twscrape_api
    if _twscrape_api is not None:
        return _twscrape_api

    from pathlib import Path
    from twscrape import API

    db_path = Path(str(TWSCRAPE_DB))

    # Delete stale DB from prior (broken) twscrape 0.17 installs so we
    # get a clean account entry with the new version's schema.
    if db_path.exists():
        db_path.unlink()

    _twscrape_api = API(str(TWSCRAPE_DB))

    if BIRD_AUTH_TOKEN and BIRD_CT0:
        async def _add():
            cookies = f"auth_token={BIRD_AUTH_TOKEN}; ct0={BIRD_CT0}"
            await _twscrape_api.pool.add_account(
                "main", "", "", "",
                cookies=cookies,
            )
        asyncio.run(_add())

    return _twscrape_api


def _tweet_to_xpost(tweet) -> XPost:
    """Map a twscrape Tweet object to our XPost model."""
    return XPost(
        handle=tweet.user.username if tweet.user else "",
        text=tweet.rawContent,
        likes=tweet.likeCount or 0,
        retweets=tweet.retweetCount or 0,
        replies=tweet.replyCount or 0,
        url=tweet.url or "",
        created_at=tweet.date.isoformat() if tweet.date else "",
    )


# ---------------------------------------------------------------------------
# bird CLI helpers (kept for trending)
# ---------------------------------------------------------------------------

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


def _bird_env() -> dict[str, str]:
    """Build env dict with bird auth credentials."""
    env = os.environ.copy()
    if BIRD_AUTH_TOKEN:
        env["AUTH_TOKEN"] = BIRD_AUTH_TOKEN
    if BIRD_CT0:
        env["CT0"] = BIRD_CT0
    return env


def _run_bird(args: list[str]) -> tuple[str, str]:
    """Run bird with the given args and return (stdout, stderr)."""
    cmd = [str(BIRD_CLI)] + args
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=30,
        env=_bird_env(),
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"bird exited with code {proc.returncode}")
    return proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_posts(query: str, count: int = 10) -> ResearchResult:
    """Search X posts by keyword using twscrape."""
    try:
        api = _get_twscrape_api()

        async def _search():
            results = []
            async for tweet in api.search(query, limit=count, kv={"product": "Top"}):
                results.append(_tweet_to_xpost(tweet))
            return results

        posts = asyncio.run(_search())
        # Sort by total engagement descending
        posts.sort(key=lambda p: p.likes + p.retweets + p.replies, reverse=True)
        return ResearchResult(posts=posts)
    except Exception as e:
        return ResearchResult(error=str(e))


def get_user_tweets(handle: str, count: int = 10) -> ResearchResult:
    """Get recent posts from a specific user using twscrape."""
    handle = handle.lstrip("@")
    try:
        api = _get_twscrape_api()

        async def _fetch():
            user = await api.user_by_login(handle)
            if not user:
                raise RuntimeError(f"User @{handle} not found")
            results = []
            async for tweet in api.user_tweets(user.id, limit=count):
                results.append(_tweet_to_xpost(tweet))
            return results

        posts = asyncio.run(_fetch())
        return ResearchResult(posts=posts)
    except Exception as e:
        return ResearchResult(error=str(e))


def get_trending() -> ResearchResult:
    """Get current trending topics (via bird CLI)."""
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
