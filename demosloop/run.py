import asyncio
import os
import sys
import time
from io import BytesIO

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from bk_light.display_session import BleDisplaySession

# pip install pynput
from pynput import keyboard

from demosloop.common import MAC_PANELS, W, H, NB, GW, GH
from demosloop.effects import (
    metaballs,
    mandelbrot,
    lorenz,
    life,
    starfield,
    fire,
    fallingletters,
    fireworks,
    galaxy,
    cube3d,
    sandfall,
    waterfall,
    dropfall,
    marquee,
)

DUREE = 30.0

# Les 14 demos "Effets visuels" du menu, dans l'ordre (1 a 14).
EFFECTS = [
    ("Metaballs", metaballs),
    ("Mandelbrot", mandelbrot),
    ("Lorenz", lorenz),
    ("Jeu de la Vie", life),
    ("Etoiles", starfield),
    ("Feu", fire),
    ("Matrix", fallingletters),
    ("Feux d'artifice", fireworks),
    ("Galaxie", galaxy),
    ("Cube 3D", cube3d),
    ("Sable", sandfall),
    ("Cascade", waterfall),
    ("Gouttes", dropfall),
    ("Marquee", marquee),
]

state = {"running": True}


def on_press(key):
    if key == keyboard.Key.esc:
        state["running"] = False
        return False


async def connect_all():
    sessions = [BleDisplaySession(mac) for mac in MAC_PANELS]
    await asyncio.gather(*[s.__aenter__() for s in sessions])
    return sessions


async def disconnect_all(sessions):
    await asyncio.gather(
        *[s.__aexit__(None, None, None) for s in sessions],
        return_exceptions=True,
    )


def make_tiles(img):
    pngs = []
    for i in range(NB):
        tile = img.crop((i * W, 0, (i + 1) * W, GH))
        buf = BytesIO()
        tile.save(buf, format="PNG", optimize=False)
        pngs.append(buf.getvalue())
    return pngs


async def send_all(sessions, pngs):
    await asyncio.gather(*[
        sessions[i].send_png(pngs[i], delay=0.0)
        for i in range(NB)
    ])


async def run_loop():
    print("Connexion a %d panneaux..." % NB)
    sessions = await connect_all()
    print("demosloop -- %d demos Effets visuels, %.0fs chacune, enchainement sans reconnexion" % (
        len(EFFECTS), DUREE))
    print("Echap pour arreter.\n")

    try:
        while state["running"]:
            for name, effect in EFFECTS:
                if not state["running"]:
                    break
                print("=== %s (%.0fs) ===" % (name, DUREE))
                effect_state = effect.init_state()
                delay = 1.0 / effect.FPS
                t_end = time.monotonic() + DUREE
                while state["running"] and time.monotonic() < t_end:
                    img = effect.render(effect_state)
                    pngs = make_tiles(img)
                    await send_all(sessions, pngs)
                    await asyncio.sleep(delay)
    finally:
        await disconnect_all(sessions)
        print("Deconnecte.")


listener = keyboard.Listener(on_press=on_press)
listener.start()

asyncio.run(run_loop())

listener.stop()
