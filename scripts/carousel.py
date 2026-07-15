#!/usr/bin/env python3
"""JournalLock brand carousel renderer (v2).

Three template families modeled on the highest-performing viral journaling
carousels:
  T1 notes    — pixel-authentic iOS Notes screenshot (alena, 80.9K sends)
  T2 card     — editorial cream card, serif + typewriter (euyos)
  T3 photo    — bright photo + white rounded card, script title (diaryoncam)

No dark scrims anywhere: text lives on cards, white space, or native app
chrome. Content lives in carousels.py; run from repo root:
    .venv/bin/python3 scripts/carousel.py
"""

import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1350

# ---------- brand kit ----------
HANDLE = "@journallock"          # placeholder until brand handle confirmed
CREAM = (246, 242, 234)
INK = (74, 52, 40)               # warm brown
GREEN_D = (39, 107, 66)          # JournalLock theme greens
GREEN_M = (66, 145, 85)
GRAY_DATE = (142, 142, 147)      # iOS secondary label
NOTE_INK = (28, 28, 30)          # iOS label
AMBER = (203, 158, 66)           # iOS Notes nav tint

F = "fonts"
SFNS = "/System/Library/Fonts/SFNS.ttf"
EMOJI = "/System/Library/Fonts/Apple Color Emoji.ttc"


def font(path, size, wght=None):
    f = ImageFont.truetype(path, size)
    if wght:
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
    return f


def sf(size, bold=False):
    f = ImageFont.truetype(SFNS, size)
    try:
        f.set_variation_by_name("Bold" if bold else "Regular")
    except Exception:
        pass
    return f


def playfair(size, wght=700, italic=False):
    p = f"{F}/PlayfairDisplay{'-Italic' if italic else ''}-Variable.ttf"
    return font(p, size, wght)


def courier(size, bold=False):
    return ImageFont.truetype(f"{F}/CourierPrime-{'Bold' if bold else 'Regular'}.ttf", size)


def emoji_glyph(char, px):
    f = ImageFont.truetype(EMOJI, 160)
    tile = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    ImageDraw.Draw(tile).text((10, 10), char, font=f, embedded_color=True)
    bb = tile.getbbox()
    if bb:
        tile = tile.crop(bb)
    s = px / tile.height
    return tile.resize((max(1, round(tile.width * s)), px), Image.LANCZOS)


def emoji_clusters(s):
    """Split an emoji string into clusters, keeping VS16/ZWJ/skin tones attached."""
    JOIN = {"️", "‍"} | {chr(c) for c in range(0x1F3FB, 0x1F400)}
    out = []
    for ch in s:
        if out and (ch in JOIN or out[-1][-1] == "‍"):
            out[-1] += ch
        else:
            out.append(ch)
    return out


def draw_emoji_run(img, x, y, chars, px):
    for ch in emoji_clusters(chars):
        g = emoji_glyph(ch, px)
        img.alpha_composite(g, (int(x), int(y)))
        x += g.width + 6
    return x


def wrap(d, text, f, max_w):
    lines, line = [], ""
    for w in text.split():
        t = f"{line} {w}".strip()
        if d.textlength(t, font=f) > max_w and line:
            lines.append(line)
            line = w
        else:
            line = t
    lines.append(line)
    return lines


def cover_crop(img, w=W, h=H):
    src, dst = img.width / img.height, w / h
    if src > dst:
        nh, nw = h, round(img.width * h / img.height)
    else:
        nw, nh = w, round(img.height * w / img.width)
    img = img.resize((nw, nh), Image.LANCZOS)
    l, t = (nw - w) // 2, (nh - h) // 2
    return img.crop((l, t, l + w, t + h))


def watermark(img, dark=False):
    d = ImageDraw.Draw(img)
    f = sf(28)
    tw = d.textlength(HANDLE, font=f)
    col = (120, 108, 96, 160) if dark else (255, 255, 255, 170)
    d.text((W - tw - 36, H - 60), HANDLE, font=f, fill=col)


def rounded_shadow_card(size, radius=44, shadow=70):
    """White rounded card with a soft drop shadow, returned as RGBA layer."""
    w, h = size
    pad = 60
    layer = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle(
        (pad, pad + 10, pad + w, pad + h + 10), radius, fill=(30, 20, 10, shadow))
    layer.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    ImageDraw.Draw(layer).rounded_rectangle(
        (pad, pad, pad + w, pad + h), radius, fill=(255, 255, 255, 246))
    return layer, pad


# ============================================================
# T1 — iOS Notes replica
# ============================================================

def notes_slide(title, title_emoji, prompts, date_str, out):
    img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    d = ImageDraw.Draw(img)

    # nav bar: back chevron + "All iCloud" (left), share + more (right)
    nav_y = 74
    d.line([(64, nav_y + 2), (44, nav_y + 22), (64, nav_y + 42)], fill=AMBER, width=6)
    d.text((84, nav_y), "All iCloud", font=sf(40), fill=AMBER)
    # share icon: box + up arrow
    bx = W - 150
    d.rounded_rectangle((bx, nav_y + 12, bx + 44, nav_y + 50), 8, outline=AMBER, width=5)
    d.line([(bx + 22, nav_y - 4), (bx + 22, nav_y + 30)], fill=AMBER, width=5)
    d.line([(bx + 8, nav_y + 8), (bx + 22, nav_y - 6), (bx + 36, nav_y + 8)], fill=AMBER, width=5)
    # ellipsis circle
    cx = W - 66
    d.ellipse((cx - 24, nav_y + 4, cx + 24, nav_y + 52), outline=AMBER, width=5)
    for i in (-12, 0, 12):
        d.ellipse((cx + i - 4, nav_y + 24, cx + i + 4, nav_y + 32), fill=AMBER)

    # centered date
    df = sf(33)
    tw = d.textlength(date_str, font=df)
    d.text(((W - tw) / 2, 190), date_str, font=df, fill=GRAY_DATE)

    # title + inline emoji
    tf = sf(58, bold=True)
    x, y = 84, 300
    d.text((x, y), title, font=tf, fill=(17, 17, 17))
    ex = x + d.textlength(title, font=tf) + 16
    draw_emoji_run(img, ex, y + 4, title_emoji, 54)

    # dash list
    bf = sf(43)
    y = 430
    dash_w = d.textlength("–   ", font=bf)
    for p in prompts:
        d.text((92, y), "–", font=bf, fill=NOTE_INK)
        for ln in wrap(d, p, bf, W - 92 - dash_w - 80):
            d.text((92 + dash_w, y), ln, font=bf, fill=NOTE_INK)
            y += 64
        y += 24

    wm = ImageDraw.Draw(img)
    f = sf(27)
    wm.text((W - wm.textlength(HANDLE, font=f) - 36, H - 56), HANDLE,
            font=f, fill=(200, 200, 202))
    img.convert("RGB").save(out, quality=94)


def notes_cover(bg_path, quote, sub, out):
    """Cover: bright photo, small typed quote on the pale upper zone."""
    img = cover_crop(Image.open(bg_path).convert("RGBA"))
    # white band top for the quote (like alena's tee-shirt zone)
    band = Image.new("RGBA", (W, 320), (255, 255, 255, 235))
    img.alpha_composite(band, (0, 0))
    d = ImageDraw.Draw(img)
    qf = sf(46, bold=True)
    y = 92
    for ln in wrap(d, quote, qf, W - 220):
        lw = d.textlength(ln, font=qf)
        d.text(((W - lw) / 2, y), ln, font=qf, fill=(30, 30, 32))
        y += 66
    sf2 = sf(34)
    lw = d.textlength(sub, font=sf2)
    d.text(((W - lw) / 2, y + 8), sub, font=sf2, fill=(120, 120, 124))
    watermark(img)
    img.convert("RGB").save(out, quality=94)


# ============================================================
# T2 — editorial cream card
# ============================================================

def washi(img, xy, wh, color, angle):
    w, h = wh
    tape = Image.new("RGBA", (w, h), color + (150,))
    tape = tape.rotate(angle, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(tape, xy)


def card_title_slide(kicker, headline, sub, out):
    img = Image.new("RGBA", (W, H), CREAM + (255,))
    d = ImageDraw.Draw(img)
    washi(img, (W // 2 - 190, 236), (380, 56), (176, 200, 158), 3)

    kf = courier(34)
    kw = d.textlength(kicker, font=kf)
    d.text(((W - kw) / 2, 320), kicker, font=kf, fill=GREEN_D)

    hf = playfair(92, 700)
    y = 430
    for ln in wrap(d, headline, hf, W - 200):
        lw = d.textlength(ln, font=hf)
        d.text(((W - lw) / 2, y), ln, font=hf, fill=INK)
        y += 118

    y += 30
    sf_ = courier(36)
    for ln in wrap(d, sub, sf_, W - 320):
        lw = d.textlength(ln, font=sf_)
        d.text(((W - lw) / 2, y), ln, font=sf_, fill=(122, 104, 90))
        y += 52

    hf2 = courier(30)
    hw = d.textlength(f"a guide by {HANDLE}", font=hf2)
    d.text(((W - hw) / 2, H - 190), f"a guide by {HANDLE}", font=hf2, fill=GREEN_M)
    d.text((84, 64), "journal guide", font=courier(30), fill=(150, 134, 120))
    watermark(img, dark=True)
    img.convert("RGB").save(out, quality=94)


def card_steps_slide(section, items, page, out):
    img = Image.new("RGBA", (W, H), CREAM + (255,))
    d = ImageDraw.Draw(img)
    d.text((84, 64), f"journal guide by {HANDLE}", font=courier(30), fill=(150, 134, 120))

    secf = playfair(76, 700)
    sw = d.textlength(section, font=secf)
    washi(img, (int((W - sw) / 2) - 46, 158), (58, 96), (233, 196, 160), -6)
    d.text(((W - sw) / 2, 170), section, font=secf, fill=INK)

    y = 350
    nf = courier(40, bold=True)
    bf = sf(42)
    for i, (item, note) in enumerate(items, 1):
        # green number badge
        d.ellipse((92, y, 152, y + 60), fill=GREEN_M)
        num = f"{i}"
        nw = d.textlength(num, font=nf)
        d.text((92 + (60 - nw) / 2, y + 7), num, font=nf, fill=(255, 255, 255))
        ty = y
        for ln in wrap(d, item, bf, W - 200 - 84):
            d.text((200, ty), ln, font=bf, fill=(58, 44, 34))
            ty += 60
        if note:
            cf = courier(33)
            for ln in wrap(d, note, cf, W - 200 - 84):
                d.text((200, ty + 2), ln, font=cf, fill=(139, 121, 105))
                ty += 46
        y = ty + 52

    pf = courier(30)
    pw = d.textlength(page, font=pf)
    d.text(((W - pw) / 2, H - 100), page, font=pf, fill=(150, 134, 120))
    watermark(img, dark=True)
    img.convert("RGB").save(out, quality=94)


# ============================================================
# T3 — bright photo + white card
# ============================================================

def photo_cover(bg_path, script_title, sub, out):
    img = cover_crop(Image.open(bg_path).convert("RGBA"))
    d = ImageDraw.Draw(img)
    gf = ImageFont.truetype(f"{F}/GreatVibes-Regular.ttf", 150)
    tw = d.textlength(script_title, font=gf)
    x, y = (W - tw) / 2, H * 0.52  # over the darker lower-middle zone
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((x, y + 6), script_title, font=gf, fill=(25, 16, 8, 235))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    d.text((x, y), script_title, font=gf, fill=(255, 255, 255))

    sf_ = sf(38, bold=True)
    sw = d.textlength(sub, font=sf_)
    sh2 = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh2).text(((W - sw) / 2, y + 222), sub, font=sf_, fill=(25, 16, 8, 220))
    img.alpha_composite(sh2.filter(ImageFilter.GaussianBlur(7)))
    d.text(((W - sw) / 2, y + 218), sub, font=sf_, fill=(255, 255, 255))
    watermark(img)
    img.convert("RGB").save(out, quality=94)


def photo_card_slide(bg_path, sections, out):
    """sections: [(header, emoji, [prompts]), ...] on a white rounded card."""
    img = cover_crop(Image.open(bg_path).convert("RGBA"))
    d0 = ImageDraw.Draw(img)

    hf = sf(44, bold=True)
    bf = sf(36)
    pad_in = 64
    cw = int(W * 0.82)
    # measure card height
    ch = pad_in
    for hdr, em, prompts in sections:
        ch += 66
        for p in prompts:
            ch += 52 * len(wrap(d0, p, bf, cw - 2 * pad_in - 56)) + 10
        ch += 34
    ch += pad_in - 34

    card, pad = rounded_shadow_card((cw, ch))
    cx, cy = (W - cw) // 2 - pad, (H - ch) // 2 - pad
    img.alpha_composite(card, (cx, cy))

    d = ImageDraw.Draw(img)
    x0, y = (W - cw) // 2 + pad_in, cy + pad + pad_in
    for hdr, em, prompts in sections:
        ex = draw_emoji_run(img, x0, y + 4, em, 40)
        d.text((ex + 10, y), hdr, font=hf, fill=GREEN_D)
        y += 66
        for p in prompts:
            g = emoji_glyph("⭐", 30)
            img.alpha_composite(g, (x0 + 4, y + 8))
            for ln in wrap(d, p, bf, cw - 2 * pad_in - 56):
                d.text((x0 + 56, y), ln, font=bf, fill=(60, 60, 64))
                y += 52
            y += 10
        y += 34
    watermark(img)
    img.convert("RGB").save(out, quality=94)


# ============================================================
# shared CTA
# ============================================================

def cta_slide(out):
    img = Image.new("RGBA", (W, H), CREAM + (255,))
    d = ImageDraw.Draw(img)

    tf = playfair(120, 700, italic=True)
    y = 330
    for ln in ["happy", "journaling"]:
        lw = d.textlength(ln, font=tf)
        d.text(((W - lw) / 2, y), ln, font=tf, fill=INK)
        y += 150

    y += 46
    cf = font(f"{F}/Caveat-Variable.ttf", 58, 600)
    line = "save this for your next blank page"
    lw = d.textlength(line, font=cf)
    x = (W - (lw + 56)) / 2
    x = draw_emoji_run(img, x, y + 4, "\U0001F516", 46)
    d.text((x + 10, y), line, font=cf, fill=GREEN_D)
    y += 130

    ff = sf(40, bold=True)
    line = f"follow {HANDLE} for daily prompts"
    lw = d.textlength(line, font=ff)
    d.text(((W - lw) / 2, y), line, font=ff, fill=(58, 44, 34))
    y += 92

    d.line([(W / 2 - 60, y), (W / 2 + 60, y)], fill=(196, 182, 166), width=3)
    y += 56
    mf = courier(34)
    for ln in ["JournalLock locks your apps", "until you journal — link in bio"]:
        lw = d.textlength(ln, font=mf)
        d.text(((W - lw) / 2, y), ln, font=mf, fill=GREEN_M)
        y += 50
    img.convert("RGB").save(out, quality=94)


# ============================================================
# builder
# ============================================================

def build(cfg, out_root="output/brand-carousels"):
    out = os.path.join(out_root, cfg["slug"])
    os.makedirs(out, exist_ok=True)
    n = 0
    for spec in cfg["slides"]:
        n += 1
        path = f"{out}/slide_{n:02d}.jpg"
        kind = spec["kind"]
        if kind == "notes_cover":
            notes_cover(spec["bg"], spec["quote"], spec["sub"], path)
        elif kind == "notes":
            notes_slide(spec["title"], spec["emoji"], spec["prompts"],
                        spec["date"], path)
        elif kind == "card_title":
            card_title_slide(spec["kicker"], spec["headline"], spec["sub"], path)
        elif kind == "card_steps":
            card_steps_slide(spec["section"], spec["items"], spec["page"], path)
        elif kind == "photo_cover":
            photo_cover(spec["bg"], spec["title"], spec["sub"], path)
        elif kind == "photo_card":
            photo_card_slide(spec["bg"], spec["sections"], path)
        elif kind == "cta":
            cta_slide(path)
    if cfg.get("caption"):
        with open(f"{out}/caption.txt", "w") as f:
            f.write(cfg["caption"])
    print(f"{cfg['slug']}: {n} slides -> {out}")


if __name__ == "__main__":
    from carousels import CAROUSELS
    for c in CAROUSELS:
        build(c)
