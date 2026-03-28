import asyncio
import math
import random
from io import BytesIO
from PIL import Image
from bk_light.display_session import BleDisplaySession

# Adresses MAC de vos deux panneaux (cf. config.yaml)
MAC_LEFT  = "6F:E3:D9:1A:19:CA"  # panneau 1 → cube
MAC_RIGHT = "76:BF:38:1E:71:88"  # panneau 2 → boule

W, H = 32, 32

# ─────────────────────────────────────────────
# UTILITAIRES COMMUNS
# ─────────────────────────────────────────────

def pixels_to_png(pixels):
    img = Image.new("RGB", (W, H))
    img.putdata(pixels)
    out = BytesIO()
    img.save(out, format="PNG", optimize=False)
    return out.getvalue()


# ─────────────────────────────────────────────
# PANNEAU 1 : CUBE 3D
# ─────────────────────────────────────────────

VERTS = [
    (-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
    (-1,-1, 1),(1,-1, 1),(1,1, 1),(-1,1, 1),
]
EDGES = [
    (0,1),(1,2),(2,3),(3,0),
    (4,5),(5,6),(6,7),(7,4),
    (0,4),(1,5),(2,6),(3,7),
]

def rot_x(v, a):
    c, s = math.cos(a), math.sin(a)
    return (v[0], v[1]*c - v[2]*s, v[1]*s + v[2]*c)

def rot_y(v, a):
    c, s = math.cos(a), math.sin(a)
    return (v[0]*c + v[2]*s, v[1], -v[0]*s + v[2]*c)

def rot_z(v, a):
    c, s = math.cos(a), math.sin(a)
    return (v[0]*c - v[1]*s, v[0]*s + v[1]*c, v[2])

def project(v, size=8, fov=20):
    z = v[2] + fov
    return (int(W/2 + v[0]*size*fov/z), int(H/2 + v[1]*size*fov/z))

def draw_line(pixels, x0, y0, x1, y1, color):
    dx, dy = abs(x1-x0), abs(y1-y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        if 0 <= x0 < W and 0 <= y0 < H:
            pixels[y0*W + x0] = color
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy: err -= dy; x0 += sx
        if e2 <  dx: err += dx; y0 += sy

def render_cube(ax, ay, az, size=8):
    pixels = [(0, 0, 0)] * (W * H)
    projected = []
    for v in VERTS:
        r = rot_x(v, ax)
        r = rot_y(r, ay)
        r = rot_z(r, az)
        projected.append(project(r, size))
    for a, b in EDGES:
        x0, y0 = projected[a]
        x1, y1 = projected[b]
        draw_line(pixels, x0, y0, x1, y1, (0, 200, 255))
    return pixels


# ─────────────────────────────────────────────
# PANNEAU 2 : BOULE REBONDISSANTE
# ─────────────────────────────────────────────

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

def draw_ball(pixels, cx, cy, radius, color, alpha=1.0):
    r, g, b = color
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx*dx + dy*dy <= radius*radius:
                px, py = int(round(cx+dx)), int(round(cy+dy))
                if 0 <= px < W and 0 <= py < H:
                    idx = py*W + px
                    pr, pg, pb = pixels[idx]
                    pixels[idx] = (
                        min(255, pr + int(r*alpha)),
                        min(255, pg + int(g*alpha)),
                        min(255, pb + int(b*alpha)),
                    )

def render_ball(trail, bx, by, radius, hue):
    pixels = [(0, 0, 0)] * (W * H)
    color = hsv_to_rgb(hue)
    for i, (tx, ty) in enumerate(trail[:-1]):
        alpha = (i / max(1, len(trail))) * 0.5
        draw_ball(pixels, tx, ty, max(1, radius-1), color, alpha)
    draw_ball(pixels, bx, by, radius, color, 1.0)
    return pixels


# ─────────────────────────────────────────────
# BOUCLES INDÉPENDANTES PAR PANNEAU
# ─────────────────────────────────────────────

async def run_cube(duration=60.0, fps=15.0):
    ax = ay = az = 0.0
    delay = 1.0 / fps
    async with BleDisplaySession(MAC_LEFT) as session:
        print("Cube démarré.")
        t0 = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - t0 < duration:
            ax += 0.02
            ay += 0.04
            pixels = render_cube(ax, ay, az)
            await session.send_png(pixels_to_png(pixels), delay=0.0)
            await asyncio.sleep(delay)
    print("Cube terminé.")


async def run_ball(duration=60.0, fps=15.0):
    bx, by = W/2.0, H/2.0
    vx, vy = 0.45, 0.38
    radius = 2
    trail_len = 6
    trail = []
    hue = 0
    delay = 1.0 / fps
    async with BleDisplaySession(MAC_RIGHT) as session:
        print("Boule démarrée.")
        t0 = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - t0 < duration:
            hue = (hue + 4) % 360
            bx += vx
            by += vy
            if bx - radius <= 0:      bx = radius;      vx =  abs(vx)
            if bx + radius >= W - 1:  bx = W-1-radius;  vx = -abs(vx)
            if by - radius <= 0:      by = radius;       vy =  abs(vy)
            if by + radius >= H - 1:  by = H-1-radius;  vy = -abs(vy)
            trail.append((bx, by))
            if len(trail) > trail_len + 1:
                trail.pop(0)
            pixels = render_ball(trail, bx, by, radius, hue)
            await session.send_png(pixels_to_png(pixels), delay=0.0)
            await asyncio.sleep(delay)
    print("Boule terminée.")


# ─────────────────────────────────────────────
# LANCEMENT SIMULTANÉ
# ─────────────────────────────────────────────

async def main():
    print("Lancement des deux panneaux...")
    await asyncio.gather(
        run_cube(duration=60.0, fps=15.0),
        run_ball(duration=60.0, fps=15.0),
    )
    print("Terminé.")

asyncio.run(main())
