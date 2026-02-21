"""Reddit research — search threads, fetch comments, summarize, cross-analyze."""

import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

import anthropic
import requests

from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, RESEARCH_OUTPUT_DIR

REDDIT_HEADERS = {"User-Agent": "OpenClaw/1.0"}


# ─── Search ───────────────────────────────────────────


def search_reddit(
    query: str,
    subreddits: list[str] | None = None,
    time_filter: str = "week",
    limit: int = 25,
) -> dict:
    """Search Reddit for threads matching query. Returns list of thread metadata."""
    threads = []

    if subreddits:
        # Search within each specified subreddit
        for sub in subreddits:
            sub = sub.strip().lstrip("r/")
            url = f"https://www.reddit.com/r/{sub}/search.json"
            params = {
                "q": query,
                "sort": "relevance",
                "t": time_filter,
                "limit": limit,
                "restrict_sr": "on",
            }
            threads.extend(_fetch_search_results(url, params))
    else:
        url = "https://www.reddit.com/search.json"
        params = {
            "q": query,
            "sort": "relevance",
            "t": time_filter,
            "limit": limit,
        }
        threads = _fetch_search_results(url, params)

    # Sort by score descending
    threads.sort(key=lambda t: t["score"], reverse=True)
    return {"query": query, "threads": threads[:limit]}


def _fetch_search_results(url: str, params: dict) -> list[dict]:
    """Fetch search results from a Reddit search endpoint."""
    resp = requests.get(url, params=params, headers=REDDIT_HEADERS, timeout=15)
    if resp.status_code == 429:
        raise ValueError("Reddit rate limited, try again in a minute")
    resp.raise_for_status()

    data = resp.json()
    threads = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        if post.get("is_self") is False and not post.get("selftext"):
            selftext_preview = f"[Link: {post.get('url', '')}]"
        else:
            selftext_preview = (post.get("selftext") or "")[:300]

        threads.append({
            "thread_id": post.get("id", ""),
            "title": post.get("title", ""),
            "subreddit": post.get("subreddit", ""),
            "score": post.get("score", 0),
            "num_comments": post.get("num_comments", 0),
            "permalink": post.get("permalink", ""),
            "created_utc": post.get("created_utc", 0),
            "selftext_preview": selftext_preview,
            "url": post.get("url", ""),
        })
    return threads


# ─── Fetch thread comments ────────────────────────────


def fetch_thread_comments(permalink: str, limit: int = 20) -> list[str]:
    """Fetch top comments from a Reddit thread as plain text."""
    url = f"https://www.reddit.com{permalink}.json"
    params = {"limit": limit, "sort": "top"}

    try:
        resp = requests.get(url, params=params, headers=REDDIT_HEADERS, timeout=15)
        if resp.status_code == 429:
            return ["[Rate limited — could not fetch comments]"]
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    if not isinstance(data, list) or len(data) < 2:
        return []

    comments = []
    for child in data[1].get("data", {}).get("children", []):
        if child.get("kind") != "t1":
            continue
        body = child.get("data", {}).get("body", "")
        if body and body != "[deleted]" and body != "[removed]":
            # Truncate very long comments
            comments.append(body[:1000])
        if len(comments) >= limit:
            break

    return comments


# ─── Analysis (async generator for SSE) ──────────────


async def run_reddit_analysis(
    query: str,
    threads: list[dict],
) -> AsyncGenerator[dict, None]:
    """Async generator yielding SSE events for the Reddit research pipeline."""
    if not ANTHROPIC_API_KEY:
        yield {"type": "error", "content": "ANTHROPIC_API_KEY not configured"}
        return

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    summaries: list[dict] = []
    total = len(threads)

    for i, thread in enumerate(threads):
        title = thread.get("title", "Untitled")
        permalink = thread.get("permalink", "")
        subreddit = thread.get("subreddit", "")
        thread_id = thread.get("thread_id", str(i))

        yield {
            "type": "status",
            "content": f"Fetching comments for: {title}",
            "progress": i,
            "total": total,
        }

        # Fetch comments (run in thread to avoid blocking)
        comments = await asyncio.to_thread(fetch_thread_comments, permalink)

        if not comments:
            summary = {
                "thread_id": thread_id,
                "title": title,
                "subreddit": subreddit,
                "summary": None,
                "key_points": [],
                "sentiment": None,
                "error": "No comments available",
            }
            summaries.append(summary)
            yield {"type": "thread_error", "thread_id": thread_id, "title": title}
            continue

        # Summarize with Claude
        yield {
            "type": "status",
            "content": f"Summarizing: {title}",
            "progress": i,
            "total": total,
        }

        selftext = thread.get("selftext_preview", "")
        comments_text = "\n---\n".join(comments[:15])

        try:
            resp = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": f"""Analyze this Reddit thread and its top comments.

Thread title: {title}
Subreddit: r/{subreddit}
Post body: {selftext}

Top comments:
{comments_text}

Provide:
1. A concise summary (2-3 sentences) of the discussion
2. 3-5 key points/takeaways as a JSON array of strings
3. Overall sentiment: "positive", "negative", "mixed", or "neutral"

Respond in this exact JSON format:
{{"summary": "...", "key_points": ["...", "..."], "sentiment": "..."}}""",
                }],
            )

            raw = resp.content[0].text
            parsed = _extract_json(raw)
            summary = {
                "thread_id": thread_id,
                "title": title,
                "subreddit": subreddit,
                "summary": parsed.get("summary", raw),
                "key_points": parsed.get("key_points", []),
                "sentiment": parsed.get("sentiment"),
                "error": None,
            }
        except Exception as e:
            summary = {
                "thread_id": thread_id,
                "title": title,
                "subreddit": subreddit,
                "summary": None,
                "key_points": [],
                "sentiment": None,
                "error": f"Summarization failed: {str(e)}",
            }

        summaries.append(summary)
        yield {"type": "thread_summary", "data": summary}

    # Check if we have any summaries to cross-analyze
    valid_summaries = [s for s in summaries if s.get("summary")]
    if not valid_summaries:
        yield {"type": "error", "content": "No comments available for any selected thread"}
        return

    # Cross-analysis with streaming
    yield {
        "type": "status",
        "content": "Running cross-thread analysis...",
        "progress": total,
        "total": total,
    }

    summaries_text = "\n\n".join(
        f"**{s['title']}** (r/{s['subreddit']})\n{s['summary']}\nKey points: {', '.join(s['key_points'])}\nSentiment: {s.get('sentiment', 'unknown')}"
        for s in valid_summaries
    )

    cross_analysis = ""
    try:
        with client.messages.stream(
            model=ANTHROPIC_MODEL,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": f"""You are a trend research analyst. Analyze these Reddit thread summaries about "{query}" and identify patterns, themes, and opportunities.

{summaries_text}

Provide a structured analysis with:
1. **Common Themes** — recurring topics, opinions, or concerns across threads
2. **Community Sentiment** — overall mood and attitudes toward the topic
3. **Trending Opportunities** — gaps, pain points, or angles we could leverage for content
4. **Key Takeaways** — actionable insights for content creators

Use markdown formatting.""",
            }],
        ) as stream:
            for text in stream.text_stream:
                cross_analysis += text
                yield {"type": "cross_analysis_chunk", "content": text}
    except Exception as e:
        yield {"type": "error", "content": f"Cross-analysis failed: {str(e)}"}
        return

    # Save result
    research_id = str(uuid.uuid4())[:8]
    result = {
        "id": research_id,
        "source": "reddit",
        "query": query,
        "channel_name": f"Reddit: {query}",  # for list compat
        "created_at": datetime.now(timezone.utc).isoformat(),
        "thread_summaries": summaries,
        "video_summaries": summaries,  # alias for list compat
        "cross_analysis": cross_analysis,
    }
    save_research(result)

    yield {"type": "complete", "id": research_id}


def _extract_json(text: str) -> dict:
    """Try to extract JSON from a Claude response that may have surrounding text."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {}


# ─── File persistence ─────────────────────────────────


def save_research(data: dict):
    RESEARCH_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = RESEARCH_OUTPUT_DIR / f"{data['id']}.json"
    path.write_text(json.dumps(data, indent=2))
    return path


def load_research(research_id: str) -> dict | None:
    path = RESEARCH_OUTPUT_DIR / f"{research_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())
