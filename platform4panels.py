import asyncio
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

GRAVITY    = 0.45
JUMP_VY    = -4.2
WALK_SPEED = 2
MAX_FALL   = 5.0
FPS        = 20.0
ANIM_SPEED = 4   # game frames per animation step

# Sprite pixel palette
PAL = {
    '.': None,
    'R': (90,  55,  15),
    'H': (255, 200, 120),
    'E': (20,  20,  100),
    'B': (50,  130, 255),
    'L': (65,  55,  30),
    'S': (35,  35,  35),
}

# 3 walk frames facing right, 8x8 pixels each
_RAW_FRAMES_R = [
    ['.RRRR...',
     '.HHEH...',
     '.HHHH...',
     '..BB....',
     '.BBBB...',
     '..BB....',
     '.LL.LL..',
     '.SS.SS..'],

    ['.RRRR...',
     '.HHEH...',
     '.HHHH...',
     '..BB....',
     '.BBBB...',
     '..BB....',
     '.LLLL...',
     '.S....S.'],

    ['.RRRR...',
     '.HHEH...',
     '.HHHH...',
     '..BB....',
     '.BBBB...',
     '..BB....',
     '...LLLL.',
     '.S....S.'],
]


def _parse_frame(rows):
    px = []
    for row in rows:
        for ch in row:
            px.append(PAL[ch])
    return px


def _mirror_frame(px):
    result = []
    for r in range(8):
        result.extend(reversed(px[r * 8:(r + 1) * 8]))
    return result


FRAMES_R = [_parse_frame(rows) for rows in _RAW_FRAMES_R]
FRAMES_L = [_mirror_frame(f) for f in FRAMES_R]

# Platforms: (x1, x2, surf_y)  — surf_y is the top surface pixel row
PLATFORMS = [
    (0,   127, 30),   # floor
    (5,   40,  22),   # left mid
    (55,  90,  22),   # center mid
    (95,  127, 22),   # right mid
    (20,  55,  14),   # left high
    (78,  113, 14),   # right high
]

# Collectibles: (cx, cy) top-left corner of a 2x2 gold pixel
COLL_INIT = [
    (25, 27), (50, 27), (80, 27), (110, 27),
    (12, 19), (32, 19), (62, 19), (78, 19), (108, 19),
    (30, 11), (45, 11), (88,  11),
]

FLOOR_COL    = (50, 55, 50)
PLATFORM_COL = (80, 60, 30)
COLL_COL_A   = (255, 220,  20)
COLL_COL_B   = (160, 130,   0)

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
    rows = FONT_3X5.get(ch, FONT_3X5['0'])
    for ri, row in enumerate(rows):
        for ci, bit in enumerate(row):
            if bit == '1':
                draw.point((x + ci, y + ri), fill=color)


# ─────────────────────────────────────────────
# CLAVIER
# ─────────────────────────────────────────────

state = {
    'left':    False,
    'right':   False,
    'jump':    False,
    'running': True,
}


def on_press(key):
    if key == keyboard.Key.left:
        state['left'] = True
    elif key == keyboard.Key.right:
        state['right'] = True
    elif key == keyboard.Key.up:
        state['jump'] = True
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

class Player:
    def __init__(self):
        self.x          = 5.0
        self.y          = 22.0   # feet at y+8 = 30 = floor surface
        self.vy         = 0.0
        self.on_ground  = False
        self.facing     = 1      # 1 = right, -1 = left
        self.anim_tick  = 0
        self.anim_frame = 0
        self.score      = 0
        self.collectibles = list(COLL_INIT)

    def update(self, dx, jump):
        # Horizontal
        if dx != 0:
            self.facing = dx
            self.x = max(0.0, min(float(GW - 8), self.x + dx * WALK_SPEED))
            self.anim_tick += 1
            if self.anim_tick >= ANIM_SPEED:
                self.anim_tick  = 0
                self.anim_frame = (self.anim_frame + 1) % 3
        else:
            self.anim_frame = 0
            self.anim_tick  = 0

        # Jump (one-shot: consumed by caller before this call)
        if jump and self.on_ground:
            self.vy        = JUMP_VY
            self.on_ground = False

        # Gravity
        self.vy = min(self.vy + GRAVITY, MAX_FALL)

        # Vertical movement + sweep platform collision
        prev_feet = self.y + 8.0
        self.y   += self.vy
        new_feet  = self.y + 8.0

        self.on_ground = False
        if self.vy >= 0:
            px = int(self.x)
            for (x1, x2, sy) in PLATFORMS:
                if px + 8 > x1 and px <= x2:
                    if prev_feet <= sy <= new_feet:
                        self.y         = float(sy - 8)
                        self.vy        = 0.0
                        self.on_ground = True
                        break

        # Top clamp
        if self.y < 0:
            self.y  = 0.0
            self.vy = max(0.0, self.vy)

        # Collect pixels
        px_int = int(self.x)
        py_int = int(self.y)
        remaining = []
        for (cx, cy) in self.collectibles:
            if px_int < cx + 2 and px_int + 8 > cx and py_int < cy + 2 and py_int + 8 > cy:
                self.score += 1
            else:
                remaining.append((cx, cy))
        self.collectibles = remaining

    def sprite(self):
        if self.facing >= 0:
            return FRAMES_R[self.anim_frame]
        return FRAMES_L[self.anim_frame]


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


def render(player, tick):
    canvas = Image.new("RGB", (GW, GH), (0, 0, 0))
    draw   = ImageDraw.Draw(canvas)

    # Platforms
    for (x1, x2, sy) in PLATFORMS:
        col = FLOOR_COL if sy == 30 else PLATFORM_COL
        draw.rectangle([x1, sy, x2, sy + 1], fill=col)

    # Collectibles (pulsing between two gold tones)
    coll_col = COLL_COL_A if (tick // 5) % 2 == 0 else COLL_COL_B
    for (cx, cy) in player.collectibles:
        draw.rectangle([cx, cy, cx + 1, cy + 1], fill=coll_col)

    # Player sprite
    sp = player.sprite()
    px, py = int(player.x), int(player.y)
    for row in range(8):
        for col in range(8):
            color = sp[row * 8 + col]
            if color is not None:
                sx = px + col
                sy = py + row
                if 0 <= sx < GW and 0 <= sy < GH:
                    draw.point((sx, sy), fill=color)

    # Score (top-right corner, yellow)
    score_str = str(min(player.score, 99))
    sx_base = GW - 4 * len(score_str) - 1
    for i, ch in enumerate(score_str):
        draw_digit(draw, ch, sx_base + i * 4, 1, (255, 255, 100))

    return make_tiles(canvas)


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
    print("Platformer %dx%d px | Gauche/Droite : deplacement, Haut : saut, Echap : quitter." % (GW, GH))
    print("Collecte les %d pixels dores pour marquer des points !\n" % len(COLL_INIT))

    player = Player()
    delay  = 1.0 / FPS
    tick   = 0

    try:
        while state['running']:
            dx = 0
            if state['left'] and not state['right']:
                dx = -1
            elif state['right'] and not state['left']:
                dx = 1

            jump = state['jump']
            state['jump'] = False   # one-shot: consume immediately

            player.update(dx, jump)

            pngs = render(player, tick)
            await send_all(sessions, pngs)
            await asyncio.sleep(delay)
            tick += 1

            if not player.collectibles:
                print("Tous les pixels collectes ! Score : %d  -- Nouveau tour." % player.score)
                player.collectibles = list(COLL_INIT)

    finally:
        await disconnect_all(sessions)
        print("\nDeconnecte. Score final : %d" % player.score)


listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

asyncio.run(game_loop())

listener.stop()
