import asyncio
import random
from io import BytesIO
from PIL import Image
from bk_light.display_session import BleDisplaySession

# pip install pynput
from pynput import keyboard

MAC_PANELS = [
    "FF:50:05:B7:03:C6",
    "2B:F4:CA:80:5D:A9",
    "6F:E3:D9:1A:19:CA",
    "76:BF:38:1E:71:88",
]

W, H = 32, 32
NB = len(MAC_PANELS)
GW = W * NB   # 128 px
GH = H        # 32 px

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
    for x in range(GW):
        if random.random() * 10 < density:
            buf[x] = random.randint(200, 255)

    new_buf = buf[:]

    # Propagation vers le bas
    for y in range(GH - 1, 0, -1):
        for x in range(GW):
            drift = random.randint(-turbulence, turbulence)
            xd = min(GW - 1, max(0, x + drift))
            v = buf[(y - 1) * GW + xd]
            new_buf[y * GW + x] = max(new_buf[y * GW + x], int(v * (decay + random.random() * 0.06)))

    return new_buf

def buf_to_img(buf):
    img = Image.new("RGB", (GW, GH))
    pixels = [PALETTE[min(255, max(0, buf[y * GW + x]))] for y in range(GH) for x in range(GW)]
    img.putdata(pixels)
    return img

def make_tiles(img):
    pngs = []
    for i in range(NB):
        tile = img.crop((i * W, 0, (i + 1) * W, GH))
        buf = BytesIO()
        tile.save(buf, format="PNG", optimize=False)
        pngs.append(buf.getvalue())
    return pngs


async def connect_all():
    sessions = [BleDisplaySession(mac) for mac in MAC_PANELS]
    await asyncio.gather(*[s.__aenter__() for s in sessions])
    return sessions


async def disconnect_all(sessions):
    await asyncio.gather(
        *[s.__aexit__(None, None, None) for s in sessions],
        return_exceptions=True,
    )


async def send_all(sessions, pngs):
    await asyncio.gather(*[
        sessions[i].send_png(pngs[i], delay=0.0)
        for i in range(NB)
    ])


async def waterfall_animation(
    duration=30.0,
    fps=15.0,
    density=5,       # densité des gouttes (1–10)
    turbulence=2,    # dispersion horizontale (0 = droit, 4 = très dispersé)
    decay=0.92,      # atténuation (0.85 = rapide, 0.97 = longue traîne)
):
    buf = [0] * (GW * GH)
    delay = 1.0 / fps

    print("Connexion a %d panneaux..." % NB)
    sessions = await connect_all()
    print(f"Cascade pendant {duration}s à {fps} FPS... (Echap pour arreter)")
    t0 = asyncio.get_event_loop().time()
    try:
        while state["running"] and asyncio.get_event_loop().time() - t0 < duration:
            buf = step_waterfall(buf, density, turbulence, decay)
            pngs = make_tiles(buf_to_img(buf))
            await send_all(sessions, pngs)
            await asyncio.sleep(delay)
        print("Animation terminée.")
    finally:
        await disconnect_all(sessions)

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
