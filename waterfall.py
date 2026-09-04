import asyncio
import random
from io import BytesIO
from PIL import Image
from bk_light.display_session import BleDisplaySession

# pip install pynput
from pynput import keyboard

MAC_ADDRESS = "76:BF:38:1E:71:88"
W, H = 32, 32

state = {"running": True}


def on_press(key):
    if key == keyboard.Key.esc:
        state["running"] = False
        return False

# Palette cascade : noir → bleu foncé → bleu → cyan → blanc
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

def step_waterfall(buf, density=5, turbulence=2, decay=0.92):
    # Injection en haut : source de la cascade
    for x in range(W):
        if random.random() * 10 < density:
            buf[x] = random.randint(200, 255)

    new_buf = buf[:]

    # Propagation vers le bas
    for y in range(H - 1, 0, -1):
        for x in range(W):
            drift = random.randint(-turbulence, turbulence)
            xd = min(W - 1, max(0, x + drift))
            v = buf[(y - 1) * W + xd]
            new_buf[y * W + x] = max(new_buf[y * W + x], int(v * (decay + random.random() * 0.06)))

    return new_buf

def buf_to_png(buf):
    img = Image.new("RGB", (W, H))
    pixels = [PALETTE[min(255, max(0, buf[y * W + x]))] for y in range(H) for x in range(W)]
    img.putdata(pixels)
    out = BytesIO()
    img.save(out, format="PNG", optimize=False)
    return out.getvalue()

async def waterfall_animation(
    duration=30.0,
    fps=15.0,
    density=5,       # densité des gouttes (1–10)
    turbulence=2,    # dispersion horizontale (0 = droit, 4 = très dispersé)
    decay=0.92,      # atténuation (0.85 = rapide, 0.97 = longue traîne)
):
    buf = [0] * (W * H)
    delay = 1.0 / fps

    async with BleDisplaySession(MAC_ADDRESS) as session:
        print(f"Cascade pendant {duration}s à {fps} FPS... (Echap pour arreter)")
        t0 = asyncio.get_event_loop().time()
        while state["running"] and asyncio.get_event_loop().time() - t0 < duration:
            buf = step_waterfall(buf, density, turbulence, decay)
            png = buf_to_png(buf)
            await session.send_png(png, delay=0.0)
            await asyncio.sleep(delay)
        print("Animation terminée.")

listener = keyboard.Listener(on_press=on_press)
listener.start()

asyncio.run(waterfall_animation(
    duration=30.0,
    fps=15.0,
    density=5,       # augmenter pour plus de gouttes
    turbulence=2,    # 0 = chute droite, 4 = très éparpillé
    decay=0.92,      # traîne des gouttes
))

listener.stop()
