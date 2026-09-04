import random
from PIL import Image
from demosloop.common import GW, GH

FPS = 15.0
INTENSITY = 4
SPEED = 2
WIND = 0


def rain_color(brightness):
    b = min(255, max(0, int(brightness)))
    return (int(b * 0.2), b, int(b * 0.2))


def splash_color(life, max_life=6):
    t = life / max_life
    b = int(t * 180)
    return (int(b * 0.2), b, int(b * 0.2))


def step_rain(drops, splashes, intensity=INTENSITY, speed=SPEED, wind=WIND):
    if random.random() * 10 < intensity:
        drops.append({
            "x": random.uniform(0, GW),
            "y": 0.0,
            "len": random.randint(1, 3),
            "speed": speed + random.random() * 1.5,
        })

    pixels = [(0, 0, 0)] * (GW * GH)

    alive = []
    for d in drops:
        d["y"] += d["speed"] * 0.4
        d["x"] += wind * 0.15
        d["x"] %= GW

        if d["y"] >= GH:
            splashes.append({"x": round(d["x"]), "life": 6})
        else:
            alive.append(d)
            for i in range(d["len"] + 1):
                py = int(d["y"]) - i
                px = round(d["x"])
                if 0 <= py < GH and 0 <= px < GW:
                    brightness = 255 * (1 - i / (d["len"] + 1))
                    pixels[py * GW + px] = rain_color(brightness)

    drops[:] = alive

    alive_splashes = []
    for s in splashes:
        s["life"] -= 1
        if s["life"] > 0:
            alive_splashes.append(s)
            col = splash_color(s["life"])
            spread = 6 - s["life"]
            for dx in [-spread, spread]:
                px = (s["x"] + dx) % GW
                pixels[(GH - 1) * GW + px] = col
            px_center = s["x"] % GW
            pixels[(GH - 1) * GW + px_center] = col

    splashes[:] = alive_splashes

    return pixels


def init_state():
    return {"drops": [], "splashes": []}


def render(state):
    pixels = step_rain(state["drops"], state["splashes"])
    img = Image.new("RGB", (GW, GH))
    img.putdata(pixels)
    return img
