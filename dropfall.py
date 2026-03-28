import asyncio
import random
from io import BytesIO
from PIL import Image
from bk_light.display_session import BleDisplaySession

MAC_ADDRESS = "76:BF:38:1E:71:88"
W, H = 32, 32

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
            "x": random.uniform(0, W),
            "y": 0.0,
            "len": random.randint(1, 3),
            "speed": speed + random.random() * 1.5,
        })

    pixels = [(0, 0, 0)] * (W * H)

    # Déplacement des gouttes
    alive = []
    for d in drops:
        d["y"] += d["speed"] * 0.4
        d["x"] += wind * 0.15
        d["x"] %= W

        if d["y"] >= H:
            # Impact → splash
            splashes.append({"x": round(d["x"]), "life": 6})
        else:
            alive.append(d)
            # Traîne de la goutte
            for i in range(d["len"] + 1):
                py = int(d["y"]) - i
                px = round(d["x"])
                if 0 <= py < H and 0 <= px < W:
                    brightness = 255 * (1 - i / (d["len"] + 1))
                    pixels[py * W + px] = rain_color(brightness)

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
                px = (s["x"] + dx) % W
                pixels[(H - 1) * W + px] = col
            px_center = s["x"] % W        # ← % W ajouté ici
            pixels[(H - 1) * W + px_center] = col

    splashes[:] = alive_splashes

    return pixels

def pixels_to_png(pixels):
    img = Image.new("RGB", (W, H))
    img.putdata(pixels)
    out = BytesIO()
    img.save(out, format="PNG", optimize=False)
    return out.getvalue()

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

    async with BleDisplaySession(MAC_ADDRESS) as session:
        print(f"Pluie pendant {duration}s à {fps} FPS...")
        t0 = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - t0 < duration:
            pixels = step_rain(drops, splashes, intensity, speed, wind)
            png = pixels_to_png(pixels)
            await session.send_png(png, delay=0.0)
            await asyncio.sleep(delay)
        print("Animation terminée.")

asyncio.run(rain_animation(
    duration=30.0,
    fps=15.0,
    intensity=4,   # bruine: 2 / averse: 6 / déluge: 9
    speed=2,       # lente: 1 / normale: 2 / rapide: 5
    wind=0,        # pluie oblique: -2 ou +2
))
