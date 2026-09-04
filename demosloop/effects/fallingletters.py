import random
from PIL import Image
from demosloop.common import GW, GH

FPS = 15.0
GRAVITY = 3.0
COLOR_MODE = "cyan"    # "cyan" | "orange" | "green" | "rainbow"
TEXT = "GRAOULUG MAKERLAND 2026 METZ"
PAUSE_AFTER = 60

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


def render_text(text):
    pixels = []
    cx = 1
    cy = (GH - 7) // 2
    for ch in text.upper():
        glyph = FONT.get(ch, FONT[' '])
        for row in range(7):
            for col in range(5):
                if glyph[row][col]:
                    gx = cx + col
                    if gx < GW:
                        pixels.append((gx, cy + row))
        cx += 4 if ch == ' ' else 6
    return pixels


def grain_color(orig_x, color_mode="cyan"):
    if color_mode == "cyan":
        return (0, 200, 255)
    if color_mode == "orange":
        return (255, 140, 20)
    if color_mode == "green":
        return (40, 255, 80)
    h = (orig_x / GW) * 300 % 360
    c = 1.0
    x = c * (1 - abs((h / 60) % 2 - 1))
    if   h < 60:  r,g,b = c,x,0
    elif h < 120: r,g,b = x,c,0
    elif h < 180: r,g,b = 0,c,x
    elif h < 240: r,g,b = 0,x,c
    elif h < 300: r,g,b = x,0,c
    else:         r,g,b = c,0,x
    return (int(r*255), int(g*255), int(b*255))


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


def step_grains(grains, grid, gravity=GRAVITY):
    grid[:] = [0] * (GW * GH)

    for g in grains:
        if g["fallen"]:
            grid[int(round(g["y"])) * GW + int(round(g["x"]))] = 1

    for g in grains:
        if g["fallen"]:
            continue
        if g["delay"] > 0:
            g["delay"] -= 1
            continue

        g["vy"] += gravity * 0.08
        next_y = g["y"] + g["vy"]
        nx, ny = int(round(g["x"])), int(round(next_y))

        if ny >= GH - 1:
            g["y"] = float(GH - 1)
            g["fallen"] = True
            grid[(GH-1) * GW + nx] = 1
            continue

        if grid[ny * GW + nx]:
            dirs = [-1, 1] if random.random() < 0.5 else [1, -1]
            slid = False
            for dx in dirs:
                sx = nx + dx
                if (0 <= sx < GW
                        and not grid[ny * GW + sx]
                        and not grid[min(GH-1, ny+1) * GW + sx]):
                    g["x"] = float(sx)
                    g["y"] = float(ny)
                    g["vy"] *= 0.3
                    grid[ny * GW + sx] = 1
                    slid = True
                    break
            if not slid:
                g["y"] = float(int(round(g["y"])))
                g["fallen"] = True
                grid[int(g["y"]) * GW + nx] = 1
        else:
            g["y"] = next_y
            grid[ny * GW + nx] = 1


def render_grains(grains):
    pixels = [(0, 0, 0)] * (GW * GH)
    for g in grains:
        gx, gy = int(round(g["x"])), int(round(g["y"]))
        if 0 <= gx < GW and 0 <= gy < GH:
            pixels[gy * GW + gx] = g["color"]
    img = Image.new("RGB", (GW, GH))
    img.putdata(pixels)
    return img


def init_state():
    return {
        "grid": [0] * (GW * GH),
        "grains": make_grains(TEXT, COLOR_MODE),
        "pause_counter": 0,
    }


def render(state):
    all_fallen = all(g["fallen"] for g in state["grains"])

    if all_fallen:
        state["pause_counter"] += 1
        if state["pause_counter"] >= PAUSE_AFTER:
            state["grains"] = make_grains(TEXT, COLOR_MODE)
            state["grid"] = [0] * (GW * GH)
            state["pause_counter"] = 0
    else:
        step_grains(state["grains"], state["grid"], GRAVITY)

    return render_grains(state["grains"])
