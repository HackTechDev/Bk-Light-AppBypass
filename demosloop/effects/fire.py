import random
import numpy as np
from PIL import Image
from demosloop.common import GW, GH

FPS = 15.0
INTENSITY = 160
COOLING = 4.0
WIND = 1

# Palette feu : noir -> rouge -> orange -> jaune -> blanc
PALETTE = []
for t in range(256):
    if t < 64:
        PALETTE.append((t * 4, 0, 0))
    elif t < 128:
        PALETTE.append((255, (t - 64) * 4, 0))
    elif t < 192:
        PALETTE.append((255, 255, (t - 128) * 4))
    else:
        PALETTE.append((255, 255, 255))


def step_fire(buf, intensity=INTENSITY, cooling=COOLING, wind=WIND):
    for x in range(GW):
        buf[GH - 1, x] = random.randint(255 - intensity, 255) if random.random() < 0.6 else 0

    new_buf = buf.copy()
    for y in range(GH - 1):
        for x in range(GW):
            xw = (x + wind) % GW
            below1 = buf[y + 1, (xw - 1) % GW]
            below2 = buf[y + 1, xw]
            below3 = buf[y + 1, (xw + 1) % GW]
            below4 = buf[y + 2, xw] if y + 2 < GH else below2
            v = (below1 + below2 + below3 + below4) / 4.0
            new_buf[y, x] = max(0, int(v - random.random() * cooling))

    return new_buf


def init_state():
    return {"buf": np.zeros((GH, GW), dtype=int)}


def render(state):
    state["buf"] = step_fire(state["buf"])
    buf = state["buf"]
    img = Image.new("RGB", (GW, GH))
    pixels = [PALETTE[min(255, max(0, buf[y, x]))] for y in range(GH) for x in range(GW)]
    img.putdata(pixels)
    return img
