import asyncio
from io import BytesIO
from PIL import Image
from bk_light.display_session import BleDisplaySession

W, H = 32, 32
COLOR = (255, 255, 255)


def build_blank_image(color):
    image = Image.new("RGB", (W, H), color)
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=False)
    return buffer.getvalue()


async def allumer_panel(mac_address):
    png_bytes = build_blank_image(COLOR)
    print("Connexion au panneau %s..." % mac_address)
    async with BleDisplaySession(mac_address) as session:
        await session.send_png(png_bytes)
    print("Panneau allume.")


def main():
    mac_address = input("Adresse MAC du panneau : ").strip()
    if not mac_address:
        print("Adresse MAC vide, arret.")
        return
    asyncio.run(allumer_panel(mac_address))


if __name__ == "__main__":
    main()
