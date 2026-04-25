import asyncio
import random
from collections import deque
from io import BytesIO
from PIL import Image, ImageDraw
from bk_light.display_session import BleDisplaySession

# pip install pynput
from pynput import keyboard

# Panneaux de gauche a droite (meme config que life4panels.py)
MAC_PANELS = [
    "FF:50:05:B7:03:C6",  # panneau 0 - gauche
    "2B:F4:CA:80:5D:A9",  # panneau 1
    "6F:E3:D9:1A:19:CA",  # panneau 2
    "76:BF:38:1E:71:88",  # panneau 3 - droite
]

W, H = 32, 32
NB = len(MAC_PANELS)
GW = W * NB   # 128 px
GH = H        # 32 px

CELL = 2              # taille d'une cellule en pixels
COLS = GW // CELL     # 64 colonnes
ROWS = GH // CELL     # 16 lignes

INIT_LEN = 5
BASE_FPS = 8.0
MAX_FPS  = 22.0
FPS_STEP = 0.5        # gain de FPS par nourriture mangee

UP    = (0, -1)
DOWN  = (0,  1)
LEFT  = (-1, 0)
RIGHT = ( 1, 0)
REVERSE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}


# ─────────────────────────────────────────────
# ETAT PARTAGE CLAVIER <-> BOUCLE PRINCIPALE
# ─────────────────────────────────────────────

state = {
    "next_dir": RIGHT,
    "direction": RIGHT,
    "running": True,
}


def on_press(key):
    try:
        if key == keyboard.Key.up:
            new_dir = UP
        elif key == keyboard.Key.down:
            new_dir = DOWN
        elif key == keyboard.Key.left:
            new_dir = LEFT
        elif key == keyboard.Key.right:
            new_dir = RIGHT
        elif key == keyboard.Key.esc:
            state["running"] = False
            return False
        else:
            return
        # Interdit le demi-tour
        if new_dir != REVERSE.get(state["direction"]):
            state["next_dir"] = new_dir
    except Exception:
        pass


# ─────────────────────────────────────────────
# JEU
# ─────────────────────────────────────────────

class SnakeGame:
    def __init__(self):
        self.reset()

    def reset(self):
        cx, cy = COLS // 2, ROWS // 2
        self.body = deque()
        self.body_set = set()
        for i in range(INIT_LEN):
            pos = (cx - i, cy)
            self.body.append(pos)
            self.body_set.add(pos)
        self.grow  = 0
        self.score = 0
        self.place_food()

    def place_food(self):
        while True:
            pos = (random.randint(0, COLS - 1), random.randint(0, ROWS - 1))
            if pos not in self.body_set:
                self.food = pos
                break

    def step(self, direction):
        hx, hy = self.body[0]
        dx, dy  = direction
        new_head = ((hx + dx) % COLS, (hy + dy) % ROWS)

        danger = self.body_set if self.grow > 0 else self.body_set - {self.body[-1]}
        if new_head in danger:
            return False

        self.body.appendleft(new_head)
        self.body_set.add(new_head)

        if self.grow > 0:
            self.grow -= 1
        else:
            self.body_set.discard(self.body.pop())

        if new_head == self.food:
            self.score += 1
            self.grow  += 3
            self.place_food()

        return True


# ─────────────────────────────────────────────
# RENDU
# ─────────────────────────────────────────────

def body_color(idx, length):
    t = idx / max(1, length - 1)
    return (0, int(240 - t * 160), 0)


def make_tiles(canvas):
    pngs = []
    for i in range(NB):
        tile = canvas.crop((i * W, 0, (i + 1) * W, GH))
        buf  = BytesIO()
        tile.save(buf, format="PNG", optimize=False)
        pngs.append(buf.getvalue())
    return pngs


def render_game(game):
    canvas = Image.new("RGB", (GW, GH), (0, 0, 0))
    draw   = ImageDraw.Draw(canvas)

    body_list = list(game.body)
    n = len(body_list)

    for idx, (cx, cy) in enumerate(body_list):
        color = body_color(idx, n)
        px, py = cx * CELL, cy * CELL
        draw.rectangle([px, py, px + CELL - 1, py + CELL - 1], fill=color)

    if body_list:
        hx, hy = body_list[0]
        px, py = hx * CELL, hy * CELL
        draw.rectangle([px, py, px + CELL - 1, py + CELL - 1], fill=(255, 255, 80))

    fx, fy = game.food
    px, py = fx * CELL, fy * CELL
    draw.rectangle([px, py, px + CELL - 1, py + CELL - 1], fill=(255, 40, 40))

    return make_tiles(canvas)


def render_flash(color):
    return make_tiles(Image.new("RGB", (GW, GH), color))


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


async def send_all(sessions, pngs):
    await asyncio.gather(*[
        sessions[i].send_png(pngs[i], delay=0.0)
        for i in range(NB)
    ])


# ─────────────────────────────────────────────
# BOUCLE PRINCIPALE
# ─────────────────────────────────────────────

async def snake_loop():
    print("Connexion a %d panneaux..." % NB)
    sessions = await connect_all()
    print("Snake - grille %dx%d cellules de %dpx (%dx%d px total)" % (
        COLS, ROWS, CELL, GW, GH))
    print("Fleches directionnelles pour jouer, Echap pour quitter.\n")

    game = SnakeGame()
    fps  = BASE_FPS

    try:
        while state["running"]:
            direction = state["next_dir"]
            state["direction"] = direction

            alive = game.step(direction)

            if not alive:
                print("Game over !  Score : %d" % game.score)
                flash = render_flash((150, 0, 0))
                for _ in range(5):
                    await send_all(sessions, flash)
                    await asyncio.sleep(0.1)
                game.reset()
                state["next_dir"]  = RIGHT
                state["direction"] = RIGHT
                fps = BASE_FPS
            else:
                fps  = min(MAX_FPS, BASE_FPS + game.score * FPS_STEP)
                pngs = render_game(game)
                await send_all(sessions, pngs)

            await asyncio.sleep(1.0 / fps)

    finally:
        await disconnect_all(sessions)
        print("Deconnecte.")


listener = keyboard.Listener(on_press=on_press)
listener.start()

asyncio.run(snake_loop())

listener.stop()
