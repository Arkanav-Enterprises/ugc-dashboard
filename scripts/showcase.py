#!/usr/bin/env python3
"""App-showcase brand posts (Prayer Lock grid style).

Single 4:5 images: solid brand-color background, condensed-black all-caps
benefit headline, real app screenshots in tilted phone mockups with soft
shadows. One per key feature, for the JournalLock / ManifestLock brand pages.

Run from repo root:  .venv/bin/python3 scripts/showcase.py
Output: output/brand-posts/<slug>.jpg + caption.txt
"""

import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1350
SHOTS = "assets/app-screenshots"
HN = "/System/Library/Fonts/HelveticaNeue.ttc"

JL_GREEN = (66, 145, 85)
JL_HANDLE = "@journallock"
ML_PURPLE = (124, 58, 237)
ML_HANDLE = "@manifestlock"


def headline_font(size):
    return ImageFont.truetype(HN, size, index=9)   # Condensed Black


def bg_canvas(color):
    """Flat brand color with a subtle darkening toward the bottom."""
    img = Image.new("RGBA", (W, H), color + (255,))
    grad = Image.new("L", (1, H))
    for y in range(H):
        grad.putpixel((0, y), int(46 * (y / H) ** 2))
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    dark.putalpha(grad.resize((W, H)))
    img.alpha_composite(dark)
    return img


def phone_mockup(shot_path, height, angle):
    """Screenshot -> rounded corners + black bezel -> rotated RGBA tile."""
    shot = Image.open(shot_path).convert("RGBA")
    scale = (height - 36) / shot.height
    shot = shot.resize((round(shot.width * scale), height - 36), Image.LANCZOS)

    r = int(shot.width * 0.13)
    mask = Image.new("L", shot.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0) + shot.size, r, fill=255)
    shot.putalpha(mask)

    pad = 18
    body = Image.new("RGBA", (shot.width + 2 * pad, height), (0, 0, 0, 0))
    ImageDraw.Draw(body).rounded_rectangle(
        (0, 0) + body.size, r + pad, fill=(24, 24, 26, 255))
    body.alpha_composite(shot, (pad, pad))
    return body.rotate(angle, expand=True, resample=Image.BICUBIC)


def place_with_shadow(canvas, tile, xy):
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sil = Image.new("RGBA", tile.size, (0, 0, 0, 130))
    sil.putalpha(tile.split()[3].point(lambda a: a * 130 // 255))
    sh.alpha_composite(sil, (xy[0] + 14, xy[1] + 26))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(16)))
    canvas.alpha_composite(tile, xy)


def showcase(slug, color, handle, headline_lines, back_shot, front_shot,
             caption, out_root="output/brand-posts"):
    os.makedirs(out_root, exist_ok=True)
    img = bg_canvas(color)
    d = ImageDraw.Draw(img)

    # headline
    hf = headline_font(96)
    y = 88
    for ln in headline_lines:
        ln = ln.upper()
        lw = d.textlength(ln, font=hf)
        d.text(((W - lw) / 2 + 2, y + 3), ln, font=hf, fill=(0, 0, 0, 70))
        d.text(((W - lw) / 2, y), ln, font=hf, fill=(255, 255, 255))
        y += 104

    # phones: back peeks over the right shoulder of the front
    ph = int(H * 0.72)
    if back_shot:
        back = phone_mockup(back_shot, int(ph * 0.94), -7)
        place_with_shadow(img, back, (W // 2 + 30, y + 60))
    front = phone_mockup(front_shot, ph, 6)
    place_with_shadow(img, front, (W // 2 - front.width + 90, y + 30))

    # watermark
    wf = ImageFont.truetype("/System/Library/Fonts/SFNS.ttf", 30)
    tw = d.textlength(handle, font=wf)
    d.text((W - tw - 36, H - 62), handle, font=wf, fill=(255, 255, 255, 200))

    img.convert("RGB").save(f"{out_root}/{slug}.jpg", quality=94)
    with open(f"{out_root}/{slug}.caption.txt", "w") as f:
        f.write(caption)
    print(slug)


POSTS = [
    # ---------------- JournalLock ----------------
    dict(slug="jl-journal-before-apps", color=JL_GREEN, handle=JL_HANDLE,
         headline_lines=["journal before you", "open your apps"],
         back_shot=f"{SHOTS}/journal-lock/37.png",
         front_shot=f"{SHOTS}/journal-lock/36.png",
         caption=("your apps stay locked until you've written today's entry. "
                  "one honest page, then the internet 🌱\n\n"
                  "JournalLock — free to try, link in bio.\n.\n.\n"
                  "#journallock #journaling #screentime #digitalwellness "
                  "#journalapp #mindfulness #phoneaddiction #dailyjournal")),
    dict(slug="jl-locked-until-write", color=JL_GREEN, handle=JL_HANDLE,
         headline_lines=["your apps stay locked", "until you write"],
         back_shot=f"{SHOTS}/journal-lock/30.png",
         front_shot=f"{SHOTS}/journal-lock/32.png",
         caption=("pick your distracting apps. they lock every morning and "
                  "only open after you journal. the streak does the rest 🔒\n\n"
                  "JournalLock — free to try, link in bio.\n.\n.\n"
                  "#journallock #appblocker #journaling #digitaldetox "
                  "#screentime #healthyhabits #journalapp #focus")),
    dict(slug="jl-screen-time", color=JL_GREEN, handle=JL_HANDLE,
         headline_lines=["turn screen time", "into self-reflection"],
         back_shot=f"{SHOTS}/journal-lock/33.png",
         front_shot=f"{SHOTS}/journal-lock/28.png",
         caption=("journal 5 minutes a day. cut screen time by 40%. watch "
                  "your plant (and your mood) grow 🌱\n\n"
                  "JournalLock — free to try, link in bio.\n.\n.\n"
                  "#journallock #screentime #journaling #selfcare "
                  "#digitalwellness #moodtracker #habittracker #growth")),
    # ---------------- ManifestLock ----------------
    dict(slug="ml-manifest-before-scroll", color=ML_PURPLE, handle=ML_HANDLE,
         headline_lines=["manifest before", "you scroll"],
         back_shot=f"{SHOTS}/write-manifestation.png",
         front_shot=f"{SHOTS}/app-blocking.png",
         caption=("your feeds stay locked until you've written today's "
                  "manifestation. intention first, internet second ✨\n\n"
                  "ManifestLock — free to try, link in bio.\n.\n.\n"
                  "#manifestlock #manifestation #affirmations #lawofattraction "
                  "#screentime #manifest #digitalwellness #intentionalliving")),
    dict(slug="ml-3-years", color=ML_PURPLE, handle=ML_HANDLE,
         headline_lines=["you'll spend 3 years", "of your life scrolling"],
         back_shot=f"{SHOTS}/practice-screen.png",
         front_shot=f"{SHOTS}/stats-screen.png",
         caption=("547 hours a year. 3 years over a lifetime. 5% of your "
                  "life — unless you point it somewhere better ✨\n\n"
                  "ManifestLock — free to try, link in bio.\n.\n.\n"
                  "#manifestlock #screentime #manifestation #wakeupcall "
                  "#phoneaddiction #mindfulness #manifest #timewellspent")),
]

if __name__ == "__main__":
    for p in POSTS:
        showcase(**p)
