import asyncio
from io import BytesIO
from PIL import Image
from bk_light.display_session import BleDisplaySession

# Dimensions du panneau (32x32 ou 64x16 selon votre modèle)
PANEL_W, PANEL_H = 32, 32
MAC_ADDRESS = "76:BF:38:1E:71:88"  # Adresse MAC de votre panneau

def build_image_with_pixel(x: int, y: int, color: tuple) -> bytes:
    """
    Crée une image noire avec un seul pixel coloré aux coordonnées (x, y).
    color : tuple RGB, ex. (255, 0, 0) pour rouge
    """
    image = Image.new("RGB", (PANEL_W, PANEL_H), (0, 0, 0))  # fond noir
    image.putpixel((x, y), color)                             # pixel coloré

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=False)
    return buffer.getvalue()

async def display_pixel(x: int, y: int, color: tuple = (255, 255, 255)):
    png_bytes = build_image_with_pixel(x, y, color)
    async with BleDisplaySession(MAC_ADDRESS) as session:
        await session.send_png(png_bytes)
    print(f"Pixel affiché en ({x}, {y}) avec la couleur {color}")

# Exemple : pixel vert au centre du panneau
asyncio.run(display_pixel(x=16, y=16, color=(255, 0, 0)))
