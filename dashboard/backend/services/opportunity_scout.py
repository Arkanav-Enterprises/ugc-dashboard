"""Opportunity Scout — find content opportunities from App Store + Reddit pain points."""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

import anthropic
import httpx

from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, SCOUT_OUTPUT_DIR

HEADERS = {"User-Agent": "OpenClaw/1.0"}


# ─── iTunes autocomplete ────────────────────────────


def expand_seeds(seeds: list[str]) -> list[str]:
    """Expand seed keywords via iTunes autocomplete hints."""
    expanded = set()
    for seed in seeds:
        seed = seed.strip()
        if not seed:
            continue
        expanded.add(seed)
        try:
            resp = httpx.get(
                "https://search.itunes.apple.com/WebObjects/MZSearchHints.woa/wa/hints",
                params={"term": seed},
                headers=HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            for hint in data.get("hints", []):
                term = hint.get("term", "").strip()
                if term:
                    expanded.add(term)
        except Exception:
            pass  # autocomplete is best-effort
    return sorted(expanded)


# ─── iTunes search ───────────────────────────────────


def search_apps(keywords: list[str], limit: int = 10) -> list[dict]:
    """Search iTunes for apps matching keywords. Deduplicates by trackId."""
    seen_ids: set[int] = set()
    apps: list[dict] = []

    for kw in keywords:
        try:
            resp = httpx.get(
                "https://itunes.apple.com/search",
                params={
                    "term": kw,
                    "entity": "software",
                    "limit": limit,
                    "country": "us",
                },
                headers=HEADERS,
                timeout=15,
            )
            resp.raise_for_status()
            for result in resp.json().get("results", []):
                track_id = result.get("trackId")
                if not track_id or track_id in seen_ids:
                    continue
                seen_ids.add(track_id)
                apps.append({
                    "track_id": track_id,
                    "name": result.get("trackName", ""),
                    "developer": result.get("artistName", ""),
                    "rating": result.get("averageUserRating"),
                    "review_count": result.get("userRatingCount"),
                    "genre": result.get("primaryGenreName", ""),
                    "icon_url": result.get("artworkUrl100", ""),
                })
        except Exception:
            continue

    return apps


# ─── App Store reviews via RSS ───────────────────────


def fetch_reviews(app_id: int, app_name: str) -> list[dict]:
    """Fetch recent App Store reviews via the RSS JSON feed."""
    reviews: list[dict] = []
    try:
        url = f"https://itunes.apple.com/us/rss/customerreviews/id={app_id}/sortBy=mostRecent/json"
        resp = httpx.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        entries = data.get("feed", {}).get("entry", [])
        for entry in entries:
            # Skip the first entry if it's the app metadata
            if "im:rating" not in entry:
                continue
            reviews.append({
                "author": entry.get("author", {}).get("name", {}).get("label", ""),
                "rating": int(entry.get("im:rating", {}).get("label", "0")),
                "title": entry.get("title", {}).get("label", ""),
                "content": entry.get("content", {}).get("label", ""),
            })
    except Exception:
        pass
    return reviews


# ─── Reddit pain points ─────────────────────────────


def search_reddit_pain_points(app_name: str) -> list[dict]:
    """Search Reddit for pain-point threads about an app."""
    query = f'"{app_name}" pain OR frustrating OR hate OR issue OR bug'
    threads: list[dict] = []
    try:
        resp = httpx.get(
            "https://www.reddit.com/search.json",
            params={"q": query, "sort": "relevance", "t": "year", "limit": 10},
            headers=HEADERS,
            timeout=15,
        )
        if resp.status_code == 429:
            return []
        resp.raise_for_status()
        data = resp.json()
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            selftext = (post.get("selftext") or "")[:300]
            threads.append({
                "thread_id": post.get("id", ""),
                "title": post.get("title", ""),
                "subreddit": post.get("subreddit", ""),
                "score": post.get("score", 0),
                "num_comments": post.get("num_comments", 0),
                "permalink": post.get("permalink", ""),
                "selftext_preview": selftext,
            })
    except Exception:
        pass
    return threads


# ─── Main pipeline (async generator for SSE) ────────


async def run_scout(
    seeds: list[str],
    skip_reviews: bool = False,
    skip_reddit: bool = False,
) -> AsyncGenerator[dict, None]:
    """Async generator yielding SSE events for the full scout pipeline."""

    # Step 1: Expand seeds
    yield {"type": "status", "step": "expanding", "message": "Expanding seed keywords via iTunes autocomplete..."}
    keywords = await asyncio.to_thread(expand_seeds, seeds)
    yield {"type": "seeds_expanded", "keywords": keywords}

    # Step 2: Search apps
    yield {"type": "status", "step": "searching", "message": f"Searching iTunes for {len(keywords)} keywords..."}
    apps = await asyncio.to_thread(search_apps, keywords)
    yield {"type": "apps_found", "apps": apps}

    if not apps:
        yield {"type": "status", "step": "analyzing", "message": "No apps found — skipping to analysis."}
        yield {"type": "complete", "id": ""}
        return

    # Step 3: Fetch reviews
    all_reviews: dict[int, list[dict]] = {}
    if not skip_reviews:
        total = len(apps)
        for i, app in enumerate(apps):
            yield {
                "type": "status",
                "step": "reviews",
                "app": app["name"],
                "progress": f"{i + 1}/{total}",
                "message": f"Fetching reviews for {app['name']}...",
            }
            reviews = await asyncio.to_thread(fetch_reviews, app["track_id"], app["name"])
            all_reviews[app["track_id"]] = reviews
            yield {
                "type": "app_reviews",
                "app_id": app["track_id"],
                "app_name": app["name"],
                "reviews": reviews,
                "count": len(reviews),
            }

    # Step 4: Reddit pain points
    all_reddit: dict[int, list[dict]] = {}
    if not skip_reddit:
        total = len(apps)
        for i, app in enumerate(apps):
            yield {
                "type": "status",
                "step": "reddit",
                "app": app["name"],
                "progress": f"{i + 1}/{total}",
                "message": f"Searching Reddit pain points for {app['name']}...",
            }
            threads = await asyncio.to_thread(search_reddit_pain_points, app["name"])
            all_reddit[app["track_id"]] = threads
            yield {
                "type": "app_reddit",
                "app_id": app["track_id"],
                "app_name": app["name"],
                "threads": threads,
                "count": len(threads),
            }

    # Step 5: Claude analysis
    if not ANTHROPIC_API_KEY:
        yield {"type": "error", "content": "ANTHROPIC_API_KEY not configured"}
        return

    yield {"type": "status", "step": "analyzing", "message": "Running opportunity analysis with Claude..."}

    # Build context for Claude
    context_parts: list[str] = []
    for app in apps:
        tid = app["track_id"]
        section = f"## {app['name']} (by {app['developer']})\n"
        section += f"Rating: {app.get('rating', 'N/A')} | Reviews: {app.get('review_count', 'N/A')} | Genre: {app.get('genre', 'N/A')}\n"

        reviews = all_reviews.get(tid, [])
        if reviews:
            section += "\n### App Store Reviews:\n"
            for r in reviews[:10]:
                section += f"- [{r['rating']}/5] {r['title']}: {r['content'][:200]}\n"

        threads = all_reddit.get(tid, [])
        if threads:
            section += "\n### Reddit Pain Points:\n"
            for t in threads[:5]:
                section += f"- [{t['subreddit']}] {t['title']} (score: {t['score']})\n"
                if t.get("selftext_preview"):
                    section += f"  {t['selftext_preview'][:150]}\n"

        context_parts.append(section)

    full_context = "\n\n".join(context_parts)
    # Truncate if too long
    if len(full_context) > 50000:
        full_context = full_context[:50000] + "\n\n[... truncated for length]"

    prompt = f"""You are an opportunity scout for a UGC content agency that makes reaction videos about apps.

Analyze these apps and their user feedback (App Store reviews + Reddit pain points) to identify content opportunities.

Seeds searched: {', '.join(seeds)}

{full_context}

Provide a structured analysis with:

1. **Top Opportunity Apps** — Which apps have the most content potential? Consider:
   - Review volume and complaint patterns
   - Reddit discussion activity
   - Pain points that make good reaction content

2. **Common Pain Points** — Recurring complaints across apps that we could make content about

3. **Content Angles** — Specific video ideas, hooks, and angles for reaction content

4. **Market Gaps** — Underserved areas where users are unhappy but there's little content coverage

5. **Recommended Priority** — Rank the top 5 apps to target first and why

Use markdown formatting. Be specific and actionable."""

    analysis = ""
    try:
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        async with client.messages.stream(
            model=ANTHROPIC_MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for text in stream.text_stream:
                analysis += text
                yield {"type": "analysis_chunk", "content": text}
    except Exception as e:
        yield {"type": "error", "content": f"Claude analysis failed: {str(e)}"}
        return

    # Save result
    result_data = {
        "seeds": seeds,
        "keywords": keywords,
        "apps": apps,
        "reviews": {str(k): v for k, v in all_reviews.items()},
        "reddit": {str(k): v for k, v in all_reddit.items()},
        "analysis": analysis,
    }
    result_id = save_scout_result(result_data)
    yield {"type": "complete", "id": result_id}


# ─── File persistence ────────────────────────────────


def save_scout_result(data: dict) -> str:
    """Save scout result to output/scout/{uuid}.json."""
    SCOUT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result_id = str(uuid.uuid4())[:8]
    data["id"] = result_id
    data["created_at"] = datetime.now(timezone.utc).isoformat()
    path = SCOUT_OUTPUT_DIR / f"{result_id}.json"
    path.write_text(json.dumps(data, indent=2))
    return result_id


def list_scout_results() -> list[dict]:
    """List past scout results."""
    if not SCOUT_OUTPUT_DIR.exists():
        return []
    results = []
    for path in sorted(SCOUT_OUTPUT_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(path.read_text())
            results.append({
                "id": data.get("id", path.stem),
                "seeds": data.get("seeds", []),
                "app_count": len(data.get("apps", [])),
                "created_at": data.get("created_at", ""),
            })
        except Exception:
            continue
    return results


def load_scout_result(result_id: str) -> dict | None:
    """Load a specific scout result."""
    path = SCOUT_OUTPUT_DIR / f"{result_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())
