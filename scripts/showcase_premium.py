#!/usr/bin/env python3
"""Premium app-showcase posts for the JournalLock brand page (pinned set).

Editorial direction — the opposite of the loud direct-response style:
Playfair serif in mixed case, letterspaced kickers, generous whitespace,
Higgsfield-generated photographic backdrops (sage/cream studio scenes), and
slim floating phone mockups with real UI. No ALL-CAPS shouting, no clutter.

Run from repo root:  .venv/bin/python3 scripts/showcase_premium.py
Output: output/brand-posts-premium/<slug>.jpg + caption.txt
"""

import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1350
SHOTS = "assets/app-screenshots"
BDS = "assets/brand-backdrops"
HANDLE = "@journallock"

INK = (44, 38, 30)            # warm near-black for type on cream
GREEN_D = (39, 107, 66)


def playfair(size, wght=600):
    f = ImageFont.truetype("fonts/PlayfairDisplay-Variable.ttf", size)
    f.set_variation_by_axes([wght])
    return f


def sf(size, bold=False):
    f = ImageFont.truetype("/System/Library/Fonts/SFNS.ttf", size)
    try:
        f.set_variation_by_name("Bold" if bold else "Regular")
    except Exception:
        pass
    return f


def cover_crop(img, w=W, h=H):
    src, dst = img.width / img.height, w / h
    if src > dst:
        nh, nw = h, round(img.width * h / img.height)
    else:
        nw, nh = w, round(img.height * w / img.width)
    img = img.resize((nw, nh), Image.LANCZOS)
    l, t = (nw - w) // 2, (nh - h) // 2
    return img.crop((l, t, l + w, t + h))


def tracked_text(d, xy, text, font, fill, tracking=8, centered_w=None):
    """Letterspaced caps — measure then draw char by char."""
    text = text.upper()
    total = sum(d.textlength(c, font=font) + tracking for c in text) - tracking
    x, y = xy
    if centered_w:
        x = (centered_w - total) / 2
    for c in text:
        d.text((x, y), c, font=font, fill=fill)
        x += d.textlength(c, font=font) + tracking
    return total


def slim_phone(shot_path, height):
    """Premium mockup: slim dark bezel, big radius, straight-on."""
    shot = Image.open(shot_path).convert("RGBA")
    inner_h = height - 24
    shot = shot.resize((round(shot.width * inner_h / shot.height), inner_h),
                       Image.LANCZOS)
    r = int(shot.width * 0.135)
    mask = Image.new("L", shot.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0) + shot.size, r, fill=255)
    shot.putalpha(mask)

    pad = 12
    body = Image.new("RGBA", (shot.width + 2 * pad, height), (0, 0, 0, 0))
    bd = ImageDraw.Draw(body)
    bd.rounded_rectangle((0, 0) + body.size, r + pad, fill=(28, 28, 30, 255))
    # hairline bezel highlight
    bd.rounded_rectangle((1, 1, body.width - 2, body.height - 2), r + pad,
                         outline=(90, 90, 94, 255), width=2)
    body.alpha_composite(shot, (pad, pad))
    return body


def float_phone(canvas, phone, cx, top):
    """Place with a soft ambient shadow beneath (floating look)."""
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    ew = int(phone.width * 0.88)
    ey = top + phone.height - 8
    sd.ellipse((cx - ew // 2, ey - 26, cx + ew // 2, ey + 30),
               fill=(30, 24, 16, 110))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(22)))
    canvas.alpha_composite(phone, (cx - phone.width // 2, top))


def type_block(img, kicker, headline, y0, kicker_col=GREEN_D):
    d = ImageDraw.Draw(img)
    tracked_text(d, (0, y0), kicker, sf(26, bold=True), kicker_col,
                 tracking=10, centered_w=W)
    y = y0 + 64
    hf = playfair(84)
    for ln in headline:
        lw = d.textlength(ln, font=hf)
        d.text(((W - lw) / 2, y), ln, font=hf, fill=INK)
        y += 104
    return y


def footer(img, dark=True):
    d = ImageDraw.Draw(img)
    col = (44, 38, 30, 210) if dark else (255, 255, 255, 220)
    line = "JournalLock  ·  free on iOS"
    f = sf(30, bold=True)
    lw = d.textlength(line, font=f)
    d.text(((W - lw) / 2, H - 96), line, font=f, fill=col)
    wf = sf(26)
    tw = d.textlength(HANDLE, font=wf)
    d.text((W - tw - 34, 34), HANDLE, font=wf, fill=col[:3] + (140,))


def studio_post(slug, backdrop, shot, kicker, headline, caption,
                kicker_col=GREEN_D, out_root="output/brand-posts-premium"):
    os.makedirs(out_root, exist_ok=True)
    img = cover_crop(Image.open(f"{BDS}/{backdrop}").convert("RGBA"))
    y = type_block(img, kicker, headline, 96, kicker_col)
    phone = slim_phone(f"{SHOTS}/{shot}", int(H * 0.58))
    float_phone(img, phone, W // 2, y + 44)
    footer(img)
    img.convert("RGB").save(f"{out_root}/{slug}.jpg", quality=94)
    with open(f"{out_root}/{slug}.caption.txt", "w") as f:
        f.write(caption)
    print(slug)


def hero_post(slug, caption, out_root="output/brand-posts-premium"):
    """The photoreal composite scene, typeset on the wall area."""
    os.makedirs(out_root, exist_ok=True)
    src = Image.open(f"{BDS}/bd-hero-composite.jpg").convert("RGBA")
    # 4:5 crop biased to keep the phone + books low, wall high
    img = cover_crop(src)
    d = ImageDraw.Draw(img)
    tracked_text(d, (0, 110), "journal first · scroll later", sf(26, bold=True),
                 (110, 96, 80), tracking=10, centered_w=W)
    hf = playfair(96)
    ln = "Your apps can wait."
    lw = d.textlength(ln, font=hf)
    d.text(((W - lw) / 2, 172), ln, font=hf, fill=INK)
    footer(img)
    img.convert("RGB").save(f"{out_root}/{slug}.jpg", quality=95)
    with open(f"{out_root}/{slug}.caption.txt", "w") as f:
        f.write(caption)
    print(slug)


if __name__ == "__main__":
    hero_post(
        "premium-1-hero-apps-can-wait",
        caption=("JournalLock keeps your distracting apps closed until "
                 "you've written today's entry. one honest page, then the "
                 "internet.\n\nfree on iOS — link in bio.\n.\n.\n"
                 "#journallock #journaling #digitalwellness #screentime "
                 "#slowliving #journalapp #mindfulness"),
    )
    studio_post(
        "premium-2-one-page", "bd-leaf-shadow.png", "journal-lock/37.png",
        "five quiet minutes",
        ["One page", "unlocks your day."],
        caption=("every morning, JournalLock asks for one page before it "
                 "opens anything else. five minutes of writing, and your "
                 "day starts on purpose.\n\nfree on iOS — link in bio.\n.\n.\n"
                 "#journallock #morningroutine #journaling #mindfulness "
                 "#digitalwellness #journalprompts #intentionalliving"),
    )
    studio_post(
        "premium-3-progress", "bd-gradient.png", "journal-lock/33.png",
        "gentle accountability",
        ["Small pages,", "big change."],
        caption=("your streak, your moods, and a little plant that grows "
                 "when you do. progress you can actually feel.\n\n"
                 "free on iOS — link in bio.\n.\n.\n"
                 "#journallock #habittracker #journaling #selfcare "
                 "#moodtracker #growth #mentalwellness"),
    )
    studio_post(
        "premium-4-choose", "bd-silk.png", "journal-lock/32.png",
        "you choose what locks",
        ["Distraction,", "politely declined."],
        kicker_col=INK,
        caption=("pick the apps that steal your evenings. JournalLock holds "
                 "them shut until you've checked in with yourself.\n\n"
                 "free on iOS — link in bio.\n.\n.\n"
                 "#journallock #appblocker #digitaldetox #journaling "
                 "#screentime #focus #intentionalliving"),
    )
