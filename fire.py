import asyncio
import random
import numpy as np
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

# Palette feu : noir → rouge → orange → jaune → blanc
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

def step_fire(buf: np.ndarray, intensity: int = 160, cooling: float = 4.0, wind: int = 1) -> np.ndarray:
    # Ligne du bas = source de chaleur aléatoire
    for x in range(GW):
        buf[GH - 1, x] = random.randint(255 - intensity, 255) if random.random() < 0.6 else 0

    # Propagation vers le haut avec refroidissement
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

def buf_to_img(buf: np.ndarray) -> Image.Image:
    img = Image.new("RGB", (GW, GH))
    pixels = [PALETTE[min(255, max(0, buf[y, x]))] for y in range(GH) for x in range(GW)]
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


async def fire_animation(
    duration: float = 30.0,   # secondes
    fps: float = 15.0,        # images par seconde
    intensity: int = 160,     # hauteur des flammes (0–255)
    cooling: float = 4.0,     # refroidissement (plus élevé = flammes courtes)
    wind: int = 1,            # décalage horizontal (-2 à +2)
):
    buf = np.zeros((GH, GW), dtype=int)
    delay = 1.0 / fps

    print("Connexion a %d panneaux..." % NB)
    sessions = await connect_all()
    print(f"Feu pendant {duration}s à {fps} FPS... (Echap pour arreter)")
    t0 = asyncio.get_event_loop().time()
    try:
        while state["running"] and asyncio.get_event_loop().time() - t0 < duration:
            buf = step_fire(buf, intensity, cooling, wind)
            pngs = make_tiles(buf_to_img(buf))
            await send_all(sessions, pngs)
            await asyncio.sleep(delay)
        print("Animation terminée.")
    finally:
        await disconnect_all(sessions)

listener = keyboard.Listener(on_press=on_press)
listener.start()

asyncio.run(fire_animation(
    duration=30.0,
    fps=15.0,
    intensity=160,   # augmenter pour des flammes plus hautes
    cooling=4.0,     # diminuer pour des flammes plus longues
    wind=1,          # 0 = droit, + = vers la droite
))

listener.stop()
