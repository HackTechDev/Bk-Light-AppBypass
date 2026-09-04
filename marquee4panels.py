import asyncio
import time
from io import BytesIO

from PIL import Image

from bk_light.display_session import BleDisplaySession
from bk_light.fonts import resolve_font
from bk_light.text import build_text_bitmap

# pip install pynput
from pynput import keyboard

# Panneaux de gauche a droite
MAC_PANELS = [
    "FF:50:05:B7:03:C6",  # panneau 0 - gauche
    "2B:F4:CA:80:5D:A9",  # panneau 1
    "6F:E3:D9:1A:19:CA",  # panneau 2
    "76:BF:38:1E:71:88",  # panneau 3 - droite
]

W, H = 32, 32
NB = len(MAC_PANELS)
TOTAL_W = W * NB  # 128 px

TEXT = "ILARD HACKLAB GRAOULUG"
COLOR = (0, 200, 255)    # cyan
BACKGROUND = (0, 0, 0)
FONT_NAME = "aldopc"
FONT_SIZE = 16
SPEED = 2                # pixels deplaces par frame (droite vers gauche)
FPS = 20.0


# ─────────────────────────────────────────────
# CLAVIER (pynput — Echap pour quitter)
# ─────────────────────────────────────────────

state = {"running": True}


def on_press(key):
    if key == keyboard.Key.esc:
        state["running"] = False
        return False


def build_strip():
    font_path = resolve_font(FONT_NAME)
    bitmap = build_text_bitmap(
        text=TEXT,
        font_path=font_path,
        size=FONT_SIZE,
        spacing=1,
        color=COLOR,
        antialias=False,
    )
    bg = Image.new("RGB", bitmap.size, BACKGROUND)
    bg.paste(bitmap, mask=bitmap.split()[3])
    return bg


def make_panel_pngs(strip, scroll_x):
    canvas = Image.new("RGB", (TOTAL_W, H), BACKGROUND)
    ty = (H - strip.height) // 2
    canvas.paste(strip, (scroll_x, ty))
    pngs = []
    for i in range(NB):
        tile = canvas.crop((i * W, 0, (i + 1) * W, H))
        buf = BytesIO()
        tile.save(buf, format="PNG", optimize=False)
        pngs.append(buf.getvalue())
    return pngs


async def connect_all():
    sessions = [BleDisplaySession(mac) for mac in MAC_PANELS]
    await asyncio.gather(*[s.__aenter__() for s in sessions])
    return sessions


async def disconnect_all(sessions):
    await asyncio.gather(
        *[s.__aexit__(None, None, None) for s in sessions],
        return_exceptions=True,
    )


async def run():
    strip = build_strip()
    strip_w = strip.width
    delay = 1.0 / FPS
    scroll_x = TOTAL_W

    print("Connexion a %d panneaux..." % NB)
    sessions = await connect_all()
    print("Defilement '%s' sur %dx%d px a %d FPS, vitesse %d px/frame" % (
        TEXT, TOTAL_W, H, FPS, SPEED))
    print("Echap pour arreter.")

    try:
        while state["running"]:
            pngs = make_panel_pngs(strip, scroll_x)
            await asyncio.gather(*[
                sessions[i].send_png(pngs[i], delay=0.0)
                for i in range(NB)
            ])
            scroll_x -= SPEED
            if scroll_x < -strip_w:
                scroll_x = TOTAL_W
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
