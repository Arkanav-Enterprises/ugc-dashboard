"""JournalLock brand-page carousel content.

One brand voice (warm, calm, lightly playful — never preachy). Three sample
carousels, one per template family. Rendered by carousel.py.

Hooks follow carousel-hook-bank patterns; prompts are the sendable payload.
"""

SCENES = "assets/lifestyle-images/journal-lock"   # AI scenes (legacy)
BG = "assets/carousel-backgrounds"                 # curated Pexels library

CAROUSELS = [
    # ---------- T1: Notes screenshots (send machine) ----------
    {
        "slug": "t1-notes-mind-wont-quiet",
        "slides": [
            {"kind": "notes_cover",
             "bg": f"{BG}/bed/cozy-bed-morning-light-book_10060922.jpg",
             "quote": "“i want to journal but i never know what to write.”",
             "sub": "so i saved these. swipe →"},
            {"kind": "notes", "date": "July 12, 2026 at 11:47 PM",
             "title": "Brain dump prompts", "emoji": "\U0001F4DD\U0001F4AD",
             "prompts": [
                 "What has been stuck in your head today?",
                 "Why do you think you can't stop thinking about it?",
                 "What are you pretending isn't bothering you?",
                 "Is there anything you've been avoiding? Why?",
                 "Write it all down. Does your head feel lighter?",
             ]},
            {"kind": "notes", "date": "July 12, 2026 at 11:52 PM",
             "title": "Overthinking prompts", "emoji": "\U0001F32A\U0000FE0F",
             "prompts": [
                 "Is this a fact, or a fear?",
                 "What story am I telling myself that isn't confirmed?",
                 "What would I tell my best friend about this?",
                 "Which part of this is actually mine to carry?",
                 "What can I let go of before tomorrow?",
             ]},
            {"kind": "notes", "date": "July 13, 2026 at 12:04 AM",
             "title": "Before-bed prompts", "emoji": "\U0001F319\U00002728",
             "prompts": [
                 "What went unexpectedly okay today?",
                 "One thing I'm proud of that nobody saw.",
                 "What am I ready to stop replaying?",
                 "Who or what made today lighter?",
                 "What am I quietly hoping for tomorrow?",
             ]},
            {"kind": "cta"},
        ],
        "caption": (
            "for everyone who opens their journal and just… stares 🫠\n\n"
            "save these for your next blank page — and send them to the "
            "friend whose brain also won't quiet down at midnight.\n\n"
            "which list are you starting with?\n.\n.\n"
            "#journalprompts #journaling #braindump #overthinking "
            "#journalideas #selfcare #mentalhealth #journalingcommunity "
            "#nightroutine #journalwithme"
        ),
    },

    # ---------- T2: editorial guide (follow driver) ----------
    {
        "slug": "t2-guide-start-journaling",
        "slides": [
            {"kind": "card_title",
             "kicker": "( a gentle guide to )",
             "headline": "starting a journal you'll actually keep",
             "sub": "no perfect handwriting required. six small rules."},
            {"kind": "card_steps", "section": "getting started", "page": "2 / 4",
             "items": [
                 ("pick any notebook or app", "the cheap one you'll actually open wins"),
                 ("start with 3 minutes, not 3 pages", "a tiny habit survives busy weeks"),
                 ("date every entry", "future you loves reading these back"),
             ]},
            {"kind": "card_steps", "section": "keeping it alive", "page": "3 / 4",
             "items": [
                 ("write like nobody's reading", "because nobody is. be messy"),
                 ("use prompts on blank-page days", "we post them daily — no excuses"),
                 ("missed a day? just come back", "streaks bend, they don't break"),
             ]},
            {"kind": "cta"},
        ],
        "caption": (
            "the only journaling guide we'd actually send a beginner 🌱\n\n"
            "six small rules, zero pressure. save it for the day you finally "
            "start — or send it to the friend who keeps saying they will.\n.\n.\n"
            "#journaling #journalguide #howtojournal #journalingforbeginners "
            "#newhabits #selfimprovement #journalprompts #mindfulness "
            "#habitbuilding #journalingcommunity"
        ),
    },

    # ---------- T3: photo + white card (aesthetic) ----------
    {
        "slug": "t3-photo-sunday-reset",
        "slides": [
            {"kind": "photo_cover",
             "bg": f"{BG}/bed/tea-cup-book-blanket_9553513.jpg",
             "title": "sunday reset",
             "sub": "journal ideas for a fresh week"},
            {"kind": "photo_card",
             "bg": f"{BG}/pastel/pastel-stationery-flatlay_5208296.jpg",
             "sections": [
                 ("morning", "☀️", [
                     "how do i want this week to feel?",
                     "what would make this week a win?",
                     "one thing i'm looking forward to",
                     "what do i need more of this week?",
                 ]),
             ]},
            {"kind": "photo_card",
             "bg": f"{BG}/bed/diary-writing-hands-cozy_7269395.jpg",
             "sections": [
                 ("evening", "\U0001F319", [
                     "what am i leaving in last week?",
                     "what deserves a little celebration?",
                     "who do i want to show up for?",
                     "one worry i can set down tonight",
                 ]),
             ]},
            {"kind": "cta"},
        ],
        "caption": (
            "your sunday reset, but make it pen and paper 🕯️\n\n"
            "save this for tonight — morning list with your coffee, evening "
            "list before bed. send it to your sunday-reset friend.\n.\n.\n"
            "#sundayreset #journalprompts #journaling #weeklyreset "
            "#selfcaresunday #journalideas #slowliving #mindfulness "
            "#journalwithme #newweek"
        ),
    },
]
