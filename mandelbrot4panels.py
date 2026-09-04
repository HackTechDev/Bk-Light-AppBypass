import asyncio
import math
from io import BytesIO
from PIL import Image
from bk_light.display_session import BleDisplaySession

# pip install pynput
from pynput import keyboard

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

MAX_ITER   = 80
FPS        = 5.0
PAL_SPEED  = 0.007   # decalage de palette par frame (couleurs qui s'ecoulent)
ZOOM_SPEED = 0.93    # view_w *= ZOOM_SPEED chaque frame (zoom avant exponentiel)

# Points de zoom alternes : (cx, cy)
# Chacun est zoome de ZOOM_W_START jusqu'a ZOOM_W_MIN, puis on passe au suivant.
TARGETS = [
    (-0.7269,      0.1889),       # spirales bord cardioide principale
    (-0.74364386,  0.13182590),   # vallee des hippocampes
    (-0.5625,     -0.6425),       # branche inferieure, filaments
]
ZOOM_W_START = 3.5      # largeur initiale du plan complexe visible
ZOOM_W_MIN   = 0.0018   # largeur minimale avant reinitialisation

TWO_PI = 2.0 * math.pi


# ─────────────────────────────────────────────
# CLAVIER (pynput — Echap pour quitter)
# ─────────────────────────────────────────────

state = {"running": True}


def on_press(key):
    if key == keyboard.Key.esc:
        state["running"] = False
        return False


# ─────────────────────────────────────────────
# CALCUL MANDELBROT
# ─────────────────────────────────────────────

def _compute_np(cx, cy, view_w):
    view_h = view_w * GH / GW
    cr = np.linspace(cx - view_w * 0.5, cx + view_w * 0.5, GW)
    ci = np.linspace(cy - view_h * 0.5, cy + view_h * 0.5, GH)
    CR, CI = np.meshgrid(cr, ci)
    ZR    = np.zeros((GH, GW), dtype=np.float64)
    ZI    = np.zeros((GH, GW), dtype=np.float64)
    iters = np.zeros((GH, GW), dtype=np.int32)
    alive = np.ones((GH, GW),  dtype=bool)
    for i in range(1, MAX_ITER + 1):
        a = alive
        zr, zi = ZR[a], ZI[a]
        ZR[a]   = zr * zr - zi * zi + CR[a]
        ZI[a]   = 2.0 * zr * zi    + CI[a]
        escaped = a & (ZR * ZR + ZI * ZI > 4.0)
        iters[escaped] = i
        alive[escaped] = False
        ZR[escaped]    = 0.0   # evite NaN/overflow sur pixels echappes
        ZI[escaped]    = 0.0
        if not alive.any():
            break
    return iters   # shape (GH, GW), 0 = dans l'ensemble


def _compute_py(cx, cy, view_w):
    view_h = view_w * GH / GW
    out = []
    for py in range(GH):
        imag = cy - view_h * 0.5 + py * view_h / GH
        for px in range(GW):
            real = cx - view_w * 0.5 + px * view_w / GW
            zr, zi, n = 0.0, 0.0, 0
            while n < MAX_ITER and zr * zr + zi * zi <= 4.0:
                zr, zi = zr * zr - zi * zi + real, 2.0 * zr * zi + imag
                n += 1
            out.append(n if n < MAX_ITER else 0)
    return out


def compute_frame(cx, cy, view_w):
    if _NP:
        return _compute_np(cx, cy, view_w)
    return _compute_py(cx, cy, view_w)


# ─────────────────────────────────────────────
# RENDU
# ─────────────────────────────────────────────

def _render_np(iters, pal_offset):
    mask = iters > 0
    t = np.where(mask, (iters.astype(np.float64) / MAX_ITER + pal_offset) % 1.0, 0.0)
    r = (128 + 127 * np.sin(t * TWO_PI)).astype(np.uint8)
    g = (128 + 127 * np.sin(t * TWO_PI + 2.09440)).astype(np.uint8)
    b = (128 + 127 * np.sin(t * TWO_PI + 4.18879)).astype(np.uint8)
    r[~mask] = 0
    g[~mask] = 0
    b[~mask] = 0
    return Image.fromarray(np.stack([r, g, b], axis=-1), mode='RGB')


def _render_py(iters, pal_offset):
    pal = [(0, 0, 0)]
    for i in range(1, MAX_ITER + 1):
        t = (i / MAX_ITER + pal_offset) % 1.0
        pal.append((
            int(128 + 127 * math.sin(t * TWO_PI)),
            int(128 + 127 * math.sin(t * TWO_PI + 2.09440)),
            int(128 + 127 * math.sin(t * TWO_PI + 4.18879)),
        ))
    img = Image.new("RGB", (GW, GH))
    img.putdata([pal[n] for n in iters])
    return img


def render_frame(iters, pal_offset):
    if _NP:
        return _render_np(iters, pal_offset)
    return _render_py(iters, pal_offset)


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
    engine = "numpy" if _NP else "Python pur (lent)"
    print("Connexion a %d panneaux... (moteur : %s)" % (NB, engine))
    sessions = await connect_all()
    print("Mandelbrot %dx%d | MAX_ITER=%d | FPS=%.0f | Echap pour arreter" % (
        GW, GH, MAX_ITER, FPS))
    print("3 cibles de zoom :\n"
          "  1) Spirales bord cardioide  (-0.7269,  0.1889)\n"
          "  2) Vallee hippocampe        (-0.7436,  0.1318)\n"
          "  3) Branche inferieure       (-0.5625, -0.6425)\n")

    delay      = 1.0 / FPS
    pal_offset = 0.0
    target_idx = 0
    view_w     = ZOOM_W_START
    frame      = 0

    try:
        while state["running"]:
            cx, cy = TARGETS[target_idx]

            iters = compute_frame(cx, cy, view_w)
            img   = render_frame(iters, pal_offset)
            pngs  = make_tiles(img)
            await send_all(sessions, pngs)

            view_w     *= ZOOM_SPEED
            pal_offset  = (pal_offset + PAL_SPEED) % 1.0
            frame      += 1

            if view_w < ZOOM_W_MIN:
                target_idx = (target_idx + 1) % len(TARGETS)
                view_w = ZOOM_W_START
                cx2, cy2 = TARGETS[target_idx]
                print("  -> Cible %d  (%.4f, %.4f)  frame=%d" % (
                    target_idx + 1, cx2, cy2, frame))

            await asyncio.sleep(delay)

    except KeyboardInterrupt:
        print("\nArret demande.")
    finally:
        await disconnect_all(sessions)
        print("Deconnecte.")


listener = keyboard.Listener(on_press=on_press)
listener.start()

asyncio.run(run())

listener.stop()
