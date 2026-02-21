"""YouTube channel research — scan, transcribe, summarize, cross-analyze."""

import asyncio
import json
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

import anthropic

from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, RESEARCH_OUTPUT_DIR, PROJECT_ROOT


def _yt_dlp_bin() -> str:
    """Find yt-dlp binary — prefer the one in the same venv as the running Python."""
    venv_bin = Path(sys.executable).parent / "yt-dlp"
    if venv_bin.exists():
        return str(venv_bin)
    system_bin = shutil.which("yt-dlp")
    if system_bin:
        return system_bin
    raise FileNotFoundError("yt-dlp not installed")


def _cookies_args() -> list[str]:
    """Return --cookies arg if yt-cookies.txt exists in project root."""
    cookies_path = PROJECT_ROOT / "yt-cookies.txt"
    if cookies_path.exists():
        return ["--cookies", str(cookies_path)]
    return []


# ─── Channel scanning ────────────────────────────────


def scan_channel(url: str, max_videos: int = 20) -> dict:
    """Scan a YouTube channel and return video metadata."""
    # Normalize URL to /videos for playlist extraction
    clean_url = url.rstrip("/")
    if not clean_url.endswith("/videos"):
        clean_url += "/videos"

    cmd = [
        _yt_dlp_bin(),
        *_cookies_args(),
        "--flat-playlist",
        "--dump-json",
        "--playlist-end", str(max_videos),
        clean_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    if result.returncode != 0:
        raise ValueError(f"yt-dlp failed: {result.stderr.strip()}")

    videos = []
    channel_name = ""
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if not channel_name:
            channel_name = entry.get("channel") or entry.get("playlist_channel") or entry.get("playlist_uploader") or entry.get("uploader") or "Unknown"

        videos.append({
            "video_id": entry.get("id", ""),
            "title": entry.get("title", "Untitled"),
            "duration": entry.get("duration"),
            "thumbnail": entry.get("thumbnails", [{}])[-1].get("url") if entry.get("thumbnails") else None,
            "view_count": entry.get("view_count"),
            "upload_date": entry.get("upload_date"),
        })

    return {
        "channel_name": channel_name or "Unknown Channel",
        "channel_url": url,
        "videos": videos,
    }


# ─── Transcript fetching ─────────────────────────────


def fetch_transcript(video_id: str) -> str | None:
    """Download and parse subtitles for a video. Returns plain text or None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            _yt_dlp_bin(),
            *_cookies_args(),
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang", "en",
            "--skip-download",
            "--convert-subs", "vtt",
            "-o", f"{tmpdir}/%(id)s.%(ext)s",
            f"https://www.youtube.com/watch?v={video_id}",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        # Find subtitle files — check both .vtt and any other sub format
        sub_files = list(Path(tmpdir).glob("*.vtt"))
        if not sub_files:
            # Fallback: try any subtitle file that was downloaded
            sub_files = list(Path(tmpdir).glob("*.en.*"))
        if not sub_files:
            return None

        vtt_text = sub_files[0].read_text(encoding="utf-8", errors="replace")
        return _vtt_to_plain_text(vtt_text)


def _vtt_to_plain_text(vtt: str) -> str:
    """Convert VTT subtitle content to plain text."""
    lines = []
    seen = set()
    for line in vtt.split("\n"):
        # Skip VTT headers, timestamps, and blank lines
        if line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if re.match(r"\d{2}:\d{2}:\d{2}\.\d{3}\s*-->", line):
            continue
        if not line.strip():
            continue
        # Remove VTT tags like <c> </c> <00:00:01.234>
        clean = re.sub(r"<[^>]+>", "", line).strip()
        if clean and clean not in seen:
            seen.add(clean)
            lines.append(clean)
    return " ".join(lines)


# ─── Analysis (async generator for SSE) ──────────────


async def run_analysis(
    channel_name: str,
    channel_url: str,
    video_ids: list[str],
    video_titles: dict[str, str],
) -> AsyncGenerator[dict, None]:
    """Async generator yielding SSE events for the research pipeline."""
    if not ANTHROPIC_API_KEY:
        yield {"type": "error", "content": "ANTHROPIC_API_KEY not configured"}
        return

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    summaries: list[dict] = []
    total = len(video_ids)

    for i, vid in enumerate(video_ids):
        title = video_titles.get(vid, vid)
        yield {"type": "status", "content": f"Fetching transcript for: {title}", "progress": i, "total": total}

        # Fetch transcript (run in thread to avoid blocking)
        transcript = await asyncio.to_thread(fetch_transcript, vid)

        if not transcript:
            summary = {
                "video_id": vid,
                "title": title,
                "has_transcript": False,
                "summary": None,
                "key_points": [],
                "error": "No transcript available",
            }
            summaries.append(summary)
            yield {"type": "transcript_error", "video_id": vid, "title": title}
            continue

        # Summarize with Claude
        yield {"type": "status", "content": f"Summarizing: {title}", "progress": i, "total": total}

        try:
            # Truncate very long transcripts
            max_chars = 30000
            truncated = transcript[:max_chars] + "..." if len(transcript) > max_chars else transcript

            resp = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": f"""Analyze this YouTube video transcript.

Video title: {title}
Channel: {channel_name}

Transcript:
{truncated}

Provide:
1. A concise summary (2-3 sentences)
2. 3-5 key points/takeaways as a JSON array of strings

Respond in this exact JSON format:
{{"summary": "...", "key_points": ["...", "..."]}}""",
                }],
            )

            raw = resp.content[0].text
            # Extract JSON from response
            parsed = _extract_json(raw)
            summary = {
                "video_id": vid,
                "title": title,
                "has_transcript": True,
                "summary": parsed.get("summary", raw),
                "key_points": parsed.get("key_points", []),
                "error": None,
            }
        except Exception as e:
            summary = {
                "video_id": vid,
                "title": title,
                "has_transcript": True,
                "summary": None,
                "key_points": [],
                "error": f"Summarization failed: {str(e)}",
            }

        summaries.append(summary)
        yield {"type": "video_summary", "data": summary}

    # Check if we have any summaries to cross-analyze
    valid_summaries = [s for s in summaries if s.get("summary")]
    if not valid_summaries:
        yield {"type": "error", "content": "No transcripts available for any selected video"}
        return

    # Cross-analysis with streaming
    yield {"type": "status", "content": "Running cross-video analysis...", "progress": total, "total": total}

    summaries_text = "\n\n".join(
        f"**{s['title']}**\n{s['summary']}\nKey points: {', '.join(s['key_points'])}"
        for s in valid_summaries
    )

    cross_analysis = ""
    try:
        with client.messages.stream(
            model=ANTHROPIC_MODEL,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": f"""You are a trend research analyst. Analyze these video summaries from the YouTube channel "{channel_name}" and identify patterns, themes, and opportunities.

{summaries_text}

Provide a structured analysis with:
1. **Common Themes** — recurring topics, formats, or strategies across videos
2. **Content Patterns** — how the creator structures content, hooks, storytelling
3. **Trending Opportunities** — gaps or angles we could leverage for our own content
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
        "channel_name": channel_name,
        "channel_url": channel_url,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "video_summaries": summaries,
        "cross_analysis": cross_analysis,
    }
    save_research(result)

    yield {"type": "complete", "id": research_id}


def _extract_json(text: str) -> dict:
    """Try to extract JSON from a Claude response that may have surrounding text."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from code block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try finding first { ... }
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {}


# ─── File persistence ─────────────────────────────────


def save_research(data: dict) -> Path:
    RESEARCH_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = RESEARCH_OUTPUT_DIR / f"{data['id']}.json"
    path.write_text(json.dumps(data, indent=2))
    return path


def load_research(research_id: str) -> dict | None:
    path = RESEARCH_OUTPUT_DIR / f"{research_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def list_research() -> list[dict]:
    RESEARCH_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for f in sorted(RESEARCH_OUTPUT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text())
            results.append({
                "id": data["id"],
                "channel_name": data["channel_name"],
                "created_at": data["created_at"],
                "video_count": len(data.get("video_summaries", [])),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return results
