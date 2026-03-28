import asyncio
import math
from io import BytesIO
from PIL import Image
from bk_light.display_session import BleDisplaySession

MAC_ADDRESS = "76:BF:38:1E:71:88"
W, H = 32, 32


def hsv_to_rgb(h, s=1.0, v=1.0):
    h = h % 360
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    if   h < 60:  r, g, b = c, x, 0
    elif h < 120: r, g, b = x, c, 0
    elif h < 180: r, g, b = 0, c, x
    elif h < 240: r, g, b = 0, x, c
    elif h < 300: r, g, b = x, 0, c
    else:         r, g, b = c, 0, x
    return (int((r+m)*255), int((g+m)*255), int((b+m)*255))


def ball_color(color_mode, hue):
    if color_mode == "cyan":    return (0, 200, 255)
    if color_mode == "red":     return (255, 60, 60)
    if color_mode == "green":   return (60, 255, 60)
    if color_mode == "white":   return (255, 255, 255)
    if color_mode == "rainbow": return hsv_to_rgb(hue)
    return (0, 200, 255)


def draw_ball(pixels, cx, cy, radius, color, alpha=1.0):
    r, g, b = color
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx*dx + dy*dy <= radius*radius:
                px, py = int(round(cx + dx)), int(round(cy + dy))
                if 0 <= px < W and 0 <= py < H:
                    idx = py * W + px
                    pr, pg, pb = pixels[idx]
                    pixels[idx] = (
                        min(255, pr + int(r * alpha)),
                        min(255, pg + int(g * alpha)),
                        min(255, pb + int(b * alpha)),
                    )


def render_frame(trail, bx, by, radius, color, trail_len):
    pixels = [(0, 0, 0)] * (W * H)

    # Traîne
    for i, (tx, ty) in enumerate(trail[:-1]):
        alpha = (i / max(1, len(trail))) * 0.5
        draw_ball(pixels, tx, ty, max(1, radius - 1), color, alpha)

    # Boule principale
    draw_ball(pixels, bx, by, radius, color, 1.0)

    return pixels


def pixels_to_png(pixels):
    img = Image.new("RGB", (W, H))
    img.putdata(pixels)
    out = BytesIO()
    img.save(out, format="PNG", optimize=False)
    return out.getvalue()


async def ball_animation(
    duration=30.0,
    fps=25.0,
    speed=3.0,       # vitesse de la boule (1–8)
    radius=5,        # rayon en pixels (1–5)
    trail_len=5,     # longueur de la traîne (0 = aucune)
    color_mode="cyan",  # "cyan" | "red" | "green" | "white" | "rainbow"
    angle=35,        # angle initial de départ en degrés
):
    # Vitesse initiale selon l'angle
    rad = math.radians(angle)
    vx = math.cos(rad) * speed * 0.15
    vy = math.sin(rad) * speed * 0.15

    bx, by = W / 2.0, H / 2.0
    hue = 0
    trail = []
    delay = 1.0 / fps

    async with BleDisplaySession(MAC_ADDRESS) as session:
        print(f"Boule rebondissante pendant {duration}s...")
        t0 = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - t0 < duration:
            hue = (hue + 3) % 360
            bx += vx
            by += vy

            # Rebonds sur les 4 bords
            if bx - radius <= 0:
                bx = radius
                vx = abs(vx)
            if bx + radius >= W - 1:
                bx = W - 1 - radius
                vx = -abs(vx)
            if by - radius <= 0:
                by = radius
                vy = abs(vy)
            if by + radius >= H - 1:
                by = H - 1 - radius
                vy = -abs(vy)

            trail.append((bx, by))
            if len(trail) > trail_len + 1:
                trail.pop(0)

            color = ball_color(color_mode, hue)
            pixels = render_frame(trail, bx, by, radius, color, trail_len)
            png = pixels_to_png(pixels)
            await session.send_png(png, delay=0.0)
            await asyncio.sleep(delay)

        print("Animation terminée.")


asyncio.run(ball_animation(
    duration=30.0,
    fps=25.0,
    speed=8.0,
    radius=5,
    trail_len=5,
    color_mode="cyan",   # "cyan" | "red" | "green" | "white" | "rainbow"
    angle=35,
))
