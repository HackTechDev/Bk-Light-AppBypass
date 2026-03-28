import asyncio
import random
from io import BytesIO
from PIL import Image
from bk_light.display_session import BleDisplaySession

MAC_ADDRESS = "76:BF:38:1E:71:88"
W, H = 32, 32

def sand_color(grain):
    v = int(160 + grain * 60)
    return (v, int(v * 0.78), int(v * 0.3))

def step_sand(grid, rate=3, wind=0):
    for _ in range(rate):
        if random.random() < 0.8:
            x = random.randint(0, W - 1)
            if not grid[x]:
                grid[x] = random.uniform(0.6, 1.0)

    next_grid = [0.0] * (W * H)
    moved = [False] * (W * H)

    for y in range(H - 1, -1, -1):
        for x in range(W):
            g = grid[y * W + x]
            if not g or moved[y * W + x]:
                continue

            below = y + 1

            if below >= H:
                next_grid[y * W + x] = g
                continue

            if not grid[below * W + x] and not moved[below * W + x]:
                next_grid[below * W + x] = g
                moved[below * W + x] = True
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
                if 0 <= nx < W and not grid[below * W + nx] and not moved[below * W + nx]:
                    next_grid[below * W + nx] = g
                    moved[below * W + nx] = True
                    placed = True
                    break

            if not placed:
                next_grid[y * W + x] = g

    return next_grid

def grid_to_png(grid):
    img = Image.new("RGB", (W, H))
    pixels = [sand_color(grid[y * W + x]) if grid[y * W + x] else (0, 0, 0)
              for y in range(H) for x in range(W)]
    img.putdata(pixels)
    out = BytesIO()
    img.save(out, format="PNG", optimize=False)
    return out.getvalue()

async def sand_animation(
    duration=60.0,
    fps=15.0,
    rate=3,
    wind=0,
    reset_when_full=True,
):
    grid = [0.0] * (W * H)
    delay = 1.0 / fps

    async with BleDisplaySession(MAC_ADDRESS) as session:
        print(f"Sable pendant {duration}s à {fps} FPS...")
        t0 = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - t0 < duration:
            grid = step_sand(grid, rate, wind)

            if reset_when_full and all(grid[x] for x in range(W)):
                await asyncio.sleep(1.0)
                grid = [0.0] * (W * H)

            png = grid_to_png(grid)
            await session.send_png(png, delay=0.0)
            await asyncio.sleep(delay)
        print("Animation terminée.")

asyncio.run(sand_animation(
    duration=60.0,
    fps=15.0,
    rate=3,
    wind=0,
    reset_when_full=True,
))
