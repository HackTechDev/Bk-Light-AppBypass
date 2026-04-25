import asyncio
import random
from io import BytesIO
from PIL import Image, ImageDraw
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
GW = W * NB   # 128 px
GH = H        # 32 px

PADDLE_W = 2
PADDLE_H = 6
BALL_SIZE = 2

PL_X = 3               # bord gauche de la raquette joueur
AI_X = GW - 3 - PADDLE_W   # bord gauche de la raquette IA

PLAYER_SPEED = 2
AI_SPEED     = 2

BALL_VX_BASE = 2.0
BALL_VY_BASE = 1.5
BALL_VX_MAX  = 5.0
BALL_VY_MAX  = 3.5

FPS       = 25.0
WIN_SCORE = 7          # points pour gagner un set


# ─────────────────────────────────────────────
# CLAVIER (pynput — touches maintenues)
# ─────────────────────────────────────────────

state = {
    "up":      False,
    "down":    False,
    "running": True,
}


def on_press(key):
    if key == keyboard.Key.up:
        state["up"] = True
    elif key == keyboard.Key.down:
        state["down"] = True
    elif key == keyboard.Key.esc:
        state["running"] = False
        return False


def on_release(key):
    if key == keyboard.Key.up:
        state["up"] = False
    elif key == keyboard.Key.down:
        state["down"] = False


# ─────────────────────────────────────────────
# POLICE 3x5 POUR L'AFFICHAGE DU SCORE
# ─────────────────────────────────────────────

FONT_3X5 = {
    '0': ['111','101','101','101','111'],
    '1': ['010','110','010','010','111'],
    '2': ['111','001','111','100','111'],
    '3': ['111','001','111','001','111'],
    '4': ['101','101','111','001','001'],
    '5': ['111','100','111','001','111'],
    '6': ['111','100','111','101','111'],
    '7': ['111','001','001','001','001'],
    '8': ['111','101','111','101','111'],
    '9': ['111','101','111','001','111'],
}


def draw_digit(draw, char, x, y, color):
    rows = FONT_3X5.get(char, FONT_3X5['0'])
    for row_idx, row in enumerate(rows):
        for col_idx, bit in enumerate(row):
            if bit == '1':
                draw.point((x + col_idx, y + row_idx), fill=color)


# ─────────────────────────────────────────────
# JEU
# ─────────────────────────────────────────────

class PongGame:
    def __init__(self):
        self.pl_y  = (GH - PADDLE_H) // 2
        self.ai_y  = (GH - PADDLE_H) // 2
        self.score_pl = 0
        self.score_ai = 0
        self.reset_ball(1)

    def reset_ball(self, direction=1):
        """direction: +1 vers IA, -1 vers joueur."""
        self.bx = float(GW // 2 - BALL_SIZE // 2)
        self.by = float(GH // 2 - BALL_SIZE // 2)
        self.vx = BALL_VX_BASE * direction
        self.vy = random.choice([-BALL_VY_BASE, BALL_VY_BASE])

    def move_player(self, dy):
        self.pl_y = max(0, min(GH - PADDLE_H, self.pl_y + dy))

    def move_ai(self):
        ball_cy = self.by + BALL_SIZE / 2.0
        ai_cy   = self.ai_y + PADDLE_H / 2.0
        diff    = ball_cy - ai_cy
        # Vitesse limitee + leger flou pour etre battable
        move = max(-AI_SPEED, min(AI_SPEED, diff * 0.85))
        self.ai_y = max(0, min(GH - PADDLE_H, self.ai_y + int(move)))

    def step(self):
        self.bx += self.vx
        self.by += self.vy

        # Rebond haut / bas
        if self.by <= 0:
            self.by = 0.0
            self.vy = abs(self.vy)
        if self.by + BALL_SIZE >= GH:
            self.by = float(GH - BALL_SIZE)
            self.vy = -abs(self.vy)

        # Collision raquette joueur (gauche)
        if (self.vx < 0
                and self.bx <= PL_X + PADDLE_W
                and self.bx + BALL_SIZE > PL_X
                and self.by + BALL_SIZE > self.pl_y
                and self.by < self.pl_y + PADDLE_H):
            self.bx = float(PL_X + PADDLE_W)
            hit = ((self.by + BALL_SIZE / 2.0) - (self.pl_y + PADDLE_H / 2.0)) / (PADDLE_H / 2.0)
            self.vx =  min(abs(self.vx) + 0.3, BALL_VX_MAX)
            self.vy =  hit * BALL_VY_MAX * 0.85

        # Collision raquette IA (droite)
        if (self.vx > 0
                and self.bx + BALL_SIZE >= AI_X
                and self.bx < AI_X + PADDLE_W
                and self.by + BALL_SIZE > self.ai_y
                and self.by < self.ai_y + PADDLE_H):
            self.bx = float(AI_X - BALL_SIZE)
            hit = ((self.by + BALL_SIZE / 2.0) - (self.ai_y + PADDLE_H / 2.0)) / (PADDLE_H / 2.0)
            self.vx = -min(abs(self.vx) + 0.3, BALL_VX_MAX)
            self.vy =  hit * BALL_VY_MAX * 0.85

        # Balle sortie a gauche -> IA marque
        if self.bx + BALL_SIZE < 0:
            self.score_ai += 1
            return 'ai_scores'

        # Balle sortie a droite -> joueur marque
        if self.bx > GW:
            self.score_pl += 1
            return 'player_scores'

        return 'playing'


# ─────────────────────────────────────────────
# RENDU
# ─────────────────────────────────────────────

COLOR_PLAYER = (0, 200, 255)    # cyan
COLOR_AI     = (255, 120, 0)    # orange
COLOR_BALL   = (255, 255, 255)  # blanc
COLOR_CENTER = (35, 35, 35)     # gris sombre


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

    # Ligne centrale pointillee
    cx = GW // 2
    for y in range(0, GH, 3):
        draw.point((cx, y), fill=COLOR_CENTER)

    # Scores (police 3x5)
    draw_digit(draw, str(min(game.score_pl, 9)), cx - 10, 2, COLOR_PLAYER)
    draw_digit(draw, str(min(game.score_ai, 9)), cx +  7, 2, COLOR_AI)

    # Raquette joueur (gauche, cyan)
    draw.rectangle(
        [PL_X, game.pl_y, PL_X + PADDLE_W - 1, game.pl_y + PADDLE_H - 1],
        fill=COLOR_PLAYER,
    )

    # Raquette IA (droite, orange)
    draw.rectangle(
        [AI_X, game.ai_y, AI_X + PADDLE_W - 1, game.ai_y + PADDLE_H - 1],
        fill=COLOR_AI,
    )

    # Balle
    bxi, byi = int(game.bx), int(game.by)
    draw.rectangle(
        [bxi, byi, bxi + BALL_SIZE - 1, byi + BALL_SIZE - 1],
        fill=COLOR_BALL,
    )

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

async def pong_loop():
    print("Connexion a %d panneaux..." % NB)
    sessions = await connect_all()
    print("Pong %dx%d px  |  Joueur (cyan) vs IA (orange)" % (GW, GH))
    print("Fleches Haut/Bas pour deplacer la raquette, Echap pour quitter.\n")

    game = PongGame()
    delay = 1.0 / FPS

    try:
        while state["running"]:
            # Deplacement raquette joueur (touche maintenue)
            if state["up"] and not state["down"]:
                game.move_player(-PLAYER_SPEED)
            elif state["down"] and not state["up"]:
                game.move_player(PLAYER_SPEED)

            # Deplacement raquette IA
            game.move_ai()

            # Physique balle
            result = game.step()

            if result in ('ai_scores', 'player_scores'):
                if result == 'ai_scores':
                    print("\r  %d - %d  (IA marque)       " % (game.score_pl, game.score_ai), end='', flush=True)
                    serve_dir = -1  # balle vers joueur
                else:
                    print("\r  %d - %d  (Joueur marque)   " % (game.score_pl, game.score_ai), end='', flush=True)
                    serve_dir = 1   # balle vers IA

                # Detection victoire
                winner = None
                if game.score_ai >= WIN_SCORE:
                    winner = 'ai'
                elif game.score_pl >= WIN_SCORE:
                    winner = 'player'

                if winner:
                    if winner == 'player':
                        print("\n  *** VOUS GAGNEZ (%d-%d) ! Nouveau set. ***" % (game.score_pl, game.score_ai))
                        flash_color = (0, 100, 180)
                    else:
                        print("\n  *** L'IA GAGNE (%d-%d) ! Nouveau set. ***" % (game.score_pl, game.score_ai))
                        flash_color = (150, 50, 0)
                    flash = render_flash(flash_color)
                    for _ in range(10):
                        await send_all(sessions, flash)
                        await asyncio.sleep(0.1)
                    game.score_pl = 0
                    game.score_ai = 0

                # Pause avant prochain service
                game.reset_ball(serve_dir)
                for _ in range(int(FPS * 0.8)):
                    await send_all(sessions, render_game(game))
                    await asyncio.sleep(delay)

            else:
                await send_all(sessions, render_game(game))
                await asyncio.sleep(delay)

    finally:
        await disconnect_all(sessions)
        print("\nDeconnecte.")


listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

asyncio.run(pong_loop())

listener.stop()
