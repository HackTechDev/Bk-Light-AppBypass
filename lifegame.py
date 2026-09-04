import asyncio
import random
from io import BytesIO
from PIL import Image
from bk_light.display_session import BleDisplaySession

# pip install pynput
from pynput import keyboard

MAC_ADDRESS = "76:BF:38:1E:71:88"
W, H = 32, 32

state = {"running": True}


def on_press(key):
    if key == keyboard.Key.esc:
        state["running"] = False
        return False


# ─────────────────────────────────────────────
# PATTERNS PRÉDÉFINIS
# ─────────────────────────────────────────────

GLIDER = [(0,0),(1,0),(2,0),(2,1),(1,2)]

PULSAR = [
    (2,0),(3,0),(4,0),(8,0),(9,0),(10,0),
    (0,2),(5,2),(7,2),(12,2),(0,3),(5,3),(7,3),(12,3),
    (0,4),(5,4),(7,4),(12,4),(2,5),(3,5),(4,5),(8,5),(9,5),(10,5),
    (2,7),(3,7),(4,7),(8,7),(9,7),(10,7),
    (0,8),(5,8),(7,8),(12,8),(0,9),(5,9),(7,9),(12,9),
    (0,10),(5,10),(7,10),(12,10),(2,12),(3,12),(4,12),(8,12),(9,12),(10,12),
]

R_PENTOMINO = [(1,0),(2,0),(0,1),(1,1),(1,2)]

DIEHARD = [
    (6,0),(0,1),(1,1),(1,2),(5,2),(6,2),(7,2)
]


def make_random(density=0.30):
    grid = [0] * (W * H)
    age  = [0] * (W * H)
    for i in range(W * H):
        if random.random() < density:
            grid[i] = 1
            age[i]  = 1
    return grid, age


def make_pattern(pattern, ox=0, oy=0):
    grid = [0] * (W * H)
    age  = [0] * (W * H)
    for dx, dy in pattern:
        x = (ox + dx) % W
        y = (oy + dy) % H
        grid[y * W + x] = 1
        age[y * W + x]  = 1
    return grid, age


# ─────────────────────────────────────────────
# RÈGLES DU JEU DE LA VIE
# ─────────────────────────────────────────────

def step_life(grid, age):
    next_grid = [0] * (W * H)
    next_age  = [0] * (W * H)
    for y in range(H):
        for x in range(W):
            n = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    n += grid[((y+dy) % H) * W + ((x+dx) % W)]
            alive = grid[y * W + x]
            if alive and n in (2, 3):
                next_grid[y * W + x] = 1
                next_age[y * W + x]  = age[y * W + x] + 1
            elif not alive and n == 3:
                next_grid[y * W + x] = 1
                next_age[y * W + x]  = 1
    return next_grid, next_age


def population(grid):
    return sum(grid)


# ─────────────────────────────────────────────
# COULEUR PAR ÂGE
# ─────────────────────────────────────────────

def cell_color(a):
    """Jeune = cyan vif → vieille = violet profond."""
    if a == 0:
        return (0, 0, 0)
    t = min(a, 20) / 20.0
    r = int(t * 160)
    g = int((1 - t) * 220 + t * 40)
    b = int(220 - t * 40)
    return (r, g, b)


def render(grid, age):
    pixels = [cell_color(age[i]) if grid[i] else (0, 0, 0) for i in range(W * H)]
    img = Image.new("RGB", (W, H))
    img.putdata(pixels)
    out = BytesIO()
    img.save(out, format="PNG", optimize=False)
    return out.getvalue()


# ─────────────────────────────────────────────
# ANIMATION PRINCIPALE
# ─────────────────────────────────────────────

async def game_of_life(
    duration=120.0,
    fps=10.0,
    density=0.30,          # densité initiale aléatoire (0.1–0.5)
    stagnation_limit=40,   # regénère si stagnant N frames
    mode="random",         # "random" | "glider" | "pulsar" | "r_pentomino" | "diehard"
):
    # Initialisation selon le mode
    if mode == "glider":
        grid, age = make_pattern(GLIDER, ox=2, oy=2)
    elif mode == "pulsar":
        grid, age = make_pattern(PULSAR, ox=9, oy=9)
    elif mode == "r_pentomino":
        grid, age = make_pattern(R_PENTOMINO, ox=14, oy=14)
    elif mode == "diehard":
        grid, age = make_pattern(DIEHARD, ox=12, oy=14)
    else:
        grid, age = make_random(density)

    delay = 1.0 / fps
    stagnant = 0
    last_pop = population(grid)

    async with BleDisplaySession(MAC_ADDRESS) as session:
        print(f"Jeu de la vie — mode '{mode}' pendant {duration}s... (Echap pour arreter)")
        t0 = asyncio.get_event_loop().time()
        while state["running"] and asyncio.get_event_loop().time() - t0 < duration:
            grid, age = step_life(grid, age)

            # Détection de stagnation → nouvelle grille aléatoire
            pop = population(grid)
            if pop == last_pop:
                stagnant += 1
            else:
                stagnant = 0
                last_pop = pop

            if stagnant >= stagnation_limit or pop == 0:
                print(f"  Stagnation détectée ({pop} cellules) → nouvelle grille")
                grid, age = make_random(density)
                stagnant = 0
                last_pop = population(grid)

            png = render(grid, age)
            await session.send_png(png, delay=0.0)
            await asyncio.sleep(delay)

        print("Animation terminée.")


listener = keyboard.Listener(on_press=on_press)
listener.start()

asyncio.run(game_of_life(
    duration=120.0,
    fps=10.0,
    density=0.30,
    stagnation_limit=40,
    mode="random",   # "random" | "glider" | "pulsar" | "r_pentomino" | "diehard"
))

listener.stop()
