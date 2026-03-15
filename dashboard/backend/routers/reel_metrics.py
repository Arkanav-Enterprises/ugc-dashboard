"""Reel metrics endpoints — serves scraped Instagram reel data from output/reel_metrics/."""

import json
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query

from config import PROJECT_ROOT

router = APIRouter(prefix="/api/reel-metrics", tags=["reel-metrics"])

METRICS_DIR = PROJECT_ROOT / "output" / "reel_metrics"

ACCOUNT_META = {
    "aliyah.manifests": {"persona": "Aliyah", "app": "ManifestLock", "handle": "@aliyah.manifests"},
    "aliyah.journals":  {"persona": "Aliyah", "app": "JournalLock",  "handle": "@aliyah.journals"},
    "riley.manifests":  {"persona": "Riley",  "app": "ManifestLock", "handle": "@riley.manifests"},
    "riley.journals":   {"persona": "Riley",  "app": "JournalLock",  "handle": "@riley.journals"},
    "sanyahealing":     {"persona": "Sanya",  "app": "JournalLock",  "handle": "@sanyahealing"},
    "sophie.unplugs":   {"persona": "Sanya",  "app": "JournalLock",  "handle": "@sophie.unplugs"},
    "emillywilks":      {"persona": "Emilly", "app": "ManifestLock", "handle": "@emillywilks"},
}

# Pattern: accountname_YYYY-MM-DD.json
_FILENAME_RE = re.compile(r"^(.+)_(\d{4}-\d{2}-\d{2})\.json$")


def _latest_files() -> dict[str, tuple[Path, str]]:
    """Return {account: (path, date)} for the latest JSON per account."""
    if not METRICS_DIR.exists():
        return {}
    best: dict[str, tuple[Path, str]] = {}
    for f in METRICS_DIR.glob("*.json"):
        m = _FILENAME_RE.match(f.name)
        if not m:
            continue
        account, date = m.group(1), m.group(2)
        if account not in best or date > best[account][1]:
            best[account] = (f, date)
    return best


def _load_reels(path: Path, account: str) -> list[dict]:
    """Load reels from a JSON file, injecting account metadata."""
    try:
        reels = json.loads(path.read_text())
    except (json.JSONDecodeError, IOError):
        return []
    meta = ACCOUNT_META.get(account, {"persona": account, "app": "Unknown", "handle": f"@{account}"})
    for r in reels:
        r["account"] = account
        r["persona"] = meta["persona"]
    return reels


def _all_reels() -> tuple[list[dict], str | None]:
    """Load all reels from latest files. Returns (reels, last_scraped_date)."""
    files = _latest_files()
    all_reels: list[dict] = []
    last_date: str | None = None
    for account, (path, date) in files.items():
        all_reels.extend(_load_reels(path, account))
        if last_date is None or date > last_date:
            last_date = date
    return all_reels, last_date


def _extract_hook(caption: str) -> str:
    """First line of the caption is the hook."""
    return caption.strip().split("\n")[0].strip() if caption else ""


_NUMBER_RE = re.compile(r"\b\d[\d,]*\b")


def _classify_hook(hook: str) -> str:
    """Classify a hook into a pattern category via keyword matching."""
    h = hook.lower()

    if "plant" in h or "shrink" in h:
        return "Plant Metaphor"
    if h.startswith("wait why") or h.endswith("?"):
        return "Question Hook"
    if "my phone" in h and any(w in h for w in ("won't", "makes", "has", "guilt")):
        return "Phone Personification"
    if any(w in h for w in ("she ", "he ", "therapist", "boss", "roommate")):
        return "Social Context"
    if "i did the math" in h or "calculated" in h or "counted" in h:
        return "Math Shock"
    if "honestly" in h or "wasn't going to" in h:
        return "Confession"
    if _NUMBER_RE.search(h):
        return "Number Shock"
    return "Other"


# ─── Endpoints ──────────────────────────────────────


@router.get("/summary")
def get_summary():
    """Per-account summary stats from latest scraped files."""
    files = _latest_files()
    if not files:
        return {"accounts": [], "total_reels": 0, "total_views": 0, "avg_views": 0, "last_scraped": None}

    accounts = []
    total_reels = 0
    total_views = 0
    last_date: str | None = None

    for account, (path, date) in sorted(files.items()):
        reels = _load_reels(path, account)
        meta = ACCOUNT_META.get(account, {"persona": account, "app": "Unknown", "handle": f"@{account}"})
        views = sum(r.get("views", 0) for r in reels)
        count = len(reels)
        accounts.append({
            "account": account,
            "handle": meta["handle"],
            "persona": meta["persona"],
            "app": meta["app"],
            "reels_posted": count,
            "total_views": views,
            "avg_views": round(views / count) if count else 0,
        })
        total_reels += count
        total_views += views
        if last_date is None or date > last_date:
            last_date = date

    return {
        "accounts": accounts,
        "total_reels": total_reels,
        "total_views": total_views,
        "avg_views": round(total_views / total_reels) if total_reels else 0,
        "last_scraped": last_date,
    }


@router.get("/reels")
def get_reels(
    account: Optional[str] = Query(None),
    sort: str = Query("views", pattern="^(views|timestamp)$"),
    limit: int = Query(50, ge=1, le=500),
):
    """Individual reels, optionally filtered by account."""
    reels, _ = _all_reels()

    if account:
        reels = [r for r in reels if r["account"] == account]

    reverse = sort == "views"
    reels.sort(key=lambda r: r.get(sort, ""), reverse=reverse)
    return reels[:limit]


@router.get("/top")
def get_top_reels(n: int = Query(15, ge=1, le=100)):
    """Top N reels across all accounts by views."""
    reels, _ = _all_reels()
    reels.sort(key=lambda r: r.get("views", 0), reverse=True)
    return reels[:n]


@router.get("/patterns")
def get_patterns():
    """Analyze hook patterns from captions."""
    reels, _ = _all_reels()

    buckets: dict[str, list[dict]] = {}
    for r in reels:
        hook = _extract_hook(r.get("caption", ""))
        pattern = _classify_hook(hook)
        buckets.setdefault(pattern, []).append({"hook": hook, "views": r.get("views", 0)})

    results = []
    for pattern, items in sorted(buckets.items(), key=lambda x: -len(x[1])):
        views = [i["views"] for i in items]
        best = max(items, key=lambda i: i["views"])
        results.append({
            "pattern": pattern,
            "count": len(items),
            "avg_views": round(sum(views) / len(views)) if views else 0,
            "best_hook": best["hook"],
            "best_views": max(views),
            "worst_views": min(views),
        })

    return results
