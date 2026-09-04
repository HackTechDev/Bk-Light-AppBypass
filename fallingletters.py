import asyncio
import random
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
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
TOTAL_W = W * NB  # 128 px sur 4 panneaux
TEXT = "ILARD HACKLAB"

state = {"running": True}


def on_press(key):
    if key == keyboard.Key.esc:
        state["running"] = False
        return False

# ─────────────────────────────────────────────
# POLICE BITMAP 5x7
# ─────────────────────────────────────────────

FONT = {
    'A': [[0,1,1,0,0],[1,0,0,1,0],[1,0,0,1,0],[1,1,1,1,0],[1,0,0,1,0],[1,0,0,1,0],[1,0,0,1,0]],
    'B': [[1,1,1,0,0],[1,0,0,1,0],[1,0,0,1,0],[1,1,1,0,0],[1,0,0,1,0],[1,0,0,1,0],[1,1,1,0,0]],
    'C': [[0,1,1,1,0],[1,0,0,0,0],[1,0,0,0,0],[1,0,0,0,0],[1,0,0,0,0],[1,0,0,0,0],[0,1,1,1,0]],
    'D': [[1,1,1,0,0],[1,0,0,1,0],[1,0,0,1,0],[1,0,0,1,0],[1,0,0,1,0],[1,0,0,1,0],[1,1,1,0,0]],
    'E': [[1,1,1,1,0],[1,0,0,0,0],[1,0,0,0,0],[1,1,1,0,0],[1,0,0,0,0],[1,0,0,0,0],[1,1,1,1,0]],
    'F': [[1,1,1,1,0],[1,0,0,0,0],[1,0,0,0,0],[1,1,1,0,0],[1,0,0,0,0],[1,0,0,0,0],[1,0,0,0,0]],
    'G': [[0,1,1,1,0],[1,0,0,0,0],[1,0,0,0,0],[1,0,1,1,0],[1,0,0,1,0],[1,0,0,1,0],[0,1,1,1,0]],
    'H': [[1,0,0,1,0],[1,0,0,1,0],[1,0,0,1,0],[1,1,1,1,0],[1,0,0,1,0],[1,0,0,1,0],[1,0,0,1,0]],
    'I': [[1,1,1,0,0],[0,1,0,0,0],[0,1,0,0,0],[0,1,0,0,0],[0,1,0,0,0],[0,1,0,0,0],[1,1,1,0,0]],
    'J': [[0,0,1,1,0],[0,0,0,1,0],[0,0,0,1,0],[0,0,0,1,0],[1,0,0,1,0],[1,0,0,1,0],[0,1,1,0,0]],
    'K': [[1,0,0,1,0],[1,0,1,0,0],[1,1,0,0,0],[1,0,1,0,0],[1,0,0,1,0],[1,0,0,1,0],[1,0,0,1,0]],
    'L': [[1,0,0,0,0],[1,0,0,0,0],[1,0,0,0,0],[1,0,0,0,0],[1,0,0,0,0],[1,0,0,0,0],[1,1,1,1,0]],
    'M': [[1,0,0,0,1],[1,1,0,1,1],[1,0,1,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1]],
    'N': [[1,0,0,0,1],[1,1,0,0,1],[1,0,1,0,1],[1,0,0,1,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1]],
    'O': [[0,1,1,1,0],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[0,1,1,1,0]],
    'P': [[1,1,1,0,0],[1,0,0,1,0],[1,0,0,1,0],[1,1,1,0,0],[1,0,0,0,0],[1,0,0,0,0],[1,0,0,0,0]],
    'R': [[1,1,1,0,0],[1,0,0,1,0],[1,0,0,1,0],[1,1,1,0,0],[1,0,1,0,0],[1,0,0,1,0],[1,0,0,1,0]],
    'S': [[0,1,1,1,0],[1,0,0,0,0],[1,0,0,0,0],[0,1,1,0,0],[0,0,0,1,0],[0,0,0,1,0],[1,1,1,0,0]],
    'T': [[1,1,1,1,1],[0,0,1,0,0],[0,0,1,0,0],[0,0,1,0,0],[0,0,1,0,0],[0,0,1,0,0],[0,0,1,0,0]],
    'U': [[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[0,1,1,1,0]],
    'V': [[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[0,1,0,1,0],[0,1,0,1,0],[0,0,1,0,0]],
    'W': [[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,1,0,1],[1,1,0,1,1],[1,0,0,0,1],[1,0,0,0,1]],
    'X': [[1,0,0,0,1],[0,1,0,1,0],[0,0,1,0,0],[0,0,1,0,0],[0,1,0,1,0],[1,0,0,0,1],[1,0,0,0,1]],
    'Y': [[1,0,0,0,1],[0,1,0,1,0],[0,0,1,0,0],[0,0,1,0,0],[0,0,1,0,0],[0,0,1,0,0],[0,0,1,0,0]],
    'Z': [[1,1,1,1,1],[0,0,0,1,0],[0,0,1,0,0],[0,1,0,0,0],[1,0,0,0,0],[1,0,0,0,0],[1,1,1,1,1]],
    ' ': [[0,0,0,0,0]]*7,
}


# ─────────────────────────────────────────────
# RENDU DU TEXTE EN PIXELS
# ─────────────────────────────────────────────

def render_text(text):
    """Retourne la liste des pixels allumés (gx, gy) sur la grille TOTAL_W x H."""
    pixels = []
    cx = 1
    cy = (H - 7) // 2  # centré verticalement
    for ch in text.upper():
        glyph = FONT.get(ch, FONT[' '])
        for row in range(7):
            for col in range(5):
                if glyph[row][col]:
                    gx = cx + col
                    if gx < TOTAL_W:
                        pixels.append((gx, cy + row))
        cx += 4 if ch == ' ' else 6
    return pixels


# ─────────────────────────────────────────────
# COULEUR PAR POSITION X
# ─────────────────────────────────────────────

def grain_color(orig_x, color_mode="cyan"):
    if color_mode == "cyan":
        return (0, 200, 255)
    if color_mode == "orange":
        return (255, 140, 20)
    if color_mode == "green":
        return (40, 255, 80)
    # arc-en-ciel selon position X
    h = (orig_x / TOTAL_W) * 300 % 360
    c = 1.0
    x = c * (1 - abs((h / 60) % 2 - 1))
    if   h < 60:  r,g,b = c,x,0
    elif h < 120: r,g,b = x,c,0
    elif h < 180: r,g,b = 0,c,x
    elif h < 240: r,g,b = 0,x,c
    elif h < 300: r,g,b = x,0,c
    else:         r,g,b = c,0,x
    return (int(r*255), int(g*255), int(b*255))


# ─────────────────────────────────────────────
# INITIALISATION DES GRAINS
# ─────────────────────────────────────────────

def make_grains(text, color_mode):
    text_pixels = render_text(text)
    grains = []
    for gx, gy in text_pixels:
        grains.append({
            "x":      float(gx),
            "y":      float(gy),
            "vy":     0.0,
            "orig_x": gx,
            "color":  grain_color(gx, color_mode),
            "delay":  random.randint(0, 25),
            "fallen": False,
        })
    return grains


# ─────────────────────────────────────────────
# SIMULATION
# ─────────────────────────────────────────────

def step_grains(grains, grid, gravity=3.0):
    grid[:] = [0] * (TOTAL_W * H)

    # Marque les grains immobiles
    for g in grains:
        if g["fallen"]:
            grid[int(round(g["y"])) * TOTAL_W + int(round(g["x"]))] = 1

    for g in grains:
        if g["fallen"]:
            continue
        if g["delay"] > 0:
            g["delay"] -= 1
            continue

        g["vy"] += gravity * 0.08
        next_y = g["y"] + g["vy"]
        nx, ny = int(round(g["x"])), int(round(next_y))

        # Sol atteint
        if ny >= H - 1:
            g["y"] = float(H - 1)
            g["fallen"] = True
            grid[(H-1) * TOTAL_W + nx] = 1
            continue

        # Collision
        if grid[ny * TOTAL_W + nx]:
            dirs = [-1, 1] if random.random() < 0.5 else [1, -1]
            slid = False
            for dx in dirs:
                sx = nx + dx
                if (0 <= sx < TOTAL_W
                        and not grid[ny * TOTAL_W + sx]
                        and not grid[min(H-1, ny+1) * TOTAL_W + sx]):
                    g["x"] = float(sx)
                    g["y"] = float(ny)
                    g["vy"] *= 0.3
                    grid[ny * TOTAL_W + sx] = 1
                    slid = True
                    break
            if not slid:
                g["y"] = float(int(round(g["y"])))
                g["fallen"] = True
                grid[int(g["y"]) * TOTAL_W + nx] = 1
        else:
            g["y"] = next_y
            grid[ny * TOTAL_W + nx] = 1


# ─────────────────────────────────────────────
# RENDU PNG PAR PANNEAU
# ─────────────────────────────────────────────

def render_panel(grains, panel_index):
    pixels = [(0, 0, 0)] * (W * H)
    x_off = panel_index * W
    for g in grains:
        gx = int(round(g["x"])) - x_off
        gy = int(round(g["y"]))
        if 0 <= gx < W and 0 <= gy < H:
            pixels[gy * W + gx] = g["color"]
    img = Image.new("RGB", (W, H))
    img.putdata(pixels)
    out = BytesIO()
    img.save(out, format="PNG", optimize=False)
    return out.getvalue()


async def connect_all():
    sessions = [BleDisplaySession(mac) for mac in MAC_PANELS]
    await asyncio.gather(*[s.__aenter__() for s in sessions])
    return sessions


async def disconnect_all(sessions):
    await asyncio.gather(
        *[s.__aexit__(None, None, None) for s in sessions],
        return_exceptions=True,
    )


async def send_all(sessions, grains):
    await asyncio.gather(*[
        sessions[i].send_png(render_panel(grains, i), delay=0.0)
        for i in range(NB)
    ])


# ─────────────────────────────────────────────
# ANIMATION PRINCIPALE
# ─────────────────────────────────────────────

async def falling_text_animation(
    duration=120.0,
    fps=15.0,
    gravity=3.0,          # intensité de la gravité (1–8)
    color_mode="cyan",    # "cyan" | "orange" | "green" | "rainbow"
    text=TEXT,
    pause_after=60,       # frames de pause avant rechargement
):
    grid   = [0] * (TOTAL_W * H)
    grains = make_grains(text, color_mode)
    delay  = 1.0 / fps
    pause_counter = 0

    print("Connexion a %d panneaux..." % NB)
    sessions = await connect_all()
    print(f"Texte tombant sur {NB} panneaux — '{text}' (Echap pour arreter)")
    t0 = asyncio.get_event_loop().time()
    try:
        while state["running"] and asyncio.get_event_loop().time() - t0 < duration:

            all_fallen = all(g["fallen"] for g in grains)

            if all_fallen:
                pause_counter += 1
                if pause_counter >= pause_after:
                    # Rechargement du texte
                    grains = make_grains(text, color_mode)
                    grid   = [0] * (TOTAL_W * H)
                    pause_counter = 0
            else:
                step_grains(grains, grid, gravity)

            await send_all(sessions, grains)
            await asyncio.sleep(delay)

        print("Animation terminée.")
    finally:
        await disconnect_all(sessions)


listener = keyboard.Listener(on_press=on_press)
listener.start()

asyncio.run(falling_text_animation(
    duration=120.0,
    fps=15.0,
    gravity=3.0,
    color_mode="cyan",    # "cyan" | "orange" | "green" | "rainbow"
    text="ILARD HACKLAB",
    pause_after=60,       # frames avant rechargement (~4s à 15fps)
))

listener.stop()
