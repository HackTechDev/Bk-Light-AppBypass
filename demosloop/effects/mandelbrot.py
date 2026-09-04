import math
from PIL import Image
from demosloop.common import GW, GH

try:
    import numpy as np
    _NP = True
except ImportError:
    _NP = False

FPS        = 5.0
MAX_ITER   = 80
PAL_SPEED  = 0.007
ZOOM_SPEED = 0.93

TARGETS = [
    (-0.7269,      0.1889),
    (-0.74364386,  0.13182590),
    (-0.5625,     -0.6425),
]
ZOOM_W_START = 3.5
ZOOM_W_MIN   = 0.0018

TWO_PI = 2.0 * math.pi


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
        ZR[escaped]    = 0.0
        ZI[escaped]    = 0.0
        if not alive.any():
            break
    return iters


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


def init_state():
    return {
        "pal_offset": 0.0,
        "target_idx": 0,
        "view_w": ZOOM_W_START,
    }


def render(state):
    cx, cy = TARGETS[state["target_idx"]]
    iters = compute_frame(cx, cy, state["view_w"])
    img = render_frame(iters, state["pal_offset"])

    state["view_w"] *= ZOOM_SPEED
    state["pal_offset"] = (state["pal_offset"] + PAL_SPEED) % 1.0

    if state["view_w"] < ZOOM_W_MIN:
        state["target_idx"] = (state["target_idx"] + 1) % len(TARGETS)
        state["view_w"] = ZOOM_W_START

    return img
