import math
from collections import deque
from PIL import Image
from demosloop.common import GW, GH

try:
    import numpy as np
    _NP = True
except ImportError:
    _NP = False

FPS = 25.0

SIGMA = 10.0
RHO   = 28.0
BETA  = 8.0 / 3.0

DT              = 0.005
STEPS_PER_FRAME = 8
TRAIL_LEN       = 500

X_MIN, X_MAX = -25.0, 25.0
Z_MIN, Z_MAX =   1.0, 49.0

SPEED_MAX = 40.0


def lorenz_deriv(x, y, z):
    return (
        SIGMA * (y - x),
        x * (RHO - z) - y,
        x * y - BETA * z,
    )


def rk4_step(x, y, z, dt):
    k1x, k1y, k1z = lorenz_deriv(x, y, z)
    k2x, k2y, k2z = lorenz_deriv(
        x + dt * k1x / 2, y + dt * k1y / 2, z + dt * k1z / 2
    )
    k3x, k3y, k3z = lorenz_deriv(
        x + dt * k2x / 2, y + dt * k2y / 2, z + dt * k2z / 2
    )
    k4x, k4y, k4z = lorenz_deriv(
        x + dt * k3x, y + dt * k3y, z + dt * k3z
    )
    nx = x + dt * (k1x + 2 * k2x + 2 * k3x + k4x) / 6
    ny = y + dt * (k1y + 2 * k2y + 2 * k3y + k4y) / 6
    nz = z + dt * (k1z + 2 * k2z + 2 * k3z + k4z) / 6
    speed = math.sqrt(k1x * k1x + k1y * k1y + k1z * k1z)
    return nx, ny, nz, speed


def project(x, z):
    sx = int((x - X_MIN) / (X_MAX - X_MIN) * (GW - 1) + 0.5)
    sy = int((Z_MAX - z) / (Z_MAX - Z_MIN) * (GH - 1) + 0.5)
    return max(0, min(GW - 1, sx)), max(0, min(GH - 1, sy))


def speed_color(t):
    if t < 0.5:
        s = t * 2.0
        return 0, int(s * 200), int(200 + s * 55)
    s = (t - 0.5) * 2.0
    return int(s * 255), int(200 + s * 55), 255


def make_frame_np(trail):
    n = len(trail)
    if n == 0:
        return Image.new("RGB", (GW, GH), (0, 0, 0))

    arr    = np.array(trail, dtype=np.float32)
    xs     = arr[:, 0]
    zs     = arr[:, 1]
    speeds = arr[:, 2]

    sx = np.clip(
        ((xs - X_MIN) / (X_MAX - X_MIN) * (GW - 1) + 0.5).astype(np.int32),
        0, GW - 1,
    )
    sy = np.clip(
        ((Z_MAX - zs) / (Z_MAX - Z_MIN) * (GH - 1) + 0.5).astype(np.int32),
        0, GH - 1,
    )

    fade = np.power(np.arange(1, n + 1, dtype=np.float32) / n, 0.7)

    t    = np.clip(speeds / SPEED_MAX, 0.0, 1.0)
    low  = t < 0.5
    s_lo = t * 2.0
    s_hi = (t - 0.5) * 2.0

    r = np.where(low, 0.0,                  s_hi * 255.0)
    g = np.where(low, s_lo * 200.0,         200.0 + s_hi * 55.0)
    b = np.where(low, 200.0 + s_lo * 55.0, 255.0)

    r *= fade
    g *= fade
    b *= fade

    canvas = np.zeros((GH, GW, 3), dtype=np.float32)
    np.maximum.at(canvas[:, :, 0], (sy, sx), r)
    np.maximum.at(canvas[:, :, 1], (sy, sx), g)
    np.maximum.at(canvas[:, :, 2], (sy, sx), b)

    return Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8), mode="RGB")


def make_frame_py(trail):
    n = len(trail)
    flat = [0.0] * (GH * GW * 3)
    for i, (x, z, speed) in enumerate(trail):
        fade    = ((i + 1) / n) ** 0.7
        t       = min(1.0, speed / SPEED_MAX)
        r, g, b = speed_color(t)
        r, g, b = r * fade, g * fade, b * fade
        sx, sy  = project(x, z)
        idx = (sy * GW + sx) * 3
        flat[idx]     = max(flat[idx],     r)
        flat[idx + 1] = max(flat[idx + 1], g)
        flat[idx + 2] = max(flat[idx + 2], b)
    pixels = [
        (int(flat[i * 3]), int(flat[i * 3 + 1]), int(flat[i * 3 + 2]))
        for i in range(GW * GH)
    ]
    img = Image.new("RGB", (GW, GH))
    img.putdata(pixels)
    return img


def make_frame(trail):
    if _NP:
        return make_frame_np(trail)
    return make_frame_py(trail)


def init_state():
    x, y, z = 1.0, 0.0, 20.0

    for _ in range(2000):
        x, y, z, _ = rk4_step(x, y, z, DT)

    trail = deque(maxlen=TRAIL_LEN)
    for _ in range(TRAIL_LEN):
        x, y, z, speed = rk4_step(x, y, z, DT)
        trail.append((x, z, speed))

    return {"x": x, "y": y, "z": z, "trail": trail}


def render(state):
    for _ in range(STEPS_PER_FRAME):
        state["x"], state["y"], state["z"], speed = rk4_step(
            state["x"], state["y"], state["z"], DT
        )
        state["trail"].append((state["x"], state["z"], speed))

    return make_frame(list(state["trail"]))
