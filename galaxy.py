import asyncio
import math
import random
from io import BytesIO
from PIL import Image
from bk_light.display_session import BleDisplaySession

# pip install pynput
from pynput import keyboard

MAC_ADDRESS = "76:BF:38:1E:71:88"
W, H = 32, 32
CX, CY = W / 2.0, H / 2.0

state = {"running": True}


def on_press(key):
    if key == keyboard.Key.esc:
        state["running"] = False
        return False


def make_galaxy(nb_stars=60, nb_arms=2, twist=3.0):
    """
    Génère les étoiles de la galaxie.
    Chaque étoile a :
      - r          : distance au centre
      - base_angle : angle de départ sur son bras
      - brightness : éclat (0.0–1.0)
      - size       : 1 = point / 2 = étoile légèrement plus large
      - color      : 'blue' | 'warm' | 'core'
    """
    stars = []
    per_arm = nb_stars // nb_arms

    for arm in range(nb_arms):
        arm_offset = (arm / nb_arms) * math.pi * 2
        for i in range(per_arm):
            t = i / per_arm
            r = t * 13.0 + random.uniform(0, 1.5)
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

    # Noyau central dense et chaud
    for _ in range(10):
        stars.append({
            "r":          random.uniform(0, 2.5),
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
    # warm
    return (b, int(b * 0.85), int(b * 0.5))


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


def render_galaxy(stars, global_angle):
    pixels = [(0, 0, 0)] * (W * H)

    for s in stars:
        # Rotation différentielle : les étoiles proches du centre tournent plus vite
        angular_speed = 1.0 / (s["r"] + 1.5)
        angle = s["base_angle"] + global_angle * angular_speed * 8.0

        x = CX + math.cos(angle) * s["r"]
        y = CY + math.sin(angle) * s["r"] * 0.6  # ellipse légère

        r, g, b = star_color(s)
        set_pixel(pixels, x, y, r, g, b, s["brightness"])

        # Étoiles larges : quelques pixels supplémentaires
        if s["size"] == 2:
            set_pixel(pixels, x + 1, y, r, g, b, s["brightness"] * 0.5)
            set_pixel(pixels, x, y + 1, r, g, b, s["brightness"] * 0.5)

    return pixels


def pixels_to_png(pixels):
    img = Image.new("RGB", (W, H))
    img.putdata(pixels)
    out = BytesIO()
    img.save(out, format="PNG", optimize=False)
    return out.getvalue()


async def galaxy_animation(
    duration=60.0,
    fps=20.0,
    speed=3.0,       # vitesse de rotation (1–10)
    nb_stars=60,     # nombre d'étoiles (20–120)
    nb_arms=2,       # nombre de bras spiraux (2–6)
    twist=3.0,       # enroulement des bras (1–8)
):
    stars = make_galaxy(nb_stars, nb_arms, twist)
    global_angle = 0.0
    delay = 1.0 / fps

    async with BleDisplaySession(MAC_ADDRESS) as session:
        print(f"Galaxie en rotation pendant {duration}s... (Echap pour arreter)")
        t0 = asyncio.get_event_loop().time()
        while state["running"] and asyncio.get_event_loop().time() - t0 < duration:
            global_angle += speed * 0.008

            pixels = render_galaxy(stars, global_angle)
            await session.send_png(pixels_to_png(pixels), delay=0.0)
            await asyncio.sleep(delay)

        print("Animation terminée.")


listener = keyboard.Listener(on_press=on_press)
listener.start()

asyncio.run(galaxy_animation(
    duration=60.0,
    fps=20.0,
    speed=3.0,     # lente: 1 → rapide: 8
    nb_stars=60,   # clairsemée: 20 → dense: 120
    nb_arms=2,     # 2 bras (Voie Lactée) → 6 bras
    twist=3.0,     # peu enroulée: 1 → très spiralée: 8
))

listener.stop()
