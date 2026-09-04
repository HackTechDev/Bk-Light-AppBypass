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

# Le canvas est bien plus large que haut (128x32) : les bras s'etirent
# sur toute la largeur mais restent aplatis verticalement (ellipse) pour
# tenir dans la hauteur d'un panneau.
R_MAX = GW / 2.0 - 8.0                    # portee radiale max des bras (~56)
CORE_R_MAX = R_MAX * 0.18                 # rayon du noyau central
ELLIPSE_SQUISH = (GH / 2.0 - 2.0) / R_MAX  # aplatissement vertical de l'ellipse

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
            r = t * R_MAX + random.uniform(0, R_MAX * 0.12)
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
            "r":          random.uniform(0, CORE_R_MAX),
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
    if not (0 <= x < GW and 0 <= y < GH):
        return
    idx = y * GW + x
    pr, pg, pb = pixels[idx]
    pixels[idx] = (
        min(255, pr + int(r * alpha)),
        min(255, pg + int(g * alpha)),
        min(255, pb + int(b * alpha)),
    )


def render_galaxy(stars, global_angle):
    pixels = [(0, 0, 0)] * (GW * GH)

    for s in stars:
        # Rotation différentielle : les étoiles proches du centre tournent plus vite
        angular_speed = 1.0 / (s["r"] + 1.5)
        angle = s["base_angle"] + global_angle * angular_speed * 8.0

        x = CX + math.cos(angle) * s["r"]
        y = CY + math.sin(angle) * s["r"] * ELLIPSE_SQUISH  # ellipse tres aplatie (canvas large)

        r, g, b = star_color(s)
        set_pixel(pixels, x, y, r, g, b, s["brightness"])

        # Étoiles larges : quelques pixels supplémentaires
        if s["size"] == 2:
            set_pixel(pixels, x + 1, y, r, g, b, s["brightness"] * 0.5)
            set_pixel(pixels, x, y + 1, r, g, b, s["brightness"] * 0.5)

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


async def galaxy_animation(
    duration=60.0,
    fps=20.0,
    speed=3.0,       # vitesse de rotation (1–10)
    nb_stars=150,    # nombre d'étoiles (60–300)
    nb_arms=2,       # nombre de bras spiraux (2–6)
    twist=3.0,       # enroulement des bras (1–8)
):
    stars = make_galaxy(nb_stars, nb_arms, twist)
    global_angle = 0.0
    delay = 1.0 / fps

    print("Connexion a %d panneaux..." % NB)
    sessions = await connect_all()
    print(f"Galaxie en rotation pendant {duration}s... (Echap pour arreter)")
    t0 = asyncio.get_event_loop().time()
    try:
        while state["running"] and asyncio.get_event_loop().time() - t0 < duration:
            global_angle += speed * 0.008

            pixels = render_galaxy(stars, global_angle)
            pngs = make_tiles(pixels_to_img(pixels))
            await send_all(sessions, pngs)
            await asyncio.sleep(delay)

        print("Animation terminée.")
    finally:
        await disconnect_all(sessions)


listener = keyboard.Listener(on_press=on_press)
listener.start()

asyncio.run(galaxy_animation(
    duration=60.0,
    fps=20.0,
    speed=3.0,      # lente: 1 → rapide: 8
    nb_stars=150,   # clairsemée: 60 → dense: 300
    nb_arms=2,      # 2 bras (Voie Lactée) → 6 bras
    twist=3.0,      # peu enroulée: 1 → très spiralée: 8
))

listener.stop()
