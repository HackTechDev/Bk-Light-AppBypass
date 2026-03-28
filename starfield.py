import asyncio
import math
import random
from io import BytesIO
from PIL import Image
from bk_light.display_session import BleDisplaySession

MAC_ADDRESS = "76:BF:38:1E:71:88"
W, H = 32, 32
CX, CY = W / 2.0, H / 2.0


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
    if not (0 <= x < W and 0 <= y < H):
        return
    idx = y * W + x
    pr, pg, pb = pixels[idx]
    pixels[idx] = (
        min(255, pr + int(r * alpha)),
        min(255, pg + int(g * alpha)),
        min(255, pb + int(b * alpha)),
    )


def render_stars(stars):
    pixels = [(0, 0, 0)] * (W * H)

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


def pixels_to_png(pixels):
    img = Image.new("RGB", (W, H))
    img.putdata(pixels)
    out = BytesIO()
    img.save(out, format="PNG", optimize=False)
    return out.getvalue()


async def starwars_animation(
    duration=60.0,
    fps=20.0,
    nb_stars=40,     # nombre d'étoiles (20–80)
    speed=4.0,       # vitesse d'expansion (1–10)
    trail_len=4,     # longueur de la traîne (1–10)
):
    stars = [make_star() for _ in range(nb_stars)]
    delay = 1.0 / fps

    async with BleDisplaySession(MAC_ADDRESS) as session:
        print(f"Hyperespace pendant {duration}s...")
        t0 = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - t0 < duration:

            # Mise à jour de chaque étoile
            for s in stars:
                s["dist"] += s["speed"] * speed * 0.04

                x = CX + math.cos(s["angle"]) * s["dist"]
                y = CY + math.sin(s["angle"]) * s["dist"]

                # Hors panneau → on réinitialise l'étoile au centre
                if not (0 <= x < W and 0 <= y < H):
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
            await session.send_png(pixels_to_png(pixels), delay=0.0)
            await asyncio.sleep(delay)

        print("Animation terminée.")


asyncio.run(starwars_animation(
    duration=60.0,
    fps=20.0,
    nb_stars=40,   # densité : 20 épars → 80 champ dense
    speed=4.0,     # vitesse : 1 lente → 10 hyperespace max
    trail_len=4,   # traîne : 1 point → 10 longues lignes
))
