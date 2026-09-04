from PIL import Image
from demosloop.common import GW, GH

FPS = 10.0
STAGNATION_LIMIT = 100

GLIDER_A = [(0,0),(1,0),(2,0),(2,1),(1,2)]
GLIDER_B = [(0,0),(1,0),(2,0),(0,1),(1,2)]
GLIDER_C = [(1,0),(2,1),(0,2),(1,2),(2,2)]
GLIDER_D = [(1,0),(0,1),(0,2),(1,2),(2,2)]

GLIDERS = [GLIDER_A, GLIDER_B, GLIDER_C, GLIDER_D]

# 12 glisseurs repartis sur 128x32, 4 orientations alternees
# (origine_x, origine_y, index_orientation)
SPAWN_POSITIONS = [
    (4,   2,  0),
    (36,  2,  1),
    (68,  2,  2),
    (100, 2,  3),
    (20,  13, 1),
    (52,  13, 2),
    (84,  13, 3),
    (116, 13, 0),
    (8,   25, 2),
    (40,  25, 3),
    (72,  25, 0),
    (104, 25, 1),
]


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


def cell_color(a):
    if a == 0:
        return (0, 0, 0)
    t = min(a, 20) / 20.0
    r = int(t * 160)
    g = int((1 - t) * 220 + t * 40)
    b = int(220 - t * 40)
    return (r, g, b)


def init_state():
    grid, age = make_gliders()
    return {
        "grid": grid,
        "age": age,
        "stagnant": 0,
        "last_pop": population(grid),
        "gen": 0,
    }


def render(state):
    grid, age = step(state["grid"], state["age"])
    state["gen"] += 1

    pop = population(grid)
    if pop == state["last_pop"]:
        state["stagnant"] += 1
    else:
        state["stagnant"] = 0
        state["last_pop"] = pop

    if state["stagnant"] >= STAGNATION_LIMIT or pop == 0:
        grid, age = make_gliders()
        state["stagnant"] = 0
        state["last_pop"] = population(grid)
        state["gen"] = 0

    state["grid"], state["age"] = grid, age

    pixels = [cell_color(age[i]) if grid[i] else (0, 0, 0) for i in range(GW * GH)]
    img = Image.new("RGB", (GW, GH))
    img.putdata(pixels)
    return img
