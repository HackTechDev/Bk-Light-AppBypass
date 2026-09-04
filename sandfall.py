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

def sand_color(grain):
    v = int(160 + grain * 60)
    return (v, int(v * 0.78), int(v * 0.3))

def step_sand(grid, rate=3, wind=0):
    for _ in range(rate):
        if random.random() < 0.8:
            x = random.randint(0, GW - 1)
            if not grid[x]:
                grid[x] = random.uniform(0.6, 1.0)

    next_grid = [0.0] * (GW * GH)
    moved = [False] * (GW * GH)

    for y in range(GH - 1, -1, -1):
        for x in range(GW):
            g = grid[y * GW + x]
            if not g or moved[y * GW + x]:
                continue

            below = y + 1

            if below >= GH:
                next_grid[y * GW + x] = g
                continue

            if not grid[below * GW + x] and not moved[below * GW + x]:
                next_grid[below * GW + x] = g
                moved[below * GW + x] = True
                continue

            if wind > 0:
                dirs = [1, -1]
            elif wind < 0:
                dirs = [-1, 1]
            else:
                dirs = [-1, 1] if random.random() < 0.5 else [1, -1]

            placed = False
            for dx in dirs:
                nx = x + dx
                if 0 <= nx < GW and not grid[below * GW + nx] and not moved[below * GW + nx]:
                    next_grid[below * GW + nx] = g
                    moved[below * GW + nx] = True
                    placed = True
                    break

            if not placed:
                next_grid[y * GW + x] = g

    return next_grid

def grid_to_img(grid):
    img = Image.new("RGB", (GW, GH))
    pixels = [sand_color(grid[y * GW + x]) if grid[y * GW + x] else (0, 0, 0)
              for y in range(GH) for x in range(GW)]
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


async def sand_animation(
    duration=60.0,
    fps=15.0,
    rate=3,
    wind=0,
    reset_when_full=True,
):
    grid = [0.0] * (GW * GH)
    delay = 1.0 / fps

    print("Connexion a %d panneaux..." % NB)
    sessions = await connect_all()
    print(f"Sable pendant {duration}s à {fps} FPS... (Echap pour arreter)")
    t0 = asyncio.get_event_loop().time()
    try:
        while state["running"] and asyncio.get_event_loop().time() - t0 < duration:
            grid = step_sand(grid, rate, wind)

            if reset_when_full and all(grid[x] for x in range(GW)):
                await asyncio.sleep(1.0)
                grid = [0.0] * (GW * GH)

            pngs = make_tiles(grid_to_img(grid))
            await send_all(sessions, pngs)
            await asyncio.sleep(delay)
        print("Animation terminée.")
    finally:
        await disconnect_all(sessions)

listener = keyboard.Listener(on_press=on_press)
listener.start()

asyncio.run(sand_animation(
    duration=60.0,
    fps=15.0,
    rate=3,
    wind=0,
    reset_when_full=True,
))

listener.stop()
