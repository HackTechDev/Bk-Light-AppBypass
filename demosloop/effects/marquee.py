from PIL import Image
from bk_light.fonts import resolve_font
from bk_light.text import build_text_bitmap
from demosloop.common import GW, GH

FPS = 20.0
SPEED = 2
TEXT = "ILARD HACKLAB GRAOULUG"
COLOR = (0, 200, 255)
BACKGROUND = (0, 0, 0)
FONT_NAME = "aldopc"
FONT_SIZE = 16


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


def init_state():
    return {"strip": build_strip(), "scroll_x": GW}


def render(state):
    strip = state["strip"]
    canvas = Image.new("RGB", (GW, GH), BACKGROUND)
    ty = (GH - strip.height) // 2
    canvas.paste(strip, (state["scroll_x"], ty))

    state["scroll_x"] -= SPEED
    if state["scroll_x"] < -strip.width:
        state["scroll_x"] = GW

    return canvas
