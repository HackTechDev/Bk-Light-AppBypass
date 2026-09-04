import asyncio
import math
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
DRIFT_AMPLITUDE = GW / 2.0 - 18.0   # portee du balayage horizontal du cube
DRIFT_SPEED = 0.15                  # vitesse de balayage gauche-droite

state = {"running": True}


def on_press(key):
    if key == keyboard.Key.esc:
        state["running"] = False
        return False

# Sommets du cube (coordonnées normalisées -1..1)
VERTS = [
    (-1,-1,-1), ( 1,-1,-1), ( 1, 1,-1), (-1, 1,-1),
    (-1,-1, 1), ( 1,-1, 1), ( 1, 1, 1), (-1, 1, 1),
]

EDGES = [
    (0,1),(1,2),(2,3),(3,0),  # face arrière
    (4,5),(5,6),(6,7),(7,4),  # face avant
    (0,4),(1,5),(2,6),(3,7),  # arêtes latérales
]

FACES = [
    {"verts": (0,1,2,3), "color": (0,   0,   180)},
    {"verts": (4,5,6,7), "color": (0,   180, 0  )},
    {"verts": (0,1,5,4), "color": (180, 0,   0  )},
    {"verts": (2,3,7,6), "color": (180, 180, 0  )},
    {"verts": (0,3,7,4), "color": (0,   180, 180)},
    {"verts": (1,2,6,5), "color": (180, 0,   180)},
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

def project(v, size=8, fov=20, center_x=W / 2, center_y=H / 2):
    z = v[2] + fov
    px = int(center_x + v[0] * size * fov / z)
    py = int(center_y + v[1] * size * fov / z)
    return (px, py)

def draw_line(pixels, x0, y0, x1, y1, color):
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        if 0 <= x0 < GW and 0 <= y0 < GH:
            pixels[y0 * GW + x0] = color
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy

def fill_face(pixels, pts, color):
    ys = [p[1] for p in pts]
    min_y = max(0, min(ys))
    max_y = min(GH - 1, max(ys))
    for y in range(min_y, max_y + 1):
        xs = []
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            if (a[1] <= y < b[1]) or (b[1] <= y < a[1]):
                x = int(a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]))
                xs.append(x)
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            for x in range(max(0, xs[i]), min(GW, xs[i + 1])):
                pixels[y * GW + x] = color

def render_cube(ax, ay, az, size=8, wireframe=True, show_faces=False, center_x=GW / 2, center_y=GH / 2):
    pixels = [(0, 0, 0)] * (GW * GH)

    # Projection de tous les sommets
    projected = []
    for v in VERTS:
        r = rot_x(v, ax)
        r = rot_y(r, ay)
        r = rot_z(r, az)
        projected.append({"p3": r, "p2": project(r, size, center_x=center_x, center_y=center_y)})

    # Faces (triées par profondeur, arrière en premier)
    if show_faces:
        faces_z = []
        for f in FACES:
            avg_z = sum(projected[i]["p3"][2] for i in f["verts"]) / 4
            faces_z.append((avg_z, f))
        for _, f in sorted(faces_z, key=lambda x: x[0]):
            pts = [projected[i]["p2"] for i in f["verts"]]
            fill_face(pixels, pts, f["color"])

    # Arêtes (fil de fer)
    if wireframe:
        for a, b in EDGES:
            x0, y0 = projected[a]["p2"]
            x1, y1 = projected[b]["p2"]
            draw_line(pixels, x0, y0, x1, y1, (0, 200, 255))

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


async def cube_animation(
    duration=30.0,
    fps=15.0,
    speed_x=1.0,    # vitesse rotation axe X
    speed_y=2.0,    # vitesse rotation axe Y
    speed_z=0.0,    # vitesse rotation axe Z
    size=8,         # taille du cube (4–12)
    wireframe=True, # afficher les arêtes
    show_faces=False,  # afficher les faces colorées
):
    ax = ay = az = 0.0
    delay = 1.0 / fps
    step = 0.02
    t = 0.0

    print("Connexion a %d panneaux..." % NB)
    sessions = await connect_all()
    print(f"Cube 3D pendant {duration}s à {fps} FPS... (Echap pour arreter)")
    t0 = asyncio.get_event_loop().time()
    try:
        while state["running"] and asyncio.get_event_loop().time() - t0 < duration:
            ax += speed_x * step
            ay += speed_y * step
            az += speed_z * step
            t += step
            center_x = GW / 2.0 + DRIFT_AMPLITUDE * math.sin(t * DRIFT_SPEED)
            pixels = render_cube(ax, ay, az, size, wireframe, show_faces, center_x, GH / 2.0)
            pngs = make_tiles(pixels_to_img(pixels))
            await send_all(sessions, pngs)
            await asyncio.sleep(delay)
        print("Animation terminée.")
    finally:
        await disconnect_all(sessions)

listener = keyboard.Listener(on_press=on_press)
listener.start()

asyncio.run(cube_animation(
    duration=30.0,
    fps=15.0,
    speed_x=1.0,
    speed_y=2.0,
    speed_z=0.0,
    size=8,
    wireframe=True,
    show_faces=False,
))

listener.stop()
