import asyncio
import random
import numpy as np
from io import BytesIO
from PIL import Image
from bk_light.display_session import BleDisplaySession

# pip install pynput
from pynput import keyboard

MAC_ADDRESS = "76:BF:38:1E:71:88"  # ← votre adresse MAC
W, H = 32, 32   # adaptez à votre panneau (64x16 si ACT1025)

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
    for x in range(W):
        buf[H - 1, x] = random.randint(255 - intensity, 255) if random.random() < 0.6 else 0

    # Propagation vers le haut avec refroidissement
    new_buf = buf.copy()
    for y in range(H - 1):
        for x in range(W):
            xw = (x + wind) % W
            below1 = buf[y + 1, (xw - 1) % W]
            below2 = buf[y + 1, xw]
            below3 = buf[y + 1, (xw + 1) % W]
            below4 = buf[y + 2, xw] if y + 2 < H else below2
            v = (below1 + below2 + below3 + below4) / 4.0
            new_buf[y, x] = max(0, int(v - random.random() * cooling))

    return new_buf

def buf_to_png(buf: np.ndarray) -> bytes:
    img = Image.new("RGB", (W, H))
    pixels = [PALETTE[min(255, max(0, buf[y, x]))] for y in range(H) for x in range(W)]
    img.putdata(pixels)
    out = BytesIO()
    img.save(out, format="PNG", optimize=False)
    return out.getvalue()

async def fire_animation(
    duration: float = 30.0,   # secondes
    fps: float = 15.0,        # images par seconde
    intensity: int = 160,     # hauteur des flammes (0–255)
    cooling: float = 4.0,     # refroidissement (plus élevé = flammes courtes)
    wind: int = 1,            # décalage horizontal (-2 à +2)
):
    buf = np.zeros((H, W), dtype=int)
    delay = 1.0 / fps

    async with BleDisplaySession(MAC_ADDRESS) as session:
        print(f"Feu pendant {duration}s à {fps} FPS... (Echap pour arreter)")
        t0 = asyncio.get_event_loop().time()
        while state["running"] and asyncio.get_event_loop().time() - t0 < duration:
            buf = step_fire(buf, intensity, cooling, wind)
            png = buf_to_png(buf)
            await session.send_png(png, delay=0.0)
            await asyncio.sleep(delay)
        print("Animation terminée.")

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
