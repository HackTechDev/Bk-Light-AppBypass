import asyncio
import sys
from io import BytesIO
from PIL import Image
from bk_light.display_session import BleDisplaySession

# pip install pynput
from pynput import keyboard

MAC_ADDRESS = "6F:E3:D9:1A:19:CA"
W, H = 32, 32


# ─────────────────────────────────────────────
# ÉTAT DU CUBE
# ─────────────────────────────────────────────

state = {
    "x":      14,
    "y":      14,
    "size":   3,       # taille du carré en pixels (1–6)
    "speed":  2,       # pixels par déplacement
    "color":  (0, 200, 255),  # cyan
    "dirty":  True,    # flag de rendu
    "running": True,
}


# ─────────────────────────────────────────────
# RENDU
# ─────────────────────────────────────────────

def render_cube():
    pixels = [(0, 0, 0)] * (W * H)
    cx, cy = state["x"], state["y"]
    half   = state["size"] // 2
    r, g, b = state["color"]

    for py in range(H):
        for px in range(W):
            in_cube = abs(px - cx) <= half and abs(py - cy) <= half
            if in_cube:
                is_edge = abs(px - cx) == half or abs(py - cy) == half
                if is_edge or state["size"] == 1:
                    pixels[py * W + px] = (r, g, b)
                else:
                    pixels[py * W + px] = (r // 4, g // 4, b // 4)

    img = Image.new("RGB", (W, H))
    img.putdata(pixels)
    out = BytesIO()
    img.save(out, format="PNG", optimize=False)
    return out.getvalue()


# ─────────────────────────────────────────────
# MOUVEMENTS
# ─────────────────────────────────────────────

def move(dx, dy):
    half  = state["size"] // 2
    spd   = state["speed"]
    old_x = state["x"]
    old_y = state["y"]

    state["x"] = max(half, min(W - 1 - half, state["x"] + dx * spd))
    state["y"] = max(half, min(H - 1 - half, state["y"] + dy * spd))

    hit_wall = (state["x"] == old_x and state["y"] == old_y)
    if hit_wall:
        print(f"\r  [WALL] pos=({state['x']},{state['y']})      ", end="", flush=True)
    else:
        print(f"\r  pos=({state['x']:2d},{state['y']:2d})        ", end="", flush=True)

    state["dirty"] = True


# ─────────────────────────────────────────────
# GESTION CLAVIER (pynput)
# ─────────────────────────────────────────────

def on_press(key):
    try:
        if key == keyboard.Key.up:    move(0, -1)
        elif key == keyboard.Key.down:  move(0, +1)
        elif key == keyboard.Key.left:  move(-1, 0)
        elif key == keyboard.Key.right: move(+1, 0)
        elif key == keyboard.Key.esc:
            state["running"] = False
            return False  # Arrête le listener
    except Exception:
        pass


# ─────────────────────────────────────────────
# BOUCLE PRINCIPALE
# ─────────────────────────────────────────────

async def cube_controller():
    print("Cube LED — contrôle clavier")
    print("  Touches fléchées : déplacer le cube")
    print("  Échap            : quitter")
    print()

    # Démarre le listener clavier dans un thread séparé
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    async with BleDisplaySession(MAC_ADDRESS) as session:
        last_png = None
        while state["running"]:
            if state["dirty"]:
                png = render_cube()
                await session.send_png(png, delay=0.0)
                last_png = png
                state["dirty"] = False
            await asyncio.sleep(0.02)  # 50 Hz de polling

    listener.stop()
    print("\nTerminé.")


asyncio.run(cube_controller())
