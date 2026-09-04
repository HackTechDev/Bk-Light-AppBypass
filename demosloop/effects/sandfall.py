import random
from PIL import Image
from demosloop.common import GW, GH

FPS = 15.0
RATE = 3
WIND = 0
RESET_WHEN_FULL = True


def sand_color(grain):
    v = int(160 + grain * 60)
    return (v, int(v * 0.78), int(v * 0.3))


def step_sand(grid, rate=RATE, wind=WIND):
    for _ in range(rate):
        if random.random() < 0.8:
            x = random.randint(0, GW - 1)
            if not grid[x]:
                grid[x] = random.uniform(0.6, 1.0)

    next_grid = [0.0] * (GW * GH)
    moved = [False] * (GW * GH)

    for y in range(GH - 1, -1, -1):
        for x in range(GW):
            g = grid[y * GW + x]
            if not g or moved[y * GW + x]:
                continue

            below = y + 1

            if below >= GH:
                next_grid[y * GW + x] = g
                continue

            if not grid[below * GW + x] and not moved[below * GW + x]:
                next_grid[below * GW + x] = g
                moved[below * GW + x] = True
                continue

            if wind > 0:
                dirs = [1, -1]
            elif wind < 0:
                dirs = [-1, 1]
            else:
                dirs = [-1, 1] if random.random() < 0.5 else [1, -1]

            placed = False
            for dx in dirs:
                nx = x + dx
                if 0 <= nx < GW and not grid[below * GW + nx] and not moved[below * GW + nx]:
                    next_grid[below * GW + nx] = g
                    moved[below * GW + nx] = True
                    placed = True
                    break

            if not placed:
                next_grid[y * GW + x] = g

    return next_grid


def init_state():
    return {"grid": [0.0] * (GW * GH)}


def render(state):
    grid = step_sand(state["grid"], RATE, WIND)
    if RESET_WHEN_FULL and all(grid[x] for x in range(GW)):
        grid = [0.0] * (GW * GH)
    state["grid"] = grid

    pixels = [sand_color(grid[y * GW + x]) if grid[y * GW + x] else (0, 0, 0)
              for y in range(GH) for x in range(GW)]
    img = Image.new("RGB", (GW, GH))
    img.putdata(pixels)
    return img
