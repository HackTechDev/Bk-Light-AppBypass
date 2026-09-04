import random
from PIL import Image
from demosloop.common import GW, GH

FPS = 15.0
DENSITY = 5
TURBULENCE = 2
DECAY = 0.92

# Palette cascade : noir -> bleu fonce -> bleu -> cyan -> blanc
PALETTE = []
for t in range(256):
    if t < 60:
        PALETTE.append((0, 0, 0))
    elif t < 120:
        PALETTE.append((0, (t - 60) * 2, (t - 60) * 3))
    elif t < 180:
        PALETTE.append((0, 80 + (t - 120) * 2, 200))
    else:
        PALETTE.append(((t - 180) * 3, 220, 255))


def step_waterfall(buf, density=DENSITY, turbulence=TURBULENCE, decay=DECAY):
    for x in range(GW):
        if random.random() * 10 < density:
            buf[x] = random.randint(200, 255)

    new_buf = buf[:]

    for y in range(GH - 1, 0, -1):
        for x in range(GW):
            drift = random.randint(-turbulence, turbulence)
            xd = min(GW - 1, max(0, x + drift))
            v = buf[(y - 1) * GW + xd]
            new_buf[y * GW + x] = max(new_buf[y * GW + x], int(v * (decay + random.random() * 0.06)))

    return new_buf


def init_state():
    return {"buf": [0] * (GW * GH)}


def render(state):
    state["buf"] = step_waterfall(state["buf"])
    buf = state["buf"]
    pixels = [PALETTE[min(255, max(0, buf[y * GW + x]))] for y in range(GH) for x in range(GW)]
    img = Image.new("RGB", (GW, GH))
    img.putdata(pixels)
    return img
