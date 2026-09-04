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
GRAVITY = 0.04

state = {"running": True}


def on_press(key):
    if key == keyboard.Key.esc:
        state["running"] = False
        return False


def hsv_to_rgb(h):
    h = h % 360
    c = 1.0
    x = c * (1 - abs((h / 60) % 2 - 1))
    if   h < 60:  r,g,b = c,x,0
    elif h < 120: r,g,b = x,c,0
    elif h < 180: r,g,b = 0,c,x
    elif h < 240: r,g,b = 0,x,c
    elif h < 300: r,g,b = x,0,c
    else:         r,g,b = c,0,x
    return (int(r*255), int(g*255), int(b*255))


def make_rocket():
    return {
        "x":       random.uniform(2, GW - 3),
        "y":       float(GH - 1),
        "vy":      -(random.uniform(0.5, 1.1)),
        "target_y": random.uniform(3, GH * 0.5),
        "hue":     random.uniform(0, 360),
        "trail":   [],
    }


def make_burst(x, y, hue, nb_parts=16, life_max=14):
    parts = []
    for i in range(nb_parts):
        angle = (i / nb_parts) * math.pi * 2
        spd   = random.uniform(0.2, 0.7)
        parts.append({
            "x":        x, "y":      y,
            "vx":       math.cos(angle) * spd,
            "vy":       math.sin(angle) * spd,
            "life":     life_max,
            "max_life": life_max,
            "hue":      hue + random.uniform(-30, 30),
        })
    return parts


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


def render(rockets, particles):
    pixels = [(0, 0, 0)] * (GW * GH)

    # Fusées montantes
    for rk in rockets:
        cr, cg, cb = hsv_to_rgb(rk["hue"])
        for j, (tx, ty) in enumerate(rk["trail"]):
            alpha = (j / max(1, len(rk["trail"]))) * 0.8
            set_pixel(pixels, tx, ty, cr, cg, cb, alpha)
        # Tête brillante (blanc chaud)
        set_pixel(pixels, rk["x"], rk["y"], 255, 255, 200, 1.0)

    # Particules d'explosion
    for p in particles:
        alpha = p["life"] / p["max_life"]
        cr, cg, cb = hsv_to_rgb(p["hue"])
        set_pixel(pixels, p["x"], p["y"], cr, cg, cb, alpha)

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


async def fireworks_animation(
    duration=60.0,
    fps=20.0,
    spawn_rate=5,    # fréquence de lancement (1–8)
    nb_parts=16,     # particules par explosion (8–32)
    life_max=14,     # durée de vie des particules (8–24)
):
    rockets    = []
    particles  = []
    delay      = 1.0 / fps

    print("Connexion a %d panneaux..." % NB)
    sessions = await connect_all()
    print(f"Feux d'artifice pendant {duration}s... (Echap pour arreter)")
    t0 = asyncio.get_event_loop().time()
    try:
        while state["running"] and asyncio.get_event_loop().time() - t0 < duration:

            # Lancement aléatoire de fusées
            if random.random() * 10 < spawn_rate:
                rockets.append(make_rocket())

            # Mise à jour des fusées
            still_flying = []
            for rk in rockets:
                rk["trail"].append((rk["x"], rk["y"]))
                if len(rk["trail"]) > 5:
                    rk["trail"].pop(0)
                rk["y"] += rk["vy"]
                if rk["y"] <= rk["target_y"]:
                    # Explosion !
                    particles.extend(make_burst(
                        rk["x"], rk["y"], rk["hue"], nb_parts, life_max
                    ))
                else:
                    still_flying.append(rk)
            rockets = still_flying

            # Mise à jour des particules
            alive = []
            for p in particles:
                p["x"]  += p["vx"]
                p["y"]  += p["vy"]
                p["vy"] += GRAVITY
                p["vx"] *= 0.97
                p["vy"] *= 0.97
                p["life"] -= 1
                if p["life"] > 0:
                    alive.append(p)
            particles = alive

            pngs = make_tiles(pixels_to_img(render(rockets, particles)))
            await send_all(sessions, pngs)
            await asyncio.sleep(delay)

        print("Animation terminée.")
    finally:
        await disconnect_all(sessions)


listener = keyboard.Listener(on_press=on_press)
listener.start()

asyncio.run(fireworks_animation(
    duration=60.0,
    fps=20.0,
    spawn_rate=5,   # 1 rare → 8 continu
    nb_parts=16,    # 8 discret → 32 dense
    life_max=14,    # 8 bref → 24 longue traîne
))

listener.stop()
