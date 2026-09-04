import math
import random
from PIL import Image
from demosloop.common import GW, GH

FPS = 20.0
NB_STARS = 100
SPEED = 4.0
TRAIL_LEN = 4

CX, CY = GW / 2.0, GH / 2.0


def make_star():
    return {
        "angle":      random.uniform(0, math.pi * 2),
        "dist":       random.uniform(0.1, 2.0),
        "speed":      random.uniform(0.2, 0.6),
        "brightness": random.uniform(0.5, 1.0),
        "trail":      [],
    }


def set_pixel(pixels, x, y, r, g, b, alpha=1.0):
    x, y = int(round(x)), int(round(y))
    if not (0 <= x < GW and 0 <= y < GH):
        return
    idx = y * GW + x
    pr, pg, pb = pixels[idx]
    pixels[idx] = (
        min(255, pr + int(r * alpha)),
        min(255, pg + int(g * alpha)),
        min(255, pb + int(b * alpha)),
    )


def render_stars(stars):
    pixels = [(0, 0, 0)] * (GW * GH)

    for s in stars:
        x = CX + math.cos(s["angle"]) * s["dist"]
        y = CY + math.sin(s["angle"]) * s["dist"]

        b = int(s["brightness"] * 255)
        r, g, col_b = (b, b, int(b * 0.85)) if s["dist"] > 4 else (b, b, b)

        trail = s["trail"]
        for i, (tx, ty) in enumerate(trail):
            alpha = (i / max(1, len(trail))) * 0.75
            set_pixel(pixels, tx, ty, r, g, col_b, alpha)

        set_pixel(pixels, x, y, r, g, col_b, 1.0)

    return pixels


def init_state():
    return {"stars": [make_star() for _ in range(NB_STARS)]}


def render(state):
    stars = state["stars"]
    for s in stars:
        s["dist"] += s["speed"] * SPEED * 0.04

        x = CX + math.cos(s["angle"]) * s["dist"]
        y = CY + math.sin(s["angle"]) * s["dist"]

        if not (0 <= x < GW and 0 <= y < GH):
            s["dist"]       = random.uniform(0.1, 1.0)
            s["angle"]      = random.uniform(0, math.pi * 2)
            s["brightness"] = random.uniform(0.5, 1.0)
            s["speed"]      = random.uniform(0.2, 0.6)
            s["trail"]      = []
            continue

        s["trail"].append((x, y))
        if len(s["trail"]) > TRAIL_LEN:
            s["trail"].pop(0)

    pixels = render_stars(stars)
    img = Image.new("RGB", (GW, GH))
    img.putdata(pixels)
    return img
