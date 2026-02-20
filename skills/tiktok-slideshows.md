# TikTok Slideshow Creation — Manifest Lock

## Format Rules

- Exactly 6 slides per slideshow
- Image size: 1024x1536 (portrait, ALWAYS)
- Text overlay on slide 1 only (the hook)
- Font size: 6.5% of image width minimum (67px at 1024w)
- Text position: vertically centered, never in top 15% (TikTok status bar) or bottom 10% (TikTok UI)
- Max line width: 80% of image width — if text is wider, reduce font or add line breaks
- Font: bold sans-serif (Impact, Montserrat Bold, or similar high-contrast font)
- Text must have dark stroke/shadow for readability on any background
- Canvas rendering: ALWAYS check that text is not being horizontally compressed

## Visual Storytelling Rules (CRITICAL)

Every slideshow is a 6-part story, NOT 6 versions of the same image.
Each slide must advance the narrative. A viewer should feel momentum
swiping through — if any two slides could be swapped without anyone
noticing, the story arc is broken.

### The 6-Slide Arc

Every slideshow follows this structure regardless of content category:

| Slide | Role               | What It Shows                                                                                                | Energy        |
| ----- | ------------------ | ------------------------------------------------------------------------------------------------------------ | ------------- |
| 1     | **Hook + Setup**   | Scene-setting image WITH hook text overlay. Establishes the characters and situation.                        | Neutral/calm  |
| 2     | **The Reveal**     | The key piece of information drops. A screen, a stat, a number, a message. This is what creates the tension. | Rising        |
| 3     | **The Reaction**   | The emotional beat. A face, a moment of silence, a physical response. This is where the viewer connects.     | Peak          |
| 4     | **The Weight**     | Context or data that makes the reveal hit harder. A stat card, a comparison, a timeline visualization.       | Sustained     |
| 5     | **The Shift**      | Something changes. A new screen, a different choice, a pivot from problem to solution.                       | Turning point |
| 6     | **The Resolution** | The outcome or CTA. Where things land. Can include app name or soft call to action.                          | Resolved      |

### Slide-to-Slide Rules

1. **No two consecutive slides can show the same scene from the same angle.**
   If slide 2 is a close-up of a phone screen, slide 3 CANNOT be another
   close-up of a phone screen. Change the subject, the distance, or the angle.

2. **Alternate between people and objects/data.** A good rhythm:
   person → screen/stat → person's reaction → data card → new screen → wide shot.
   Never do: person → person → person → person.

3. **Each slide must be describable in one sentence that's different from
   every other slide.** If your description of slide 3 sounds like slide 5,
   one of them is redundant.

4. **Slide 1 is the ONLY slide with text overlay.** Slides 2-6 tell the
   story visually. No text, no captions, no labels on the images themselves.

5. **Scale shifts create visual interest.** Mix close-ups (face, phone screen)
   with medium shots (two people talking) and wide shots (room, environment).
   Never stay at the same scale for more than 2 consecutive slides.

### Example Arc: "I showed my mom my lifetime screen time. She went silent."

| Slide | Description                                                                                                      | Scale             |
| ----- | ---------------------------------------------------------------------------------------------------------------- | ----------------- |
| 1     | Daughter and mom sitting at kitchen table, casual afternoon, phone on table. Hook text overlaid.                 | Medium shot       |
| 2     | Close-up of phone screen showing "Screen Time: 11 years of your life" stat. Mom's hand visible at edge of frame. | Close-up          |
| 3     | Mom's face — eyes wide, mouth slightly open, frozen mid-thought. Soft natural light.                             | Close-up portrait |
| 4     | Infographic-style stat card: "7 hrs/day × 365 days × 60 years = 11 YEARS" on dark purple gradient.               | Data card         |
| 5     | Phone screen showing a different app — the manifestation practice interface, morning light, fresh start feeling. | Close-up          |
| 6     | Wide shot of the kitchen, mom and daughter both looking at the phone together, leaning in. Warm light.           | Wide shot         |

### Example Arc: "You'll spend 7 YEARS on TikTok. I replaced 3 minutes with this."

| Slide | Description                                                                                                | Scale            |
| ----- | ---------------------------------------------------------------------------------------------------------- | ---------------- |
| 1     | Young person scrolling phone in bed, blue screen glow on face, dark room. Hook text overlaid.              | Medium shot      |
| 2     | Stat card: "Average daily TikTok time: 95 minutes" on dark gradient.                                       | Data card        |
| 3     | Timeline visualization: "95 min/day = 578 hours/year = 24 FULL DAYS per year"                              | Data card        |
| 4     | Split image: left side is person scrolling in dark room, right side is person in morning light journaling. | Split comparison |
| 5     | Phone screen showing manifestation being read aloud, audio visualizer animation visible.                   | Close-up         |
| 6     | Same person from slide 1, now in morning light, phone down on table, looking out window. Calm, resolved.   | Medium shot      |

### Common Failures (Never Do These)

- **The Slideshow of Sameness**: All 6 slides show the same person in the
  same room with slightly different expressions. No story, no progression.
- **The Data Dump**: All 6 slides are stat cards. No human element, no emotion.
- **The Ad**: Slides 2-6 are all app screenshots. Feels like a product demo, not a story.
- **The Jumble**: Slides have no logical order. Could be rearranged randomly
  with no change in meaning.

## Caption Rules

- Story-style, first person
- Mention the app naturally, never as the first sentence
- Include a soft CTA: "link in bio" or "app is called Manifest Lock"
- Max 5 hashtags (TikTok's current limit)
- Hashtag strategy: 2 niche (#manifestation #lawofattraction), 2 broad (#selfimprovement #mindset), 1 trending

## Delivery & Posting Rules

- After generation, deliver slides + caption via email:
  ```bash
  python3 /root/openclaw/scripts/deliver_email.py "HOOK TEXT" "CAPTION TEXT"
  ```
- Email arrives with all 6 slides attached + caption in the body
- User saves images to phone, opens TikTok/IG natively
- User adds trending sound manually and publishes (~60 seconds)
- Cron schedule: 2 posts/day at peak times (test and iterate)
- NEVER post via API — native posting is required for trending audio

## Content Categories for Manifest Lock

### Category A: Screen Time Shock (Highest potential — visual data)

Generate stat-based slideshows showing phone usage impact.

Slide structure:

1. Hook text on lifestyle background image
2. "The average person spends [X] hours/day on their phone"
3. "That's [Y] hours per year"
4. "Which equals [Z] full days — just on your phone"
5. "Over a lifetime, that's [W] years"
6. "What if you spent just 3 minutes of that manifesting instead?" + app name

Image generation approach: Clean, minimal stat cards with bold typography on
gradient backgrounds. Use gpt-image-1.5 with prompt:
"Clean modern infographic slide, dark purple gradient background (#2D1B69 to #4C1D95),
large white bold text centered, minimalist design, no clutter, portrait orientation 1024x1536"

The numbers change per scenario (student, parent, professional, etc.)

### Category B: Reaction/Story Hooks (Proven viral formula)

"[Person] + [conflict/doubt] → showed them [result] → they changed their mind"

Slide structure (follows the 6-Slide Arc):

1. Hook text on scene-setting image (the two people together, calm before the storm)
2. The reveal — what was shown (phone screen, stat, app, data)
3. The reaction — the other person's face/body language in that moment
4. The weight — context that makes it hit harder (stat card, comparison, timeline)
5. The shift — something changes (new screen, new behavior, new morning)
6. Resolution — the outcome, both people in a new state, soft CTA

Image generation: lifestyle photography style images
Prompt base: "iPhone photo, natural lighting, realistic, portrait orientation.
[Specific scene description]. No AI artifacts, authentic amateur photography quality."

IMPORTANT: Each prompt must specify a DIFFERENT scene, angle, and scale.
Reference the Visual Storytelling Rules above — never repeat the same
composition across slides.

### Category C: Streak/Transformation Content

Document daily manifestation journey through slides.

Slide structure:

1. "Day [X] of reading my manifestations out loud every morning"
   2-5. Journey snapshots (moods, wins, changes)
2. Current streak + invitation to try

### Category D: App Demo Slideshows

Show the actual app experience.

Slide structure:

1. Hook about the problem
   2-5. App screenshots showing the flow (mood check → write → read aloud → unlock)
2. "Download Manifest Lock" CTA

For this category, use actual app screenshots from ~/openclaw/assets/app-screenshots/
Add text overlays to screenshots explaining each step.

## Hook Formulas That Work (Update continuously)

### Proven Formula (from Oliver Henry's data):

"[Another person] + [conflict or doubt] → showed them [thing] → they changed their mind"

Adapted for Manifest Lock:

- "My therapist didn't believe manifestation works until I showed her my 30-day streak"
- "I told my boyfriend I spend 3 minutes every morning talking to myself. Then I showed him why"
- "My roommate laughed when I said I manifest every day. Then she saw my screen time drop by 4 hours"
- "My mom thought manifestation was nonsense until I showed her what happened after 21 days"
- "I showed my friend how many years she'll waste on Instagram. She downloaded this app the same day"

### Shock/Stat Formula:

- "You'll spend [X] years of your life on your phone. Here's what that actually looks like"
- "The average [age group] spends [X] hours on TikTok daily. I spent 3 minutes doing this instead"
- "I replaced 3 minutes of scrolling with this. Here's what happened in 30 days"

### Curiosity Gap Formula:

- "There's an app that blocks your phone until you read your manifestations out loud"
- "I found an app that makes you earn your screen time"
- "The app my therapist recommended that actually changed my morning routine"

## Failure Log (Update after every flop)

<!-- Add entries here as: [date] [hook] [views] [why it failed] -->

- Template: Self-focused hooks ("See your goals in a new way") → nobody cares
- Template: Feature-focused hooks ("Our app has AI-generated affirmations") → sounds like an ad
- Template: Vague motivation ("You can do anything") → no story, no conflict, scroll-past

## Success Log (Update after every win)

<!-- Add entries here as: [date] [hook] [views] [why it worked] -->

## Image Generation — How to Execute

You have a Python script at `/root/openclaw/scripts/generate_slideshow.py`
that generates images via the OpenAI API and applies text overlays.

### For Reaction/Story Slideshows (Category B)

Once you have 6 approved image prompts and a hook, generate the slideshow
by running this command:

```bash
cd /root/openclaw && python3 -c "
from scripts.generate_slideshow import generate_reaction_slideshow

hook = 'YOUR HOOK TEXT HERE'
slides_config = [
    {'prompt': 'SLIDE 1 PROMPT HERE', 'overlay_text': None},
    {'prompt': 'SLIDE 2 PROMPT HERE', 'overlay_text': None},
    {'prompt': 'SLIDE 3 PROMPT HERE', 'overlay_text': None},
    {'prompt': 'SLIDE 4 PROMPT HERE', 'overlay_text': None},
    {'prompt': 'SLIDE 5 PROMPT HERE', 'overlay_text': None},
    {'prompt': 'SLIDE 6 PROMPT HERE', 'overlay_text': None},
]

result = generate_reaction_slideshow(hook, slides_config)
for s in result:
    print(s)
"
```

The script will:

1. Generate each image via OpenAI gpt-image-1.5 (1024x1536 portrait)
2. Apply the hook text overlay to slide 1 only (bold, centered, with stroke)
3. Save all slides to `/root/openclaw/output/`
4. Print the file paths when done

### For Screen Time Stat Slideshows (Category A)

```bash
cd /root/openclaw && python3 -c "
from scripts.generate_slideshow import generate_stat_slideshow

result = generate_stat_slideshow({
    'persona': 'college student',
    'daily_hours': 7,
    'hook': 'YOUR HOOK TEXT HERE',
    'age': 20,
    'life_expectancy': 80,
})
for s in result:
    print(s)
"
```

### After Generation

Once slides are generated in `/root/openclaw/output/`:

1. Deliver to phone via email:
   ```bash
   python3 /root/openclaw/scripts/deliver_email.py "HOOK TEXT" "FULL CAPTION TEXT"
   ```
2. Email arrives with 6 slides attached + hook and caption in the body
3. User saves slides to camera roll, posts natively with trending sound

### Cost Per Slideshow

- 6 images × ~$0.04-0.08 each = ~$0.25-0.50 per slideshow
- Budget for 3 slideshows/day = ~$1-1.50/day in OpenAI image costs
