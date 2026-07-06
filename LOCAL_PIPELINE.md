# OpenClaw — Local Operating Runbook

Last updated: 2026-07-06
Status: **CANONICAL.** This describes how the system runs now — locally, on demand,
with a Claude Code session in the loop. The older `PIPELINE.md` documents the retired
VPS automation and is kept only for deep reference (asset layout, ffmpeg internals,
hook rules).

---

## The model in one paragraph

The VPS is gone. There is no cron, no dispatcher, no always-on server, no email
delivery, and no Anthropic API key in the content path. The system is now a
**deterministic asset-cycler + ffmpeg stitcher** that a Claude Code session drives by
hand. When you name a persona, *I* (the session) write the hook / reaction / caption in
that persona's voice, pass them into `autopilot.py` as flags, and it stitches a reel to
`video_output/`. That file on disk is the deliverable — you add trending audio and post
it manually.

Why this shape: the old API call existed only because the VPS ran headless with no
human-Claude present. Locally, the model is already in the loop, so the script degrades
to pure Python + ffmpeg. Zero keys, zero external dependencies (except optional Drive
upload).

---

## The core loop — what I do each time you name a persona

1. **Read the voice.** `skills/personas/{persona}.md` for tone, plus
   `skills/content/hook-bank.md` (discovery) or `skills/content/fear-hooks.md` (fear
   angle) for proven patterns.
2. **Pick the angle.** Default is discovery (70%) vs fear (30%). I'll usually pick
   discovery unless you ask for fear. Force with `--angle discovery|fear`.
3. **Check dedup.** If the persona has a sibling account (e.g. `riley.manifests` ↔
   `riley.journals`), don't reuse the same hook the same day. Recent hooks live in
   `output/` and `memory/`.
4. **Write the text** — hook (POV), reaction, caption, hashtags — in the persona's
   voice. Guidance: hook ≈ 50 chars, reaction ≈ 40 chars (assemble_video.py word-wraps
   at ~28/line); caption is 2–3 casual first-person lines; never name the app; 5
   hashtags.
5. **Run the command** (below). It cycles in clips + the screen recording and stitches.
6. **Verify** the output with ffprobe (dimensions, duration, codec) and eyeball a frame
   if needed.
7. **Hand off** — report the file path. You add audio and post.

---

## The command

```bash
.venv/bin/python3 scripts/autopilot.py \
  --account <account> \
  --no-upload --no-email \
  --hook-text     "…" \
  --reaction-text "…" \
  --caption       "…" \
  --hashtags      "#a #b #c #d #e"
```

**Flags that make it key-free (added 2026-07-06):**

| Flag | Effect |
|------|--------|
| `--hook-text` / `--reaction-text` | Supply overlay text — skips the hook-generation API call |
| `--caption` / `--hashtags` | Supply caption — skips the *caption* API call. **Both text sets together = zero Anthropic calls.** |
| `--no-email` | Skip delivery; the `.mp4` on disk is the output (there are no SMTP creds locally) |
| `--no-upload` | Skip Google Drive upload (rclone not installed locally) |
| `--angle discovery\|fear` | Force the angle instead of weighted-random |
| `--hook-clip` / `--reaction-clip` | Pin specific clips instead of auto-cycling |
| `--dry-run` | Print the ffmpeg commands without writing the video (preview only) |

Omit `--caption`/`--hashtags` and it falls back to the API for the caption — which
needs a live `ANTHROPIC_API_KEY`. For the local flow, always supply all four text flags.

---

## Accounts

| `--account` | Persona | App | Priority |
|-------------|---------|-----|----------|
| `aliyah.manifests` | Aliyah | Manifest Lock | HIGH |
| `aliyah.journals`  | Aliyah | Journal Lock  | HIGH |
| `riley.manifests`  | Riley  | Manifest Lock | MEDIUM (breakout) |
| `riley.journals`   | Riley  | Journal Lock  | MEDIUM |
| `emillywilks`      | Emilly | Manifest Lock | MEDIUM |
| `sanyahealing`     | Sanya  | Journal Lock  | LOW |
| `sophie.unplugs`   | Sanya  | Journal Lock  | LOW (deprioritized, ~130 views) |

Content categories (the script picks weighted-random, or force with `--category`):
**A** Screen Time Shock (40%) · **B** Reaction/Story (30%) · **C** Streak/Transformation
(15%) · **D** App Demo (15%).

---

## Assets (real counts, 2026-07-06)

Clips are pre-made and reused — **no video generation**. Cycling avoids repeats within
7 days per account.

```
assets/{persona}/
  hook/            discovery hook clips   (aliyah 20 · riley 11 · sanya 14 · emilly 25)
  reaction/        discovery reaction clips (same counts)
  hook-fear/       fear-angle hook clip    (1 each — thin, fear angle reuses heavily)
  reaction-fear/   fear-angle reaction clip (1 each)
assets/screen-recordings/
  manifest-lock/   full-flow.mp4
  journal-lock/    full-flow.mp4
  autojournal/     autojournal-{food,friends,travel}.mov  (autojournal reels)
fonts/             Geist-Regular.otf, Geist-Bold.otf  (overlay fonts)
```

The stitch order is **hook → screen recording → reaction**, normalized to 1080×1920 @
30fps, audio stripped (trending sound added at post time). Output lands in
`video_output/` (gitignored — regenerated on demand).

---

## What is OFF now (was VPS-only)

- ❌ **cron / dispatcher / `config/schedule.json`** — no automated scheduling. Runs are
  manual.
- ❌ **email delivery** — no SMTP creds; use `--no-email`.
- ❌ **Google Drive upload** — `rclone` not installed; use `--no-upload`.
- ❌ **Anthropic API in the content path** — the session writes the text.
- ❌ **systemd (`openclaw-api`) / the VPS box** — retired. Never `ssh`/`systemctl` it.

The dashboard frontend still auto-deploys via Vercel on push to `main`. The dashboard
*backend* (FastAPI) is not running anywhere by default — start it locally only if you
want to browse the dashboard.

---

## Other local scripts

| Script | Purpose | Needs a key? |
|--------|---------|--------------|
| `scripts/autopilot.py` | The reel pipeline (above) | No (with the four text flags) |
| `scripts/lifestyle_reel.py` | 3-scene lifestyle reels (Ken Burns + screen rec) | Yes for auto text; supply `--scene-*-text` to skip |
| `scripts/autojournal_reel.py` | Autojournal-style reels from `autojournal/` recordings | same pattern |
| `scripts/scrape_reel_metrics.mjs` | Instagram metrics via Chrome CDP (port 9222) | No (browser-based, run locally) |
| `scripts/analyze_reel_performance.py` | Turns scraped metrics into performance files | `--no-llm` for stats-only, else needs key |
| `scripts/fetch_revenue_metrics.py` | RevenueCat MRR/trials → `logs/` + `memory/` | Uses `RC_*` keys in `.env` |

Same principle everywhere: anything that "calls Claude" has a `--*-text` or `--no-llm`
escape hatch so the session can supply the reasoning instead of the API.

---

## Re-enabling the optional pieces

- **Drive upload:** `brew install rclone` → `rclone config` (reconnect the `gdrive`
  remote → `manifest-social-videos/`) → drop `--no-upload`.
- **Email:** add `SMTP_USER` / `SMTP_PASS` / `DELIVERY_EMAIL` to `.env` → drop
  `--no-email`.
- **Dashboard chat / caption API:** put a live `ANTHROPIC_API_KEY` in `.env`.

---

## Fresh-machine setup

```bash
cd /Users/pranavambwani/openclaw
python3 -m venv .venv                       # if missing
.venv/bin/pip install -r requirements.txt   # anthropic, Pillow, dotenv, requests, replicate
brew install ffmpeg                          # required for stitching
```

---

## Troubleshooting (local)

| Symptom | Cause | Fix |
|---------|-------|-----|
| `No module named 'anthropic'` / `PIL` | venv not provisioned | `pip install -r requirements.txt` |
| `401 invalid x-api-key` | Fell back to the API path | Supply `--caption`/`--hashtags` so no API call happens (or add a live key) |
| `NO HOOK CLIPS` | Missing clips | Check `assets/{persona}/hook/` has `.mp4`s |
| Text overlay not visible | Font missing | Ensure `fonts/Geist-*.otf` exist |
| `rclone: command not found` | Not installed | Use `--no-upload`, or install + reconnect |
| No `.mp4` written | Ran with `--dry-run` | Drop `--dry-run` for a real render |
```
