---
name: journal-lock
description: Product knowledge for Journal Lock iOS app. Features, value props, target audience, mascot system. Reference when generating content for @sanyahealing and @sophie.unplugs.
related: [manifest-lock, sanya, hook-architecture, content-mix, text-overlays]
---

# Journal Lock — Product Knowledge

## What It Is

An iOS app that blocks distracting apps until users write a daily journal entry. Features a block-based editor (text, drawing, images), a kawaii sprout mascot ("Sprout") that grows when users journal and shrinks when they skip, and AI-generated prompts and titles. Apps stay locked until the user journals each day.

## Core Value Propositions (ranked by hook potential)

1. **"Your apps are locked until you journal"** — the core mechanic. This is the only journaling app that forces you to write before you can scroll. Lead with this in [[hook-architecture]] Tier 1 and Tier 2 hooks.
2. **"There's a little plant on your phone that dies when you don't journal"** — root emotional hook. Mascot shrinks visibly when you skip days, grows when you're consistent. Best for character-driven content and [[content-mix]] Category A (mascot/meme).
3. **"5 minutes of writing replaces 3 hours of doom scrolling"** — time swap framing. Works especially well for [[text-overlays]] POV openers.
4. **"Your phone guilt-trips you with a tiny plant"** — the visceral, slightly unhinged description. Best for curiosity-gap hooks and TikTok native tone.
5. **"Build a streak that literally levels up your mascot"** — gamification angle. HP system (+2 per journal day, -1 per missed day), leveling every 100 HP. Best for [[content-mix]] Category C (streak/transformation).
6. **"AI writes your journal prompt based on your mood"** — tech angle. Use sparingly, mostly for Category D (app demo).

## Mascot: Sprout

Sprout is the emotional core of the app and the primary content vehicle. A kawaii green sprout character with multiple mood states.

### Available Moods (for content)
- **Normal** — happy face
- **Cool** — sunglasses, confident energy
- **Surprised** — wide eyes, open mouth
- **Meditating** — zen, peaceful
- **Breathing** — calm, focused
- **Writing** — journaling pose (used in entry share images)
- **Samurai** — warrior mode (used in streak share images)
- **Worried** — anxiety, concern
- **Dreaming** — aspirational, sleepy
- **Strong** — flexing, powerful
- **Phone** — holding phone (screen time context)
- **Lock** — security/blocking context

### HP System (Content-Relevant)
- +2 HP per day journaled, -1 HP per missed day
- Every 100 HP = new level
- Sprout physically shrinks as HP drops (scales from 1.0 to 0.2)
- Push notification when Sprout hits minimum: "Your mascot needs you!"
- Level-ups and streak milestones are shareable as images

### Content Rules for Sprout
- Sprout is NOT the user's pet — Sprout is a character with its own personality
- Sprout has opinions about your screen time (judgmental, but lovable)
- Sprout's suffering when neglected = comedic
- Sprout celebrations are over-the-top (samurai mode for streaks)

## Persona

All JournalLock content is posted by [[sanya]] (2 accounts: @sanyahealing, @sophie.unplugs). Sanya's dry, grounded, skeptic-turned-believer voice is the lens through which this app is presented. Sprout is a recurring "character" in Sanya's content — she talks about Sprout like a needy roommate.

## Target Audience

### Primary: The Doom Scroller (18-28)
Knows they waste hours on their phone, feels guilty about it but can't stop. Hook angle: screen time stats, "what if you journaled instead of scrolling for 3 hours," guilt humor.

### Secondary: The Journaling Quitter (22-35)
Has tried journaling before — bought the Moleskine, downloaded Day One — but never stuck with it. Hook angle: "this app literally won't let you skip," accountability framing, streak gamification.

### Tertiary: The Self-Improver (25-40)
Wants intentional mornings and routines, interested in mental wellness. Hook angle: productivity, habit building, Sprout as companion. Sanya's warm, relatable energy fits this audience.

## App Features (Content-Relevant)

Use these in screen recordings and [[text-overlays]] reaction moments:

- **Block-based journal editor** — text + drawing + image blocks (Notion-style). Visually rich, shareable entries
- **AI daily prompts** — personalized based on user context, shown above editor. Good for "look at what my app asked me today" content
- **AI auto-generated titles** — triggers after 15+ words, editable. Subtle "wow" moment for demos
- **Mood check** (emoji slider) — visually appealing, shows the practice is personalized
- **App blocking with shield overlay** — the "earn your screen time" mechanic, the money shot for demos
- **Sprout mascot with HP system** — grows/shrinks based on consistency, the emotional hook for all character content
- **Streak tracking with celebrations** — StreakCelebrationView after saving, shareable milestone images (Day 3, 7, 14, 30, 60, 100)
- **Level-up system** — every 100 HP = new level, shareable level cards with samurai Sprout
- **Drawing blocks** — PencilKit canvas for doodles/sketches inside entries. Visual differentiator from text-only journal apps
- **Unlock countdown timer** — visual urgency when apps are temporarily unlocked, good for reaction moments
- **Share images** — streak share (samurai Sprout + streak count), entry share (writing Sprout + entry preview), level share (samurai Sprout + HP progress). All screenshot-worthy with gradient backgrounds and sparkle dots

## Key Differentiators vs Manifest Lock

| | Journal Lock | Manifest Lock |
|---|---|---|
| Core practice | Freeform journaling (text/draw/image) | Manifestation writing + read aloud |
| Mascot | Sprout (HP system, grows/shrinks) | None |
| Editor | Block-based (Notion-style) | Single text field |
| AI features | Prompts + auto-titles | Mood-based affirmation generation |
| Audio component | None (keyboard dictation available) | Read aloud with audio visualizer |
| Gamification | HP, levels, streak celebrations, shareable cards | Streak tracking |
| Visual identity | Kawaii green/nature theme | Cosmic/aurora theme |

When creating content, lean into what Journal Lock has that Manifest Lock doesn't: **Sprout is the star.** The mascot system is the primary content differentiator and the reason people share.

## What We Never Say

- Never claim journaling will cure anxiety, depression, or any medical condition — see [[what-never-works]]
- Never directly ask people to download — see [[tiktok]] "never name the app" rule
- Never frame Sprout dying/shrinking as genuinely distressing — keep it comedic
- Credible claims only: reduced screen time, built a journaling habit, felt more intentional, kept a streak going, Sprout is thriving
- Never say "journal lock" unprompted in video captions — let comments ask "what app is this?"
