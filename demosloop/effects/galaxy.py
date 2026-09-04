import math
import random
from PIL import Image
from demosloop.common import GW, GH

FPS = 20.0
SPEED = 3.0
NB_STARS = 150
NB_ARMS = 2
TWIST = 3.0

CX, CY = GW / 2.0, GH / 2.0

# Le canvas est bien plus large que haut (128x32) : les bras s'etirent
# sur toute la largeur mais restent aplatis verticalement (ellipse) pour
# tenir dans la hauteur d'un panneau.
R_MAX = GW / 2.0 - 8.0
CORE_R_MAX = R_MAX * 0.18
ELLIPSE_SQUISH = (GH / 2.0 - 2.0) / R_MAX


def make_galaxy(nb_stars=NB_STARS, nb_arms=NB_ARMS, twist=TWIST):
    stars = []
    per_arm = nb_stars // nb_arms

    for arm in range(nb_arms):
        arm_offset = (arm / nb_arms) * math.pi * 2
        for i in range(per_arm):
            t = i / per_arm
            r = t * R_MAX + random.uniform(0, R_MAX * 0.12)
            scatter = (1 - t) * 0.6 + 0.1
            base_angle = arm_offset + t * twist * math.pi
            base_angle += random.uniform(-scatter, scatter)
            stars.append({
                "r":          r,
                "base_angle": base_angle,
                "brightness": random.uniform(0.4, 1.0),
                "size":       2 if random.random() < 0.15 else 1,
                "color":      "blue" if arm % 2 == 0 else "warm",
            })

    for _ in range(10):
        stars.append({
            "r":          random.uniform(0, CORE_R_MAX),
            "base_angle": random.uniform(0, math.pi * 2),
            "brightness": random.uniform(0.8, 1.0),
            "size":       1,
            "color":      "core",
        })

    return stars


def star_color(s):
    b = int(s["brightness"] * 255)
    if s["color"] == "core":
        return (255, 240, 200)
    if s["color"] == "blue":
        return (int(b * 0.6), int(b * 0.8), b)
    return (b, int(b * 0.85), int(b * 0.5))


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


def render_galaxy(stars, global_angle):
    pixels = [(0, 0, 0)] * (GW * GH)

    for s in stars:
        angular_speed = 1.0 / (s["r"] + 1.5)
        angle = s["base_angle"] + global_angle * angular_speed * 8.0

        x = CX + math.cos(angle) * s["r"]
        y = CY + math.sin(angle) * s["r"] * ELLIPSE_SQUISH

        r, g, b = star_color(s)
        set_pixel(pixels, x, y, r, g, b, s["brightness"])

        if s["size"] == 2:
            set_pixel(pixels, x + 1, y, r, g, b, s["brightness"] * 0.5)
            set_pixel(pixels, x, y + 1, r, g, b, s["brightness"] * 0.5)

    return pixels


def init_state():
    return {"stars": make_galaxy(), "global_angle": 0.0}


def render(state):
    state["global_angle"] += SPEED * 0.008
    pixels = render_galaxy(state["stars"], state["global_angle"])
    img = Image.new("RGB", (GW, GH))
    img.putdata(pixels)
    return img
