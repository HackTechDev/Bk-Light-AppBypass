import asyncio
import math
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
CX, CY = GW / 2.0, GH / 2.0

state = {"running": True}


def on_press(key):
    if key == keyboard.Key.esc:
        state["running"] = False
        return False


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
        # Légère teinte bleutée pour les traînes longues (effet vitesse)
        r, g, col_b = (b, b, int(b * 0.85)) if s["dist"] > 4 else (b, b, b)

        # Traîne
        trail = s["trail"]
        for i, (tx, ty) in enumerate(trail):
            alpha = (i / max(1, len(trail))) * 0.75
            set_pixel(pixels, tx, ty, r, g, col_b, alpha)

        # Tête de l'étoile
        set_pixel(pixels, x, y, r, g, col_b, 1.0)

    return pixels


def pixels_to_img(pixels):
    img = Image.new("RGB", (GW, GH))
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


async def starwars_animation(
    duration=60.0,
    fps=20.0,
    nb_stars=100,    # nombre d'étoiles (40–200)
    speed=4.0,       # vitesse d'expansion (1–10)
    trail_len=4,     # longueur de la traîne (1–10)
):
    stars = [make_star() for _ in range(nb_stars)]
    delay = 1.0 / fps

    print("Connexion a %d panneaux..." % NB)
    sessions = await connect_all()
    print(f"Hyperespace pendant {duration}s... (Echap pour arreter)")
    t0 = asyncio.get_event_loop().time()
    try:
        while state["running"] and asyncio.get_event_loop().time() - t0 < duration:

            # Mise à jour de chaque étoile
            for s in stars:
                s["dist"] += s["speed"] * speed * 0.04

                x = CX + math.cos(s["angle"]) * s["dist"]
                y = CY + math.sin(s["angle"]) * s["dist"]

                # Hors panneau → on réinitialise l'étoile au centre
                if not (0 <= x < GW and 0 <= y < GH):
                    s["dist"]       = random.uniform(0.1, 1.0)
                    s["angle"]      = random.uniform(0, math.pi * 2)
                    s["brightness"] = random.uniform(0.5, 1.0)
                    s["speed"]      = random.uniform(0.2, 0.6)
                    s["trail"]      = []
                    continue

                s["trail"].append((x, y))
                if len(s["trail"]) > trail_len:
                    s["trail"].pop(0)

            pixels = render_stars(stars)
            pngs = make_tiles(pixels_to_img(pixels))
            await send_all(sessions, pngs)
            await asyncio.sleep(delay)

        print("Animation terminée.")
    finally:
        await disconnect_all(sessions)


listener = keyboard.Listener(on_press=on_press)
listener.start()

asyncio.run(starwars_animation(
    duration=60.0,
    fps=20.0,
    nb_stars=100,  # densité : 40 épars → 200 champ dense
    speed=4.0,     # vitesse : 1 lente → 10 hyperespace max
    trail_len=4,   # traîne : 1 point → 10 longues lignes
))

listener.stop()
