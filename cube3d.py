import asyncio
import math
from io import BytesIO
from PIL import Image
from bk_light.display_session import BleDisplaySession

MAC_ADDRESS = "76:BF:38:1E:71:88"
W, H = 32, 32

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

def project(v, size=8, fov=20):
    z = v[2] + fov
    px = int(W / 2 + v[0] * size * fov / z)
    py = int(H / 2 + v[1] * size * fov / z)
    return (px, py)

def draw_line(pixels, x0, y0, x1, y1, color):
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        if 0 <= x0 < W and 0 <= y0 < H:
            pixels[y0 * W + x0] = color
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
    max_y = min(H - 1, max(ys))
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
            for x in range(max(0, xs[i]), min(W, xs[i + 1])):
                pixels[y * W + x] = color

def render_cube(ax, ay, az, size=8, wireframe=True, show_faces=False):
    pixels = [(0, 0, 0)] * (W * H)

    # Projection de tous les sommets
    projected = []
    for v in VERTS:
        r = rot_x(v, ax)
        r = rot_y(r, ay)
        r = rot_z(r, az)
        projected.append({"p3": r, "p2": project(r, size)})

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

def pixels_to_png(pixels):
    img = Image.new("RGB", (W, H))
    img.putdata(pixels)
    out = BytesIO()
    img.save(out, format="PNG", optimize=False)
    return out.getvalue()

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

    async with BleDisplaySession(MAC_ADDRESS) as session:
        print(f"Cube 3D pendant {duration}s à {fps} FPS...")
        t0 = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - t0 < duration:
            ax += speed_x * step
            ay += speed_y * step
            az += speed_z * step
            pixels = render_cube(ax, ay, az, size, wireframe, show_faces)
            png = pixels_to_png(pixels)
            await session.send_png(png, delay=0.0)
            await asyncio.sleep(delay)
        print("Animation terminée.")

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
