import asyncio
import math
from collections import deque
from io import BytesIO
from PIL import Image
from bk_light.display_session import BleDisplaySession

try:
    import numpy as np
    _NP = True
except ImportError:
    _NP = False

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

SIGMA = 10.0
RHO   = 28.0
BETA  = 8.0 / 3.0

FPS             = 25.0
DT              = 0.005
STEPS_PER_FRAME = 8       # avance de 0.04 unite de temps Lorenz par frame
TRAIL_LEN       = 500

# Bornes de projection (plan XZ)
X_MIN, X_MAX = -25.0, 25.0
Z_MIN, Z_MAX =   1.0, 49.0

SPEED_MAX = 40.0


# ─────────────────────────────────────────────
# INTEGRATION RK4
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
# PROJECTION ET COULEUR
# ─────────────────────────────────────────────

def project(x, z):
    sx = int((x - X_MIN) / (X_MAX - X_MIN) * (GW - 1) + 0.5)
    sy = int((Z_MAX - z) / (Z_MAX - Z_MIN) * (GH - 1) + 0.5)
    return max(0, min(GW - 1, sx)), max(0, min(GH - 1, sy))


def speed_color(t):
    """t dans [0,1]. bleu(lent) -> cyan -> blanc(rapide)."""
    if t < 0.5:
        s = t * 2.0
        return 0, int(s * 200), int(200 + s * 55)
    s = (t - 0.5) * 2.0
    return int(s * 255), int(200 + s * 55), 255


# ─────────────────────────────────────────────
# RENDU
# ─────────────────────────────────────────────

def make_frame_np(trail):
    n = len(trail)
    if n == 0:
        return Image.new("RGB", (GW, GH), (0, 0, 0))

    arr    = np.array(trail, dtype=np.float32)  # (n, 3) : x, z, speed
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

    # Fondu : queue sombre, tete lumineuse
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


def make_tiles(img):
    pngs = []
    for i in range(NB):
        tile = img.crop((i * W, 0, (i + 1) * W, GH))
        buf  = BytesIO()
        tile.save(buf, format="PNG", optimize=False)
        pngs.append(buf.getvalue())
    return pngs


# ─────────────────────────────────────────────
# BLE
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
# BOUCLE PRINCIPALE
# ─────────────────────────────────────────────

async def run():
    engine = "numpy" if _NP else "Python pur"
    print("Connexion a %d panneaux... (moteur : %s)" % (NB, engine))
    sessions = await connect_all()
    print("Lorenz %dx%d | sigma=%.0f rho=%.0f beta=%.4f | FPS=%.0f" % (
        GW, GH, SIGMA, RHO, BETA, FPS))
    print("Trainee %d pts | bleu=lent -> cyan -> blanc=rapide | projection XZ" % TRAIL_LEN)
    print("Ctrl+C pour arreter\n")

    # Condition initiale
    x, y, z = 1.0, 0.0, 20.0

    # Chauffe : rejoint l'attracteur etrange avant d'afficher
    for _ in range(2000):
        x, y, z, _ = rk4_step(x, y, z, DT)

    trail = deque(maxlen=TRAIL_LEN)

    # Pre-remplissage pour que la premiere frame soit deja complete
    for _ in range(TRAIL_LEN):
        x, y, z, speed = rk4_step(x, y, z, DT)
        trail.append((x, z, speed))

    delay = 1.0 / FPS

    try:
        while True:
            for _ in range(STEPS_PER_FRAME):
                x, y, z, speed = rk4_step(x, y, z, DT)
                trail.append((x, z, speed))

            img  = make_frame(list(trail))
            pngs = make_tiles(img)
            await send_all(sessions, pngs)
            await asyncio.sleep(delay)

    except KeyboardInterrupt:
        print("\nArret demande.")
    finally:
        await disconnect_all(sessions)
        print("Deconnecte.")


asyncio.run(run())
