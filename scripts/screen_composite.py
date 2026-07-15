#!/usr/bin/env python3
"""Composite a real app screenshot onto a phone screen in a generated scene.

Workflow: generate a scene with Higgsfield Soul V2 prompting a phone with a
"plain solid dark green screen" (top-down works best), then run this to warp
the real UI onto it. The result is an app-in-the-wild product photo no stock
library can provide.

Usage:
  .venv/bin/python3 scripts/screen_composite.py <scene> <screenshot> <out>

Auto-detects the solid dark-green screen quad; cleans uncovered green slivers
BEFORE compositing so legit green UI (buttons) is never touched.
"""

import sys
from PIL import Image, ImageDraw


def solve8(A, b):
    n = 8
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        for r in range(n):
            if r != c and M[r][c]:
                f = M[r][c] / M[c][c]
                M[r] = [a - f * bb for a, bb in zip(M[r], M[c])]
    return [M[i][8] / M[i][i] for i in range(n)]


def find_coeffs(src, dest):
    A, b = [], []
    for (X, Y), (x, y) in zip(src, dest):
        A.append([x, y, 1, 0, 0, 0, -X * x, -X * y]); b.append(X)
        A.append([0, 0, 0, x, y, 1, -Y * x, -Y * y]); b.append(Y)
    return solve8(A, b)


def is_screen_green(r, g, b):
    return g > r + 14 and g > b + 14 and 45 < g < 150 and r < 105


def detect_quad(img):
    px = img.load()
    pts = [(x, y) for y in range(0, img.height, 3)
           for x in range(0, img.width, 3)
           if is_screen_green(*px[x, y][:3])]
    if len(pts) < 500:
        raise SystemExit("no solid green screen found in scene")
    tl = min(pts, key=lambda p: p[0] + p[1])
    br = max(pts, key=lambda p: p[0] + p[1])
    tr = max(pts, key=lambda p: p[0] - p[1])
    bl = min(pts, key=lambda p: p[0] - p[1])
    return [tl, tr, br, bl]


def composite(scene_path, shot_path, out_path,
              overshoot=(1.065, 1.032), corner=0.09):
    scene = Image.open(scene_path).convert("RGB")
    shot = Image.open(shot_path).convert("RGBA")

    r = int(shot.width * corner)
    mask = Image.new("L", shot.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0) + shot.size, r, fill=255)
    shot.putalpha(mask)

    # faint diagonal sheen sells the emissive-screen look
    sheen = Image.new("L", shot.size, 0)
    sd = ImageDraw.Draw(sheen)
    for i in range(shot.width + shot.height):
        a = max(0, 26 - abs(i - (shot.width + shot.height) * 0.35) // 14)
        sd.line([(i, 0), (0, i)], fill=int(a))
    white = Image.new("RGBA", shot.size, (255, 255, 255, 255))
    white.putalpha(sheen)
    shot.alpha_composite(white)

    quad = detect_quad(scene)
    cx = sum(p[0] for p in quad) / 4
    cy = sum(p[1] for p in quad) / 4
    quad = [(cx + (x - cx) * overshoot[0], cy + (y - cy) * overshoot[1])
            for x, y in quad]
    src = [(0, 0), (shot.width, 0), (shot.width, shot.height), (0, shot.height)]
    layer = shot.transform(scene.size, Image.PERSPECTIVE,
                           find_coeffs(src, quad), Image.BICUBIC)

    # clean uncovered green slivers on the raw scene, then overlay UI on top
    alpha = layer.split()[3].load()
    px = scene.load()
    x0 = max(0, int(min(p[0] for p in quad)) - 80)
    x1 = min(scene.width, int(max(p[0] for p in quad)) + 80)
    y0 = max(0, int(min(p[1] for p in quad)) - 80)
    y1 = min(scene.height, int(max(p[1] for p in quad)) + 80)
    for y in range(y0, y1):
        for x in range(x0, x1):
            if alpha[x, y] < 128 and is_screen_green(*px[x, y]):
                px[x, y] = (34, 37, 33)

    scene = scene.convert("RGBA")
    scene.alpha_composite(layer)
    scene.convert("RGB").save(out_path, quality=94)
    print("wrote", out_path)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    composite(*sys.argv[1:4])
