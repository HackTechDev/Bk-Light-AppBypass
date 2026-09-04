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

def rain_color(brightness):
    b = min(255, max(0, int(brightness)))
    return (int(b * 0.2), b, int(b * 0.2))

def splash_color(life, max_life=6):
    t = life / max_life
    b = int(t * 180)
    return (int(b * 0.2), b, int(b * 0.2))

def step_rain(drops, splashes, intensity=4, speed=2, wind=0):
    # Spawn de nouvelles gouttes
    if random.random() * 10 < intensity:
        drops.append({
            "x": random.uniform(0, GW),
            "y": 0.0,
            "len": random.randint(1, 3),
            "speed": speed + random.random() * 1.5,
        })

    pixels = [(0, 0, 0)] * (GW * GH)

    # Déplacement des gouttes
    alive = []
    for d in drops:
        d["y"] += d["speed"] * 0.4
        d["x"] += wind * 0.15
        d["x"] %= GW

        if d["y"] >= GH:
            # Impact → splash
            splashes.append({"x": round(d["x"]), "life": 6})
        else:
            alive.append(d)
            # Traîne de la goutte
            for i in range(d["len"] + 1):
                py = int(d["y"]) - i
                px = round(d["x"])
                if 0 <= py < GH and 0 <= px < GW:
                    brightness = 255 * (1 - i / (d["len"] + 1))
                    pixels[py * GW + px] = rain_color(brightness)

    drops[:] = alive

# Animation des splashs
    alive_splashes = []
    for s in splashes:
        s["life"] -= 1
        if s["life"] > 0:
            alive_splashes.append(s)
            col = splash_color(s["life"])
            spread = 6 - s["life"]
            for dx in [-spread, spread]:
                px = (s["x"] + dx) % GW
                pixels[(GH - 1) * GW + px] = col
            px_center = s["x"] % GW        # ← % GW ajouté ici
            pixels[(GH - 1) * GW + px_center] = col

    splashes[:] = alive_splashes

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


async def rain_animation(
    duration=30.0,
    fps=15.0,
    intensity=4,   # densité des gouttes (1–10)
    speed=2,       # vitesse de chute (1–6)
    wind=0,        # vent (-3 = gauche, 0 = droit, +3 = droite)
):
    drops = []
    splashes = []
    delay = 1.0 / fps

    print("Connexion a %d panneaux..." % NB)
    sessions = await connect_all()
    print(f"Pluie pendant {duration}s à {fps} FPS... (Echap pour arreter)")
    t0 = asyncio.get_event_loop().time()
    try:
        while state["running"] and asyncio.get_event_loop().time() - t0 < duration:
            pixels = step_rain(drops, splashes, intensity, speed, wind)
            pngs = make_tiles(pixels_to_img(pixels))
            await send_all(sessions, pngs)
            await asyncio.sleep(delay)
        print("Animation terminée.")
    finally:
        await disconnect_all(sessions)

listener = keyboard.Listener(on_press=on_press)
listener.start()

asyncio.run(rain_animation(
    duration=30.0,
    fps=15.0,
    intensity=4,   # bruine: 2 / averse: 6 / déluge: 9
    speed=2,       # lente: 1 / normale: 2 / rapide: 5
    wind=0,        # pluie oblique: -2 ou +2
))

listener.stop()
