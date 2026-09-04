import asyncio
from io import BytesIO
from PIL import Image
from bk_light.display_session import BleDisplaySession

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
GW = W * NB  # 128 px de large
GH = H       # 32 px de haut

FPS = 10.0
STAGNATION_LIMIT = 100   # frames sans changement avant reinit

# ─────────────────────────────────────────────
# 4 ORIENTATIONS DE GLISSEUR
# ─────────────────────────────────────────────
#
#  A (NW)   B (NE)   C (SE)   D (SW)
#  XXX      XXX      .X.      .X.
#  ..X      X..      ..X      X..
#  .X.      .X.      XXX      XXX
#
GLIDER_A = [(0,0),(1,0),(2,0),(2,1),(1,2)]
GLIDER_B = [(0,0),(1,0),(2,0),(0,1),(1,2)]
GLIDER_C = [(1,0),(2,1),(0,2),(1,2),(2,2)]
GLIDER_D = [(1,0),(0,1),(0,2),(1,2),(2,2)]

GLIDERS = [GLIDER_A, GLIDER_B, GLIDER_C, GLIDER_D]

# 12 glisseurs repartis sur 128x32, 4 orientations alternees
# (origine_x, origine_y, index_orientation)
SPAWN_POSITIONS = [
    (4,   2,  0),   # A
    (36,  2,  1),   # B
    (68,  2,  2),   # C
    (100, 2,  3),   # D
    (20,  13, 1),   # B
    (52,  13, 2),   # C
    (84,  13, 3),   # D
    (116, 13, 0),   # A
    (8,   25, 2),   # C
    (40,  25, 3),   # D
    (72,  25, 0),   # A
    (104, 25, 1),   # B
]


# ─────────────────────────────────────────────
# CLAVIER (pynput — Echap pour quitter)
# ─────────────────────────────────────────────

state = {"running": True}


def on_press(key):
    if key == keyboard.Key.esc:
        state["running"] = False
        return False


# ─────────────────────────────────────────────
# GRILLE
# ─────────────────────────────────────────────

def make_gliders():
    grid = [0] * (GW * GH)
    age  = [0] * (GW * GH)
    for ox, oy, gi in SPAWN_POSITIONS:
        for dx, dy in GLIDERS[gi]:
            x = (ox + dx) % GW
            y = (oy + dy) % GH
            idx = y * GW + x
            grid[idx] = 1
            age[idx]  = 1
    return grid, age


def step(grid, age):
    next_grid = [0] * (GW * GH)
    next_age  = [0] * (GW * GH)
    for y in range(GH):
        for x in range(GW):
            n = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    n += grid[((y + dy) % GH) * GW + ((x + dx) % GW)]
            idx = y * GW + x
            alive = grid[idx]
            if alive and n in (2, 3):
                next_grid[idx] = 1
                next_age[idx]  = age[idx] + 1
            elif not alive and n == 3:
                next_grid[idx] = 1
                next_age[idx]  = 1
    return next_grid, next_age


def population(grid):
    return sum(grid)


# ─────────────────────────────────────────────
# RENDU
# ─────────────────────────────────────────────

def cell_color(a):
    """Jeune = cyan vif, vieille = violet profond."""
    if a == 0:
        return (0, 0, 0)
    t = min(a, 20) / 20.0
    r = int(t * 160)
    g = int((1 - t) * 220 + t * 40)
    b = int(220 - t * 40)
    return (r, g, b)


def render_tiles(grid, age):
    pixels = [cell_color(age[i]) if grid[i] else (0, 0, 0) for i in range(GW * GH)]
    img = Image.new("RGB", (GW, GH))
    img.putdata(pixels)
    pngs = []
    for i in range(NB):
        tile = img.crop((i * W, 0, (i + 1) * W, GH))
        buf = BytesIO()
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


# ─────────────────────────────────────────────
# BOUCLE PRINCIPALE
# ─────────────────────────────────────────────

async def run():
    delay = 1.0 / FPS
    grid, age = make_gliders()
    stagnant = 0
    last_pop = population(grid)
    gen = 0

    print("Connexion a %d panneaux..." % NB)
    sessions = await connect_all()
    print("Jeu de la vie %dx%d - %d glisseurs - Echap pour arreter" % (
        GW, GH, len(SPAWN_POSITIONS)))

    try:
        while state["running"]:
            grid, age = step(grid, age)
            gen += 1

            pop = population(grid)
            if pop == last_pop:
                stagnant += 1
            else:
                stagnant = 0
                last_pop = pop

            if stagnant >= STAGNATION_LIMIT or pop == 0:
                print("  Gen %d - stagnation (%d cellules) - reinitialisation" % (gen, pop))
                grid, age = make_gliders()
                stagnant = 0
                last_pop = population(grid)
                gen = 0

            if gen % 50 == 0:
                print("  Gen %d - %d cellules vivantes" % (gen, pop))

            pngs = render_tiles(grid, age)
            await asyncio.gather(*[
                sessions[i].send_png(pngs[i], delay=0.0)
                for i in range(NB)
            ])
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
