import math
from PIL import Image
from demosloop.common import GW, GH

FPS = 15.0
SPEED_X = 1.0
SPEED_Y = 2.0
SPEED_Z = 0.0
SIZE = 8
WIREFRAME = True
SHOW_FACES = False
STEP = 0.02
DRIFT_AMPLITUDE = GW / 2.0 - 18.0
DRIFT_SPEED = 0.15

VERTS = [
    (-1,-1,-1), ( 1,-1,-1), ( 1, 1,-1), (-1, 1,-1),
    (-1,-1, 1), ( 1,-1, 1), ( 1, 1, 1), (-1, 1, 1),
]

EDGES = [
    (0,1),(1,2),(2,3),(3,0),
    (4,5),(5,6),(6,7),(7,4),
    (0,4),(1,5),(2,6),(3,7),
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


def project(v, size=8, fov=20, center_x=GW / 2.0, center_y=GH / 2.0):
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


def render_cube(ax, ay, az, size=SIZE, wireframe=WIREFRAME, show_faces=SHOW_FACES,
                 center_x=GW / 2.0, center_y=GH / 2.0):
    pixels = [(0, 0, 0)] * (GW * GH)

    projected = []
    for v in VERTS:
        r = rot_x(v, ax)
        r = rot_y(r, ay)
        r = rot_z(r, az)
        projected.append({"p3": r, "p2": project(r, size, center_x=center_x, center_y=center_y)})

    if show_faces:
        faces_z = []
        for f in FACES:
            avg_z = sum(projected[i]["p3"][2] for i in f["verts"]) / 4
            faces_z.append((avg_z, f))
        for _, f in sorted(faces_z, key=lambda x: x[0]):
            pts = [projected[i]["p2"] for i in f["verts"]]
            fill_face(pixels, pts, f["color"])

    if wireframe:
        for a, b in EDGES:
            x0, y0 = projected[a]["p2"]
            x1, y1 = projected[b]["p2"]
            draw_line(pixels, x0, y0, x1, y1, (0, 200, 255))

    return pixels


def init_state():
    return {"ax": 0.0, "ay": 0.0, "az": 0.0, "t": 0.0}


def render(state):
    state["ax"] += SPEED_X * STEP
    state["ay"] += SPEED_Y * STEP
    state["az"] += SPEED_Z * STEP
    state["t"] += STEP

    center_x = GW / 2.0 + DRIFT_AMPLITUDE * math.sin(state["t"] * DRIFT_SPEED)
    pixels = render_cube(state["ax"], state["ay"], state["az"],
                          center_x=center_x, center_y=GH / 2.0)
    img = Image.new("RGB", (GW, GH))
    img.putdata(pixels)
    return img
