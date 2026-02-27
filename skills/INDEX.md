---
name: manifest-lock-content-graph
description: Entry point for the social content generation system. Two apps (ManifestLock, JournalLock), three personas (Aliyah, Riley, Sanya, Emilly), seven accounts. Agent reads this first, then traverses relevant nodes.
---

# Content Skill Graph

This graph teaches an AI content engine how to generate viral social media content for two iOS apps that lock distracting apps until users complete a daily practice.

The system generates **text overlays and captions** for UGC-style reaction videos posted by two avatar personas across three accounts.

## How to Use This Graph

1. Read this index to understand the landscape
2. For any generation task, identify: **which account** → which persona → which app
3. Follow the [[wikilinks]] into only the nodes you need
4. Each node is self-contained — you don't need to read the whole graph for any single task

## Account Map

| Account | Persona | App | Posts/Day |
|---------|---------|-----|-----------|
| @sanyahealing | Sanya | JournalLock | 1 |
| @sophie.unplugs | Sanya | JournalLock | 1 |
| @emillywilks | Emilly | ManifestLock | 1 |

**Total: 3 posts/day.** Sanya's two accounts must have different content each day.

## The Products

Two apps, same core mechanic (lock apps until daily practice), different practices:

- [[manifest-lock]] — locks apps until users read manifestations aloud. Promoted by Emilly on @emillywilks. Morning routine energy.
- [[journal-lock]] — locks apps until users journal for the day. Promoted by Sanya on @sanyahealing and @sophie.unplugs. Late-night overthinking energy.

Read the relevant product file before generating content to ensure accurate feature references and credible claims.

## The Personas

Two avatar personas with distinct looks and voices. Each persona is locked to one app:

- [[sanya]] — dark hair, band tee, outdoor park. Dry, grounded, skeptic-turned-believer. Runs 2 JournalLock accounts (@sanyahealing, @sophie.unplugs).
- [[emilly]] — brunette, red sweatshirt, cozy room. Warm, vulnerable, overthinker. Runs 1 ManifestLock account (@emillywilks).

Read the persona file before generating content — the hook must feel like something *that person* would actually say.

## Content Generation

The core knowledge for creating posts. Start with [[content-mix]] to understand category ratios, then follow into the specific node:

- [[content-mix]] — the weekly balance of content categories (A through D) and when to use each. This is the strategic layer that decides *what kind* of post to make.
- [[hook-architecture]] — the formulas, quality rules, and self-check process for hooks. The most critical node in the graph. A bad hook kills everything downstream.
- [[text-overlays]] — specific patterns for the POV opening text and reaction text that appear on the video clips.
- [[caption-formulas]] — structures for the post caption. Includes CTA patterns, hashtag rules, and persona-specific tone.
- [[what-never-works]] — anti-patterns, banned phrases, and content that consistently fails. Final check before approving content.

## Visual Format

How the actual videos are structured and how assets rotate:

- [[video-format]] — the 3-part structure of every post (persona clip → screen recording → reaction clip), text overlay placement, and timing.
- [[asset-cycling]] — how to select and rotate through pre-made video assets without repeating.

## Platform Rules

Each platform has specific tactics that affect how we write and format:

- [[tiktok]] — posting rules, algorithm signals, hashtag strategy, the "never name the app" rule, and the 500-view floor.
- [[instagram]] — Reels-specific differences, hashtag limits, save/share optimization.
- [[account-warmup]] — the Day 1-2 protocol for new accounts before posting begins.

## Performance & Analytics

The feedback loop that makes the system smarter over time:

- [[performance-loop]] — how to track what works, the weekly review process, and how performance data feeds back into content decisions.
- [[proven-hooks]] — a living document of hooks that actually performed. Updated after each review cycle.

## Operations

How the automated pipeline works:

- [[pipeline]] — end-to-end architecture of the generation and delivery system, cron schedule, email delivery format, and manual posting workflow.
