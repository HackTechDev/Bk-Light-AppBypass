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

FPS = 20.0

# Champ de metaball : f(p) = r^2 / dist^2
# Intensite pixel : smoothstep(total_field / (2 * THRESHOLD))
# => bord visible ~50% a total=THRESHOLD, 100% a total=2*THRESHOLD
THRESHOLD = 1.0


# ─────────────────────────────────────────────
# BILLES
# ─────────────────────────────────────────────

class Ball:
    """Metaball animee par oscillations sinusoidales independantes sur x et y."""

    def __init__(self, cx, cy, ax, ay, fx, fy, phi_x, phi_y, radius, color):
        self.cx    = float(cx)
        self.cy    = float(cy)
        self.ax    = float(ax)
        self.ay    = float(ay)
        self.fx    = fx        # frequence angulaire en rad/s
        self.fy    = fy
        self.phi_x = phi_x    # phase initiale
        self.phi_y = phi_y
        self.r_sq  = float(radius * radius)
        self.color = color     # (r, g, b) en 0..255

    def pos(self, t):
        return (
            self.cx + self.ax * math.sin(self.fx * t + self.phi_x),
            self.cy + self.ay * math.sin(self.fy * t + self.phi_y),
        )


#         cx  cy   ax  ay    fx     fy    phi_x  phi_y  r    couleur
BALLS = [
    Ball(64, 16, 44,  8, 0.71, 1.13,  0.00, 0.00,  9, (255,  50,   0)),  # orange
    Ball(64, 16, 38, 10, 1.13, 0.71,  2.09, 1.00,  9, (  0, 210,  60)),  # vert
    Ball(64, 16, 42,  9, 0.89, 1.31,  4.19, 2.50,  9, ( 30,  80, 255)),  # bleu
    Ball(64, 16, 30, 11, 1.31, 0.58,  1.05, 3.70,  8, (210,   0, 180)),  # magenta
]

# ─────────────────────────────────────────────
# CLAVIER (pynput — Echap pour quitter)
# ─────────────────────────────────────────────

state = {"running": True}


def on_press(key):
    if key == keyboard.Key.esc:
        state["running"] = False
        return False


# Grille de pixels precalculee pour numpy
if _NP:
    _PX, _PY = np.meshgrid(
        np.arange(GW, dtype=np.float32),
        np.arange(GH, dtype=np.float32),
    )


# ─────────────────────────────────────────────
# RENDU
# ─────────────────────────────────────────────

def _frame_np(t):
    total = np.zeros((GH, GW), dtype=np.float32)
    CR    = np.zeros((GH, GW), dtype=np.float32)
    CG    = np.zeros((GH, GW), dtype=np.float32)
    CB    = np.zeros((GH, GW), dtype=np.float32)

    for ball in BALLS:
        bx, by = ball.pos(t)
        d2 = np.maximum((_PX - bx) ** 2 + (_PY - by) ** 2, 4.0)
        f  = ball.r_sq / d2
        total += f
        CR    += f * ball.color[0]
        CG    += f * ball.color[1]
        CB    += f * ball.color[2]

    safe  = np.maximum(total, 1e-6)
    sv    = np.clip(total / (2.0 * THRESHOLD), 0.0, 1.0)
    inten = sv * sv * (3.0 - 2.0 * sv)   # smoothstep : bords doux

    r = np.clip(CR / safe * inten, 0, 255).astype(np.uint8)
    g = np.clip(CG / safe * inten, 0, 255).astype(np.uint8)
    b = np.clip(CB / safe * inten, 0, 255).astype(np.uint8)

    return Image.fromarray(np.stack([r, g, b], axis=-1), mode='RGB')


def _frame_py(t):
    # Positions et proprietes precalculees pour eviter les appels dans la boucle interne
    bx_arr = []
    by_arr = []
    rsq_arr = []
    rc_arr = []
    gc_arr = []
    bc_arr = []
    for ball in BALLS:
        bx, by = ball.pos(t)
        bx_arr.append(bx)
        by_arr.append(by)
        rsq_arr.append(ball.r_sq)
        rc_arr.append(ball.color[0])
        gc_arr.append(ball.color[1])
        bc_arr.append(ball.color[2])
    nb = len(BALLS)

    pixels = []
    for py in range(GH):
        for px in range(GW):
            total = cr = cg = cb = 0.0
            for i in range(nb):
                dx = px - bx_arr[i]
                dy = py - by_arr[i]
                d2 = dx * dx + dy * dy
                if d2 < 4.0:
                    d2 = 4.0
                f      = rsq_arr[i] / d2
                total += f
                cr    += f * rc_arr[i]
                cg    += f * gc_arr[i]
                cb    += f * bc_arr[i]
            safe  = total if total > 1e-6 else 1e-6
            sv    = total / (2.0 * THRESHOLD)
            if sv > 1.0:
                sv = 1.0
            inten = sv * sv * (3.0 - 2.0 * sv)
            pixels.append((
                min(255, int(cr / safe * inten)),
                min(255, int(cg / safe * inten)),
                min(255, int(cb / safe * inten)),
            ))

    img = Image.new("RGB", (GW, GH))
    img.putdata(pixels)
    return img


def make_frame(t):
    if _NP:
        return _frame_np(t)
    return _frame_py(t)


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
    print("Metaballs %dx%d px | %d billes | FPS cible : %.0f | Echap pour arreter" % (
        GW, GH, len(BALLS), FPS))
    print("Couleurs : orange / vert / bleu / magenta -- melange par champ scalaire\n")

    delay = 1.0 / FPS
    t     = 0.0

    try:
        while state["running"]:
            img  = make_frame(t)
            pngs = make_tiles(img)
            await send_all(sessions, pngs)
            await asyncio.sleep(delay)
            t += delay

    except KeyboardInterrupt:
        print("\nArret demande.")
    finally:
        await disconnect_all(sessions)
        print("Deconnecte.")


listener = keyboard.Listener(on_press=on_press)
listener.start()

asyncio.run(run())

listener.stop()
