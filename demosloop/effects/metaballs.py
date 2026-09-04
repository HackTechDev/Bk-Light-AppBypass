import math
from PIL import Image
from demosloop.common import GW, GH

try:
    import numpy as np
    _NP = True
except ImportError:
    _NP = False

FPS = 20.0
THRESHOLD = 1.0


class Ball:
    """Metaball animee par oscillations sinusoidales independantes sur x et y."""

    def __init__(self, cx, cy, ax, ay, fx, fy, phi_x, phi_y, radius, color):
        self.cx    = float(cx)
        self.cy    = float(cy)
        self.ax    = float(ax)
        self.ay    = float(ay)
        self.fx    = fx
        self.fy    = fy
        self.phi_x = phi_x
        self.phi_y = phi_y
        self.r_sq  = float(radius * radius)
        self.color = color

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

if _NP:
    _PX, _PY = np.meshgrid(
        np.arange(GW, dtype=np.float32),
        np.arange(GH, dtype=np.float32),
    )


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
    inten = sv * sv * (3.0 - 2.0 * sv)

    r = np.clip(CR / safe * inten, 0, 255).astype(np.uint8)
    g = np.clip(CG / safe * inten, 0, 255).astype(np.uint8)
    b = np.clip(CB / safe * inten, 0, 255).astype(np.uint8)

    return Image.fromarray(np.stack([r, g, b], axis=-1), mode='RGB')


def _frame_py(t):
    bx_arr, by_arr, rsq_arr, rc_arr, gc_arr, bc_arr = [], [], [], [], [], []
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


def init_state():
    return {"t": 0.0}


def render(state):
    img = make_frame(state["t"])
    state["t"] += 1.0 / FPS
    return img
