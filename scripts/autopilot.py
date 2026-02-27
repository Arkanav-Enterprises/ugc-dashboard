#!/usr/bin/env python3
"""
autopilot.py — Generate daily content for 3 social accounts.

Reads the skill graph, calls Anthropic to generate text overlays + captions,
selects pre-made assets via cycling logic, and delivers via email.

Usage:
    python3 autopilot.py --account sophie.unplugs
    python3 autopilot.py --account emillywilks --category A
    python3 autopilot.py --account sanyahealing --dry-run
    python3 autopilot.py                          # All 3 accounts
    python3 autopilot.py --idea-only              # Print text, skip email
"""

import os
import sys
import json
import random
import smtplib
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ---------------------------------------------------------------------------
# Config — state lives in one place
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = PROJECT_ROOT / "skills"
MEMORY_DIR = PROJECT_ROOT / "memory"
ASSETS_DIR = PROJECT_ROOT / "assets"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOGS_DIR = PROJECT_ROOT / "logs"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
VIDEO_OUTPUT_DIR = PROJECT_ROOT / "video_output"

# Account → persona → app mapping (single source of truth)
# Priority order: Aliyah > Riley > Sanya > Sophie (based on per-reel performance)
ACCOUNTS = {
    # Aliyah — top performer, ~800 views/reel on ManifestLock, ~450 on JournalLock
    "aliyah.manifests": {"persona": "aliyah", "app": "manifest-lock", "handle": "@aliyah.manifests"},
    "aliyah.journals":  {"persona": "aliyah", "app": "journal-lock",  "handle": "@aliyah.journals"},
    # Riley — breakout potential, spiky distribution (1,144-view hit with only 6 reels)
    "riley.manifests":  {"persona": "riley",  "app": "manifest-lock", "handle": "@riley.manifests"},
    "riley.journals":   {"persona": "riley",  "app": "journal-lock",  "handle": "@riley.journals"},
    # Sanya avatar — used across 3 accounts
    "sanyahealing":     {"persona": "sanya",  "app": "journal-lock",  "handle": "@sanyahealing"},
    "sophie.unplugs":   {"persona": "sanya",  "app": "journal-lock",  "handle": "@sophie.unplugs"},
    "emillywilks":      {"persona": "sanya",  "app": "manifest-lock", "handle": "@emillywilks"},
}

# Category weights — 40/30/15/15 split
CATEGORIES = {
    "A": {"name": "Screen Time Shock", "weight": 40},
    "B": {"name": "Reaction/Story Hook", "weight": 30},
    "C": {"name": "Streak/Transformation", "weight": 15},
    "D": {"name": "App Demo", "weight": 15},
}

# Email config from env
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
RECIPIENT = os.environ.get("DELIVERY_EMAIL", "")


# ---------------------------------------------------------------------------
# Skill graph reader — load only what's needed
# ---------------------------------------------------------------------------

def read_skill(relative_path: str) -> str:
    """Read a skill file from the graph. Returns content or empty string."""
    path = SKILLS_DIR / relative_path
    if path.exists():
        return path.read_text()
    print(f"  WARN: Skill not found: {path}")
    return ""


def load_memory_file(filename: str) -> str:
    """Read a memory file. Returns content or empty string."""
    path = MEMORY_DIR / filename
    if path.exists():
        return path.read_text()
    return ""


def load_context_for_account(account: str) -> str:
    """Build the Anthropic system prompt from relevant skill graph nodes + memory."""
    cfg = ACCOUNTS[account]
    persona = cfg["persona"]
    app = cfg["app"]

    # Traversal order matches pipeline.md specification
    skills = [
        ("INDEX.md",                      "Landscape overview"),
        (f"{app}.md",                     "Product knowledge"),
        (f"personas/{persona}.md",        "Persona voice"),
        ("content/content-mix.md",        "Category ratios"),
        ("content/hook-architecture.md",  "Hook formulas"),
        ("content/text-overlays.md",      "Text overlay patterns"),
        ("content/caption-formulas.md",   "Caption structures"),
        ("content/what-never-works.md",   "Anti-patterns"),
        ("analytics/proven-hooks.md",     "Proven winners"),
        ("content/hook-bank.md",          "Hook bank — draw from these"),
    ]

    parts = []
    for filepath, label in skills:
        content = read_skill(filepath)
        if content:
            parts.append(f"--- {label} ({filepath}) ---\n{content}")

    # Load memory files for performance signal
    for mem_file, label in [
        ("post-performance.md", "Performance data — what works and what doesn't"),
        ("failure-log.md", "Failure log — rules that must not be broken"),
    ]:
        content = load_memory_file(mem_file)
        if content:
            parts.append(f"--- {label} (memory/{mem_file}) ---\n{content}")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Category selection — weighted random
# ---------------------------------------------------------------------------

def pick_category(forced: str | None = None) -> str:
    """Pick a content category. Respects forced override."""
    if forced and forced.upper() in CATEGORIES:
        return forced.upper()

    pool = []
    for cat, info in CATEGORIES.items():
        pool.extend([cat] * info["weight"])
    return random.choice(pool)


# ---------------------------------------------------------------------------
# Asset selection — cycling with memory
# ---------------------------------------------------------------------------

def load_asset_usage() -> dict:
    """Load recent asset usage from memory file."""
    path = MEMORY_DIR / "asset-usage.md"
    if not path.exists():
        return {"entries": []}

    entries = []
    for line in path.read_text().splitlines():
        if line.startswith("|") and not line.startswith("| Date") and not line.startswith("|---"):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 5:
                entries.append({
                    "date": parts[0], "account": parts[1],
                    "hook": parts[2], "reaction": parts[3], "screen_rec": parts[4],
                })
    return {"entries": entries}


def save_asset_usage(usage: dict):
    """Save updated asset usage back to memory file."""
    path = MEMORY_DIR / "asset-usage.md"
    lines = ["## Recent Asset Usage\n",
             "| Date | Account | Hook Clip | Reaction Clip | Screen Recording |",
             "|------|---------|-----------|---------------|-----------------|"]
    for e in usage["entries"][-30:]:  # keep last 30 entries
        lines.append(f"| {e['date']} | {e['account']} | {e['hook']} | {e['reaction']} | {e['screen_rec']} |")
    path.write_text("\n".join(lines) + "\n")


def list_assets(persona: str, clip_type: str) -> list[str]:
    """List available clips for a persona. Returns filenames sorted."""
    folder = ASSETS_DIR / persona / clip_type
    if not folder.exists():
        return []
    return sorted([f.name for f in folder.iterdir() if f.suffix in (".mp4", ".mov")])


def list_screen_recordings(app: str) -> list[str]:
    """List available screen recordings for a specific app."""
    folder = ASSETS_DIR / "screen-recordings" / app
    if not folder.exists():
        return []
    return sorted([f.name for f in folder.iterdir() if f.suffix in (".mp4", ".mov")])


def pick_clip_pair(persona: str, usage: dict, account: str) -> tuple[str, str]:
    """Pick a matched hook+reaction pair (same filename = same session).

    Returns (hook_filename, reaction_filename). Falls back to independent
    picks only if no matched pairs exist.
    """
    hooks = list_assets(persona, "hook")
    reactions = list_assets(persona, "reaction")

    if not hooks:
        return (f"[NO HOOK CLIPS in assets/{persona}/hook/]",
                f"[NO REACTION CLIPS in assets/{persona}/reaction/]")
    if not reactions:
        return (random.choice(hooks),
                f"[NO REACTION CLIPS in assets/{persona}/reaction/]")

    # Find filenames that exist in both hook/ and reaction/
    matched = sorted(set(hooks) & set(reactions))

    if not matched:
        # No matching filenames — fall back to independent picks (shouldn't happen)
        return (random.choice(hooks), random.choice(reactions))

    # Recently used pairs by this account
    recent = {e["hook"] for e in usage["entries"][-7:] if e["account"] == account}

    # Prefer unused pairs
    unused = [m for m in matched if m not in recent]
    pick = random.choice(unused) if unused else random.choice(matched)
    return (pick, pick)


def pick_screen_recording(app: str, usage: dict, account: str) -> str:
    """Pick a screen recording for the correct app, not recently used by this account."""
    available = list_screen_recordings(app)
    if not available:
        return f"[NO SCREEN RECORDINGS in assets/screen-recordings/{app}/]"

    recent = {e["screen_rec"] for e in usage["entries"][-7:] if e["account"] == account}
    unused = [a for a in available if a not in recent]
    return random.choice(unused) if unused else random.choice(available)


# ---------------------------------------------------------------------------
# Content generation — Anthropic API call
# ---------------------------------------------------------------------------

def generate_content(account: str, category: str, context: str, dedup_hooks: list[str]) -> dict:
    """Call Anthropic API to generate text overlays + caption."""
    import anthropic

    cfg = ACCOUNTS[account]
    cat_name = CATEGORIES[category]["name"]

    # Build dedup instruction if sophie's second account
    dedup_note = ""
    if dedup_hooks:
        dedup_note = (
            f"\n\nIMPORTANT — These hooks were already generated today for the same persona's "
            f"other account. Your hook MUST be completely different:\n"
            + "\n".join(f"- {h}" for h in dedup_hooks)
        )

    user_prompt = f"""Generate content for: {cfg['handle']}
Persona: {cfg['persona']}
App: {cfg['app']}
Content Category: {category} ({cat_name})
Date: {date.today().isoformat()}
{dedup_note}

HARD RULES (from failure-log — violating these kills performance):
1. ONLY default clothing/setting. Never reference outdoor, UGC lighting, or studio setups.
2. Use PHONE PERSONIFICATION hooks ("my phone won't...", "my phone guilt trips me...") — these outperform by 3-8x.
3. Include SPECIFIC SOCIAL CONTEXT (boyfriend, boss, therapist, sister, co-worker, roommate) — adds a person to create a mini-story.
4. Include EMOTIONAL ESCALATION (guilt, shame, surprise) — pure feature-description hooks get ignored.
5. Never repeat the same hook structure used recently on this account. Check the proven-hooks and hook-bank files.
6. Draw from or riff on the hook-bank.md patterns. Vary the specific details but keep the winning structures.

Generate exactly this JSON (no markdown fencing):
{{
  "pov_text": "the POV text overlay for Part 1 (the hook)",
  "reaction_text": "the reaction text overlay for Part 3 (the payoff)",
  "suggested_screen_recording": "which type of screen recording fits best (e.g., stats-screen, full-practice, app-blocking, streak-celebration, unlock-countdown)",
  "caption": "the full post caption with line breaks",
  "hashtags": "#tag1 #tag2 #tag3 #tag4 #tag5"
}}

Follow ALL rules from the skill files. The hook must pass the 3-second test.
Never mention the app name in the POV text or caption.
First person, authentic voice matching the persona."""

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=800,
        system=f"You are the content engine for a social media marketing pipeline. "
               f"Generate content strictly following the rules in these skill files:\n\n{context}",
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = response.content[0].text.strip()
    # Strip markdown fences if model adds them despite instruction
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    return _parse_json(raw)


def _parse_json(raw: str) -> dict:
    """Parse JSON from model output, repairing common issues."""
    import re

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Fix 1: unescaped newlines inside string values — replace with \\n
    repaired = re.sub(
        r'(?<=": ")(.*?)(?="(?:,|\s*\}))',
        lambda m: m.group(0).replace("\n", "\\n"),
        raw,
        flags=re.DOTALL,
    )
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Fix 2: extract fields individually with regex as last resort
    fields = {}
    for key in ("pov_text", "reaction_text", "suggested_screen_recording", "caption", "hashtags"):
        match = re.search(rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"', raw, re.DOTALL)
        if match:
            fields[key] = match.group(1).replace("\\n", "\n").replace('\\"', '"')

    if "pov_text" in fields and "reaction_text" in fields:
        # Fill defaults for optional fields
        fields.setdefault("suggested_screen_recording", "any")
        fields.setdefault("caption", "")
        fields.setdefault("hashtags", "")
        return fields

    raise json.JSONDecodeError(f"Could not parse model output", raw, 0)


# ---------------------------------------------------------------------------
# Deduplication — check what was generated earlier today
# ---------------------------------------------------------------------------

def load_today_output(account: str) -> dict | None:
    """Load today's output for an account if it exists."""
    today = date.today().isoformat()
    path = OUTPUT_DIR / f"{today}_{account}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def save_output(account: str, result: dict):
    """Save generated content for dedup and records."""
    today = date.today().isoformat()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{today}_{account}.json"
    path.write_text(json.dumps(result, indent=2))


# ---------------------------------------------------------------------------
# Email delivery — plain text, no attachments
# ---------------------------------------------------------------------------

def send_email(subject: str, body: str):
    """Send content email. Fails gracefully with error message."""
    if not all([SMTP_USER, SMTP_PASS, RECIPIENT]):
        print("  SKIP EMAIL: Set SMTP_USER, SMTP_PASS, DELIVERY_EMAIL env vars")
        return False

    recipients = [r.strip() for r in RECIPIENT.split(",") if r.strip()]

    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, recipients, msg.as_string())
        print(f"  Email sent to {', '.join(recipients)}")
        return True
    except Exception as e:
        print(f"  EMAIL ERROR: {e}")
        return False


# ---------------------------------------------------------------------------
# Video assembly — stitch clips + upload to Google Drive
# ---------------------------------------------------------------------------

def assemble_reel(account: str, content: dict, assets: dict,
                  dry_run: bool = False, no_upload: bool = False,
                  no_reaction: bool = False) -> str | None:
    """Assemble the final reel via assemble_video.py and optionally upload to Drive.

    Returns the reel file path on success, or None on failure.
    """
    cfg = ACCOUNTS[account]
    persona = cfg["persona"]
    app = cfg["app"]

    # Resolve full asset paths
    hook_path = ASSETS_DIR / persona / "hook" / assets["hook"]
    screen_path = ASSETS_DIR / "screen-recordings" / app / assets["screen_rec"]

    # Check required assets exist
    required = [("Hook", hook_path), ("Screen", screen_path)]
    if not no_reaction:
        reaction_path = ASSETS_DIR / persona / "reaction" / assets["reaction"]
        required.append(("Reaction", reaction_path))

    for label, path in required:
        if not path.exists():
            print(f"  SKIP ASSEMBLY: {label} clip not found: {path}")
            return None

    # Output filename
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    VIDEO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = VIDEO_OUTPUT_DIR / f"reel_{ts}_{account}.mp4"

    # Build command
    cmd = [
        sys.executable, str(SCRIPTS_DIR / "assemble_video.py"),
        "--hook-clip", str(hook_path),
        "--screen-recording", str(screen_path),
        "--hook-text", content["pov_text"],
        "--output", str(output_path),
    ]
    if not no_reaction:
        cmd += ["--reaction-clip", str(reaction_path),
                "--reaction-text", content["reaction_text"]]
    if no_upload:
        cmd.append("--no-upload")
    if dry_run:
        cmd.append("--dry-run")

    print(f"  Assembling reel...")
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout for ffmpeg
        )
        # Print assembly output
        for line in result.stdout.splitlines():
            print(f"    {line}")
        if result.stderr:
            for line in result.stderr.splitlines():
                print(f"    ERR: {line}")

        if result.returncode != 0:
            print(f"  ASSEMBLY FAILED (exit code {result.returncode})")
            return None

        # Parse output for reel path
        for line in result.stdout.splitlines():
            if "Reel assembled:" in line:
                # Line format: "✅ Reel assembled: /path/to/reel.mp4 (X.X MB)"
                path_part = line.split("Reel assembled:")[1].strip()
                reel_path = path_part.split("(")[0].strip()
                print(f"  Reel: {reel_path}")
                return reel_path

        # If dry run, no "Reel assembled" line — return the intended output path
        if dry_run:
            print(f"  [DRY RUN] Would assemble: {output_path}")
            return str(output_path)

        # Fallback: check if output file exists
        if output_path.exists():
            print(f"  Reel: {output_path}")
            return str(output_path)

        print("  ASSEMBLY WARNING: No reel path found in output")
        return None

    except subprocess.TimeoutExpired:
        print("  ASSEMBLY FAILED: Timed out after 5 minutes")
        return None
    except Exception as e:
        print(f"  ASSEMBLY ERROR: {e}")
        return None


# ---------------------------------------------------------------------------
# Format email body — what you see on your phone
# ---------------------------------------------------------------------------

def format_email(account: str, category: str, content: dict, assets: dict,
                 reel_path: str | None = None) -> tuple[str, str]:
    """Return (subject, body) for the delivery email."""
    cfg = ACCOUNTS[account]
    cat_name = CATEGORIES[category]["name"]
    pov_preview = content["pov_text"][:50]

    subject = f"[{cfg['persona'].title()}] {cfg['handle']} Cat-{category}: \"{pov_preview}\""

    app_label = "MANIFEST LOCK" if cfg["app"] == "manifest-lock" else "JOURNAL LOCK"

    reel_section = ""
    if reel_path:
        reel_section = f"""
━━━ REEL ━━━

Reel: {reel_path}
Google Drive: manifest-social-videos/
"""

    body = f"""{app_label} — Daily Content
Persona: {cfg['persona'].title()} ({cfg['handle']})
Category: {category} ({cat_name})
Date: {date.today().isoformat()}

━━━ TEXT OVERLAYS ━━━

POV (Part 1): {content['pov_text']}

Reaction (Part 3): {content['reaction_text']}

━━━ CAPTION ━━━

{content['caption']}

{content['hashtags']}

━━━ ASSETS ━━━

Hook clip: {cfg['persona']}/hook/{assets['hook']}
Reaction clip: {cfg['persona']}/reaction/{assets['reaction']}
Screen recording: screen-recordings/{cfg['app']}/{assets['screen_rec']}
Suggested type: {content.get('suggested_screen_recording', 'any')}
{reel_section}
━━━ POSTING NOTES ━━━

- Add trending sound before publishing
- Post to TikTok first, then IG Reels (swap hashtags)
- Never mention "{app_label.replace(' ', '')}" by name in comments
- Reply to "what app?" comments individually
"""
    return subject, body


# ---------------------------------------------------------------------------
# Main — the training loop: generate → select → deliver → record
# ---------------------------------------------------------------------------

def run_account(account: str, category_override: str | None = None,
                dry_run: bool = False, idea_only: bool = False,
                no_upload: bool = False, no_reaction: bool = False):
    """Generate content for one account."""
    cfg = ACCOUNTS[account]
    print(f"\n{'='*60}")
    print(f"Generating for {cfg['handle']} ({cfg['persona']}, {cfg['app']})")
    print(f"{'='*60}")

    # 1. Pick category
    category = pick_category(category_override)
    print(f"  Category: {category} ({CATEGORIES[category]['name']})")

    # 2. Load skill graph context
    print("  Loading skill graph...")
    context = load_context_for_account(account)

    # 3. Check dedup (personas with two accounts must not duplicate hooks)
    dedup_hooks = []
    dedup_pairs = {
        "sanyahealing": "sophie.unplugs",
        "sophie.unplugs": "sanyahealing",
        "aliyah.journals": "aliyah.manifests",
        "aliyah.manifests": "aliyah.journals",
        "riley.journals": "riley.manifests",
        "riley.manifests": "riley.journals",
    }
    if account in dedup_pairs:
        sibling = dedup_pairs[account]
        sibling_output = load_today_output(sibling)
        if sibling_output:
            dedup_hooks = [sibling_output["content"]["pov_text"]]
            print(f"  Dedup: avoiding hook from @{sibling}")

    # 4. Generate text via Anthropic
    print("  Calling Anthropic API...")
    try:
        content = generate_content(account, category, context, dedup_hooks)
    except Exception as e:
        print(f"  ERROR generating content: {e}")
        # Retry once on transient errors (529s)
        if "529" in str(e) or "overloaded" in str(e).lower():
            print("  Retrying in 30s (server overload)...")
            import time
            time.sleep(30)
            content = generate_content(account, category, context, dedup_hooks)
        else:
            raise

    print(f"  POV: {content['pov_text']}")
    print(f"  Reaction: {content['reaction_text']}")

    if idea_only:
        print(f"\n  Caption:\n  {content['caption']}")
        print(f"  {content['hashtags']}")
        return

    # 5. Select assets (cycling) — hook+reaction as matched pair
    print("  Selecting assets...")
    usage = load_asset_usage()
    hook_clip, reaction_clip = pick_clip_pair(cfg["persona"], usage, account)
    assets = {
        "hook": hook_clip,
        "reaction": reaction_clip,
        "screen_rec": pick_screen_recording(cfg["app"], usage, account),
    }
    print(f"  Hook: {assets['hook']}, Reaction: {assets['reaction']}, Screen: {assets['screen_rec']}")

    # 6. Record asset usage
    usage["entries"].append({
        "date": date.today().isoformat(),
        "account": account,
        "hook": assets["hook"],
        "reaction": assets["reaction"],
        "screen_rec": assets["screen_rec"],
    })
    save_asset_usage(usage)

    # 7. Save output for dedup
    save_output(account, {"category": category, "content": content, "assets": assets})

    # 8. Assemble reel
    reel_path = assemble_reel(account, content, assets,
                              dry_run=dry_run, no_upload=no_upload,
                              no_reaction=no_reaction)

    # 9. Deliver
    subject, body = format_email(account, category, content, assets,
                                 reel_path=reel_path)

    if dry_run:
        print(f"\n  --- DRY RUN (no email) ---")
        print(f"  Subject: {subject}")
        print(f"\n{body}")
    else:
        send_email(subject, body)

    print(f"  Done.")


def main():
    parser = argparse.ArgumentParser(description="Generate daily content for social accounts")
    parser.add_argument("--account", choices=list(ACCOUNTS.keys()),
                        help="Generate for one account (default: all 3)")
    parser.add_argument("--category", choices=list(CATEGORIES.keys()),
                        help="Force a content category")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate content but don't send email")
    parser.add_argument("--idea-only", action="store_true",
                        help="Generate text only, skip asset selection and email")
    parser.add_argument("--no-upload", action="store_true",
                        help="Assemble reel but skip Google Drive upload")
    parser.add_argument("--no-reaction", action="store_true",
                        help="Skip reaction clip in video assembly (hook + screen only)")
    args = parser.parse_args()

    accounts = [args.account] if args.account else list(ACCOUNTS.keys())

    for account in accounts:
        run_account(account, args.category, args.dry_run, args.idea_only,
                    args.no_upload, args.no_reaction)

    print(f"\nAll done. {len(accounts)} account(s) processed.")


if __name__ == "__main__":
    main()
