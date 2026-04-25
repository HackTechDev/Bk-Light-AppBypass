import asyncio
import random
from io import BytesIO
from PIL import Image, ImageDraw
from bk_light.display_session import BleDisplaySession
from pynput import keyboard

MAC_PANELS = [
    "FF:50:05:B7:03:C6",
    "2B:F4:CA:80:5D:A9",
    "6F:E3:D9:1A:19:CA",
    "76:BF:38:1E:71:88",
]

W, H = 32, 32
NB = len(MAC_PANELS)
GW = W * NB   # 128 px
GH = H        # 32 px

# Briques : 16 colonnes x 7px + 1px gap = 128px exactement
BRICK_COLS  = 16
BRICK_ROWS  = 3
BRICK_W     = 7
BRICK_H     = 3
BRICK_GAP   = 1
BRICK_TOP   = 1     # y de la premiere rangee

PADDLE_W    = 14
PADDLE_H    = 2
PADDLE_Y    = 29
PADDLE_SPD  = 3

BALL_SIZE   = 2
BALL_VX0    = 1.5
BALL_VY0    = 2.0
BALL_VX_MAX = 3.0
BALL_VY_MAX = 3.5

LIVES_INIT  = 3
FPS         = 20.0

ROW_SCORES  = [30, 20, 10]
BRICK_COLORS = [
    (255,  60,  60),   # rouge  (rangee haute)
    (255, 155,   0),   # orange
    ( 50, 200,  50),   # vert   (rangee basse)
]

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


def draw_digit(draw, ch, x, y, color):
    for ri, row in enumerate(FONT_3X5.get(ch, FONT_3X5['0'])):
        for ci, bit in enumerate(row):
            if bit == '1':
                draw.point((x + ci, y + ri), fill=color)


def brick_rect(row, col):
    """Retourne (x1, y1, x2, y2) inclusifs."""
    x = col * (BRICK_W + BRICK_GAP)
    y = BRICK_TOP + row * (BRICK_H + BRICK_GAP)
    return (x, y, x + BRICK_W - 1, y + BRICK_H - 1)


# ─────────────────────────────────────────────
# CLAVIER
# ─────────────────────────────────────────────

state = {
    'left':    False,
    'right':   False,
    'launch':  False,
    'running': True,
}


def on_press(key):
    if key == keyboard.Key.left:
        state['left'] = True
    elif key == keyboard.Key.right:
        state['right'] = True
    elif key in (keyboard.Key.space, keyboard.Key.up):
        state['launch'] = True
    elif key == keyboard.Key.esc:
        state['running'] = False
        return False


def on_release(key):
    if key == keyboard.Key.left:
        state['left'] = False
    elif key == keyboard.Key.right:
        state['right'] = False


# ─────────────────────────────────────────────
# JEU
# ─────────────────────────────────────────────

class BreakoutGame:
    def __init__(self):
        self.speed_bonus = 0.0
        self.reset_game()

    def reset_game(self):
        self.lives       = LIVES_INIT
        self.score       = 0
        self.speed_bonus = 0.0
        self.paddle_x    = float(GW // 2 - PADDLE_W // 2)
        self.bricks      = [[True] * BRICK_COLS for _ in range(BRICK_ROWS)]
        self._reset_ball()

    def new_round(self):
        self.speed_bonus = min(self.speed_bonus + 0.3, 1.5)
        self.bricks = [[True] * BRICK_COLS for _ in range(BRICK_ROWS)]
        self._reset_ball()

    def _reset_ball(self):
        self.bx       = float(GW // 2 - BALL_SIZE // 2)
        self.by       = float(PADDLE_Y - BALL_SIZE - 2)
        self.vx       = random.choice([-BALL_VX0, BALL_VX0])
        self.vy       = -(BALL_VY0 + self.speed_bonus)
        self.launched = False

    def move_paddle(self, dx):
        self.paddle_x = max(0.0, min(float(GW - PADDLE_W), self.paddle_x + dx * PADDLE_SPD))

    def _all_clear(self):
        return not any(self.bricks[r][c] for r in range(BRICK_ROWS) for c in range(BRICK_COLS))

    def step(self):
        if not self.launched:
            self.bx = self.paddle_x + PADDLE_W / 2.0 - BALL_SIZE / 2.0
            return 'waiting'

        prev_by = self.by
        self.bx += self.vx
        self.by += self.vy

        # Rebonds murs
        if self.bx <= 0:
            self.bx = 0.0
            self.vx = abs(self.vx)
        elif self.bx + BALL_SIZE >= GW:
            self.bx = float(GW - BALL_SIZE)
            self.vx = -abs(self.vx)

        if self.by <= 0:
            self.by = 0.0
            self.vy = abs(self.vy)

        # Collision briques (AABB + determination du cote touche)
        bx2, by2 = self.bx + BALL_SIZE, self.by + BALL_SIZE
        for row in range(BRICK_ROWS):
            for col in range(BRICK_COLS):
                if not self.bricks[row][col]:
                    continue
                rx, ry, rx2, ry2 = brick_rect(row, col)
                rx2 += 1
                ry2 += 1   # passage en coordonnees exclusives
                if bx2 <= rx or self.bx >= rx2 or by2 <= ry or self.by >= ry2:
                    continue
                ov_x = min(bx2, rx2) - max(self.bx, rx)
                ov_y = min(by2, ry2) - max(self.by, ry)
                if ov_x < ov_y:
                    self.vx = -self.vx
                else:
                    self.vy = -self.vy
                self.bricks[row][col] = False
                self.score += ROW_SCORES[row]
                if self._all_clear():
                    return 'win'
                return 'brick'

        # Collision raquette
        px = int(self.paddle_x)
        if (self.vy > 0
                and self.by + BALL_SIZE >= PADDLE_Y
                and prev_by + BALL_SIZE < PADDLE_Y
                and self.bx + BALL_SIZE > px
                and self.bx < px + PADDLE_W):
            self.by = float(PADDLE_Y - BALL_SIZE)
            hit = ((self.bx + BALL_SIZE / 2.0) - (px + PADDLE_W / 2.0)) / (PADDLE_W / 2.0)
            self.vy = -max(abs(self.vy), BALL_VY0)
            self.vy = max(-BALL_VY_MAX, self.vy)
            new_vx = hit * BALL_VX_MAX * 0.85
            if abs(new_vx) < 0.4:
                new_vx = 0.4 * (1 if self.vx >= 0 else -1)
            self.vx = new_vx
            return 'paddle'

        # Balle perdue
        if self.by > GH:
            self.lives -= 1
            if self.lives <= 0:
                return 'game_over'
            self._reset_ball()
            return 'lost_ball'

        return 'playing'


# ─────────────────────────────────────────────
# RENDU
# ─────────────────────────────────────────────

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

    # Briques
    for row in range(BRICK_ROWS):
        color = BRICK_COLORS[row]
        for col in range(BRICK_COLS):
            if game.bricks[row][col]:
                rx, ry, rx2, ry2 = brick_rect(row, col)
                draw.rectangle([rx, ry, rx2, ry2], fill=color)

    # Score (coin bas-droit, jaune, police 3x5, y=25-29)
    score_str = str(min(game.score, 9999))
    sx_base = GW - 4 * len(score_str) - 1
    for i, ch in enumerate(score_str):
        draw_digit(draw, ch, sx_base + i * 4, 25, (220, 200, 0))

    # Raquette (cyan)
    px = int(game.paddle_x)
    draw.rectangle([px, PADDLE_Y, px + PADDLE_W - 1, PADDLE_Y + PADDLE_H - 1], fill=(0, 200, 255))

    # Balle (blanche)
    bx, by = int(game.bx), int(game.by)
    draw.rectangle([bx, by, bx + BALL_SIZE - 1, by + BALL_SIZE - 1], fill=(255, 255, 255))

    # Vies (petits points rouges, y=31)
    for i in range(game.lives):
        draw.rectangle([2 + i * 4, 31, 3 + i * 4, 31], fill=(255, 80, 80))

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

async def game_loop():
    print("Connexion a %d panneaux..." % NB)
    sessions = await connect_all()
    print("Breakout %dx%d px | Gauche/Droite : raquette  Espace/Haut : lancer  Echap : quitter" % (GW, GH))
    print("Briques : rouge=30pts  orange=20pts  vert=10pts\n")

    game  = BreakoutGame()
    delay = 1.0 / FPS

    try:
        while state['running']:
            dx = 0
            if state['left'] and not state['right']:
                dx = -1
            elif state['right'] and not state['left']:
                dx = 1

            if dx != 0:
                game.move_paddle(dx)

            if state['launch'] and not game.launched:
                game.launched   = True
                state['launch'] = False

            result = game.step()

            if result == 'brick':
                print("\rScore : %-5d  Vies : %d" % (game.score, game.lives), end='', flush=True)

            elif result == 'lost_ball':
                print("\n  Balle perdue !  Vies restantes : %d" % game.lives)
                flash = render_flash((70, 0, 0))
                for _ in range(6):
                    await send_all(sessions, flash)
                    await asyncio.sleep(0.1)
                await asyncio.sleep(0.5)

            elif result == 'game_over':
                print("\n  GAME OVER  Score final : %d" % game.score)
                flash = render_flash((110, 0, 0))
                for _ in range(12):
                    await send_all(sessions, flash)
                    await asyncio.sleep(0.08)
                await asyncio.sleep(0.5)
                game.reset_game()

            elif result == 'win':
                bonus = game.speed_bonus
                print("\n  BRAVO ! Toutes les briques ! Score : %d  (vitesse +%.1f)" % (game.score, bonus + 0.3))
                flash = render_flash((0, 100, 0))
                for _ in range(10):
                    await send_all(sessions, flash)
                    await asyncio.sleep(0.1)
                await asyncio.sleep(0.3)
                game.new_round()

            pngs = render_game(game)
            await send_all(sessions, pngs)
            await asyncio.sleep(delay)

    finally:
        await disconnect_all(sessions)
        print("\nDeconnecte. Score final : %d" % game.score)


listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

asyncio.run(game_loop())

listener.stop()
