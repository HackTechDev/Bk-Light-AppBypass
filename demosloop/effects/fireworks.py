import math
import random
from PIL import Image
from demosloop.common import GW, GH

FPS = 20.0
GRAVITY = 0.04
SPAWN_RATE = 5
NB_PARTS = 16
LIFE_MAX = 14


def hsv_to_rgb(h):
    h = h % 360
    c = 1.0
    x = c * (1 - abs((h / 60) % 2 - 1))
    if   h < 60:  r,g,b = c,x,0
    elif h < 120: r,g,b = x,c,0
    elif h < 180: r,g,b = 0,c,x
    elif h < 240: r,g,b = 0,x,c
    elif h < 300: r,g,b = x,0,c
    else:         r,g,b = c,0,x
    return (int(r*255), int(g*255), int(b*255))


def make_rocket():
    return {
        "x":       random.uniform(2, GW - 3),
        "y":       float(GH - 1),
        "vy":      -(random.uniform(0.5, 1.1)),
        "target_y": random.uniform(3, GH * 0.5),
        "hue":     random.uniform(0, 360),
        "trail":   [],
    }


def make_burst(x, y, hue, nb_parts=NB_PARTS, life_max=LIFE_MAX):
    parts = []
    for i in range(nb_parts):
        angle = (i / nb_parts) * math.pi * 2
        spd   = random.uniform(0.2, 0.7)
        parts.append({
            "x":        x, "y":      y,
            "vx":       math.cos(angle) * spd,
            "vy":       math.sin(angle) * spd,
            "life":     life_max,
            "max_life": life_max,
            "hue":      hue + random.uniform(-30, 30),
        })
    return parts


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


def render_pixels(rockets, particles):
    pixels = [(0, 0, 0)] * (GW * GH)

    for rk in rockets:
        cr, cg, cb = hsv_to_rgb(rk["hue"])
        for j, (tx, ty) in enumerate(rk["trail"]):
            alpha = (j / max(1, len(rk["trail"]))) * 0.8
            set_pixel(pixels, tx, ty, cr, cg, cb, alpha)
        set_pixel(pixels, rk["x"], rk["y"], 255, 255, 200, 1.0)

    for p in particles:
        alpha = p["life"] / p["max_life"]
        cr, cg, cb = hsv_to_rgb(p["hue"])
        set_pixel(pixels, p["x"], p["y"], cr, cg, cb, alpha)

    return pixels


def init_state():
    return {"rockets": [], "particles": []}


def render(state):
    if random.random() * 10 < SPAWN_RATE:
        state["rockets"].append(make_rocket())

    still_flying = []
    for rk in state["rockets"]:
        rk["trail"].append((rk["x"], rk["y"]))
        if len(rk["trail"]) > 5:
            rk["trail"].pop(0)
        rk["y"] += rk["vy"]
        if rk["y"] <= rk["target_y"]:
            state["particles"].extend(make_burst(rk["x"], rk["y"], rk["hue"]))
        else:
            still_flying.append(rk)
    state["rockets"] = still_flying

    alive = []
    for p in state["particles"]:
        p["x"]  += p["vx"]
        p["y"]  += p["vy"]
        p["vy"] += GRAVITY
        p["vx"] *= 0.97
        p["vy"] *= 0.97
        p["life"] -= 1
        if p["life"] > 0:
            alive.append(p)
    state["particles"] = alive

    pixels = render_pixels(state["rockets"], state["particles"])
    img = Image.new("RGB", (GW, GH))
    img.putdata(pixels)
    return img
