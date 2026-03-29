import asyncio
import math
from io import BytesIO
from PIL import Image
from bk_light.display_session import BleDisplaySession

# Vos deux panneaux (cf. config.yaml)
MAC_LEFT  = "6F:E3:D9:1A:19:CA"
MAC_RIGHT = "76:BF:38:1E:71:88"

W, H = 32, 32
TOTAL_W = W * 2  # espace global couvrant les 2 panneaux


# ─────────────────────────────────────────────
# COULEUR ARC-EN-CIEL
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


# ─────────────────────────────────────────────
# RENDU D'UN PANNEAU
# ─────────────────────────────────────────────

def set_pixel(pixels, lx, ly, r, g, b, alpha=1.0):
    """Pose un pixel en coordonnées locales du panneau."""
    lx, ly = int(round(lx)), int(round(ly))
    if not (0 <= lx < W and 0 <= ly < H):
        return
    idx = ly * W + lx
    pr, pg, pb = pixels[idx]
    pixels[idx] = (
        min(255, pr + int(r * alpha)),
        min(255, pg + int(g * alpha)),
        min(255, pb + int(b * alpha)),
    )


def draw_ball(pixels, gx, gy, panel_index, r, g, b, radius=2, alpha=1.0):
    """Dessine la boule en coordonnées globales sur un panneau local."""
    x_off = panel_index * W
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx*dx + dy*dy <= radius*radius:
                set_pixel(pixels, gx - x_off + dx, gy + dy, r, g, b, alpha)


def render_panel(panel_index, trail, gx, gy, color):
    pixels = [(0, 0, 0)] * (W * H)
    r, g, b = color
    x_off = panel_index * W

    # Traîne
    for i, (tx, ty) in enumerate(trail[:-1]):
        alpha = (i / max(1, len(trail))) * 0.65
        draw_ball(pixels, tx, ty, panel_index, r, g, b, radius=1, alpha=alpha * 0.5)
        set_pixel(pixels, tx - x_off, ty, r, g, b, alpha)

    # Boule principale
    draw_ball(pixels, gx, gy, panel_index, r, g, b, radius=2, alpha=1.0)

    return pixels


def pixels_to_png(pixels):
    img = Image.new("RGB", (W, H))
    img.putdata(pixels)
    out = BytesIO()
    img.save(out, format="PNG", optimize=False)
    return out.getvalue()


# ─────────────────────────────────────────────
# ÉTAT PARTAGÉ ENTRE LES DEUX PANNEAUX
# ─────────────────────────────────────────────

class SharedState:
    def __init__(self, speed, amplitude, frequency, trail_len):
        self.gx        = 2.0          # position X globale (0 → TOTAL_W)
        self.t         = 0.0          # temps pour la sinusoïde
        self.dir       = 1            # direction : +1 droite / -1 gauche
        self.hue       = 0.0
        self.trail     = []
        self.speed     = speed
        self.amplitude = amplitude
        self.frequency = frequency
        self.trail_len = trail_len

    def update(self):
        self.t   += self.speed * 0.04
        self.gx  += self.dir * self.speed * 0.3
        self.hue  = (self.hue + self.speed * 0.5) % 360

        # Rebond sur les bords
        if self.gx > TOTAL_W - 3: self.gx = TOTAL_W - 3; self.dir = -1
        if self.gx < 2:           self.gx = 2;            self.dir =  1

        gy = H / 2 + math.sin(self.t * self.frequency * 0.5) * self.amplitude
        self.trail.append((self.gx, gy))
        if len(self.trail) > self.trail_len + 1:
            self.trail.pop(0)

        return self.gx, gy


# ─────────────────────────────────────────────
# BOUCLES PAR PANNEAU
# ─────────────────────────────────────────────

async def run_panel(session, panel_index, state, fps):
    """Boucle de rendu pour un panneau (0 = gauche, 1 = droite)."""
    delay = 1.0 / fps
    while True:
        gx, gy = state.gx, (
            H / 2 + math.sin(state.t * state.frequency * 0.5) * state.amplitude
        )
        color = hsv_to_rgb(state.hue)
        pixels = render_panel(panel_index, state.trail, gx, gy, color)
        await session.send_png(pixels_to_png(pixels), delay=0.0)
        await asyncio.sleep(delay)


async def run_physics(state, fps):
    """Boucle de mise à jour physique (partagée)."""
    delay = 1.0 / fps
    while True:
        state.update()
        await asyncio.sleep(delay)


# ─────────────────────────────────────────────
# ANIMATION PRINCIPALE
# ─────────────────────────────────────────────

async def sine_ball_animation(
    duration=60.0,
    fps=20.0,
    speed=3.0,       # vitesse de déplacement (1–8)
    amplitude=8.0,   # amplitude de la sinusoïde en pixels (2–14)
    frequency=2.0,   # fréquence des oscillations (1–6)
    trail_len=5,     # longueur de la traîne (0–12)
):
    state = SharedState(speed, amplitude, frequency, trail_len)

    async with BleDisplaySession(MAC_LEFT)  as sess_left, \
               BleDisplaySession(MAC_RIGHT) as sess_right:

        print(f"Boule sinusoïdale sur 2 panneaux pendant {duration}s...")

        async def left_loop():
            t0 = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - t0 < duration:
                gx = state.gx
                gy = H / 2 + math.sin(state.t * state.frequency * 0.5) * state.amplitude
                color = hsv_to_rgb(state.hue)
                pixels = render_panel(0, state.trail, gx, gy, color)
                await sess_left.send_png(pixels_to_png(pixels), delay=0.0)
                await asyncio.sleep(1.0 / fps)

        async def right_loop():
            t0 = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - t0 < duration:
                gx = state.gx
                gy = H / 2 + math.sin(state.t * state.frequency * 0.5) * state.amplitude
                color = hsv_to_rgb(state.hue)
                pixels = render_panel(1, state.trail, gx, gy, color)
                await sess_right.send_png(pixels_to_png(pixels), delay=0.0)
                await asyncio.sleep(1.0 / fps)

        async def physics_loop():
            t0 = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - t0 < duration:
                state.update()
                await asyncio.sleep(1.0 / (fps * 2))  # physique 2x plus rapide

        await asyncio.gather(
            physics_loop(),
            left_loop(),
            right_loop(),
        )

    print("Animation terminée.")


asyncio.run(sine_ball_animation(
    duration=60.0,
    fps=20.0,
    speed=3.0,       # 1 lente → 8 rapide
    amplitude=8.0,   # 2 légère → 14 grande oscillation
    frequency=2.0,   # 1 lente → 6 rapide
    trail_len=5,     # 0 aucune → 12 longue
))
