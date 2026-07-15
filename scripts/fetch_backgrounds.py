#!/usr/bin/env python3
"""Fetch candidate carousel backgrounds from Pexels into an inbox for curation.

Needs PEXELS_API_KEY in .env (free: pexels.com/api — 200 req/hr).
Run from repo root:
    .venv/bin/python3 scripts/fetch_backgrounds.py

Downloads portrait photos per query into assets/carousel-backgrounds/_inbox/
and records photographer + source URL in sources.jsonl (license bookkeeping).
Curation happens after: keep ~40 on-aesthetic images, sorted into
{desk,cafe,bed,flatlay,props}/ with a manifest of text-safe zones.
"""

import json
import os
import urllib.request

QUERIES = [
    "journal notebook flatlay",
    "open notebook coffee aesthetic",
    "matcha latte desk",
    "cozy bed morning light book",
    "pastel stationery flatlay",
    "handwritten notebook pen",
    "cafe table latte art",
    "diary writing hands cozy",
    "candle notebook evening cozy",
    "planner stickers cute desk",
    "tea cup book blanket",
    "minimal desk notebook plant",
]

PER_QUERY = 10
INBOX = "assets/carousel-backgrounds/_inbox"


def env_key():
    for line in open(".env"):
        if line.startswith("PEXELS_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("PEXELS_API_KEY not found in .env — grab a free key at pexels.com/api")


UA = "OpenClaw/1.0 (carousel background curation)"


def get(url, key=None):
    headers = {"User-Agent": UA}
    if key:
        headers["Authorization"] = key
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers))


def fetch(query, key, log):
    q = urllib.parse.quote(query)
    url = (f"https://api.pexels.com/v1/search?query={q}"
           f"&orientation=portrait&size=large&per_page={PER_QUERY}")
    data = json.load(get(url, key))
    n = 0
    for photo in data.get("photos", []):
        src = photo["src"].get("large2x") or photo["src"]["original"]
        slug = query.replace(" ", "-")
        out = f"{INBOX}/{slug}_{photo['id']}.jpg"
        if os.path.exists(out):
            continue
        with open(out, "wb") as fh:
            fh.write(get(src).read())
        log.write(json.dumps({
            "file": os.path.basename(out), "query": query,
            "photographer": photo["photographer"], "url": photo["url"],
            "source": "pexels",
        }) + "\n")
        n += 1
    return n


if __name__ == "__main__":
    import urllib.parse
    key = env_key()
    os.makedirs(INBOX, exist_ok=True)
    total = 0
    with open(f"{INBOX}/sources.jsonl", "a") as log:
        for q in QUERIES:
            n = fetch(q, key, log)
            total += n
            print(f"{q}: {n} downloaded")
    print(f"\n{total} candidates in {INBOX} — ready for curation pass")
