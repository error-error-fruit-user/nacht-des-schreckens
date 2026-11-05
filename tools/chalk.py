#!/usr/bin/env python3
"""Draw the chalk outlines of Doom's weapons for nacht's walls (sprites/chalk/), the way World at
War draws its own: a white chalk line around the weapon's shape, with a dark edge, and nothing
inside. Each is traced from the weapon's pickup sprite in an IWAD, Freedoom: Phase 2's (NCWF) and
Doom II's (NCWD), since the two draw their weapons differently; Nacht_DoomDrawing shows the set
of the IWAD being played. Frames: A the shotgun, B the super shotgun, C the chaingun.

usage: python3 tools/chalk.py [--freedoom2 WAD] [--doom2 WAD]

The IWADs default to ../tdl/secrets/wads/ (freedoom2.wad, DOOM2.WAD). Dependency-free Python 3.8+,
and reproducible: the chalk's grain follows from pixel positions, not a random seed. The traced
outlines are drawn at twice the sprites' size and shown at half (Scale 0.5), like doomify's.
"""

import argparse
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
CHALK = os.path.join(HERE, "..", "nacht", "sprites", "chalk")
WADS = os.path.join(HERE, "..", "..", "tdl", "secrets", "wads")

# frame letter → the IWADs' pickup sprite
WEAPONS = {"A": "SHOTA0", "B": "SGN2A0", "C": "MGUNA0"}
SETS = {"freedoom2": "NCWF", "doom2": "NCWD"}

SCALE = 2           # traced at twice the size
PAD = 4             # room around the shape, in the sprite's pixels
LINE = 3            # the chalk line, in traced pixels, outside the shape
EDGE = 1            # the dark edge around the line
CHALK_COLOR = (226, 222, 208)
EDGE_COLOR = (12, 10, 8, 150)


def noise(x, y, seed=0):
    n = (x * 374761393 + y * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 0xFFFF


def read_wad(path):
    with open(path, "rb") as f:
        data = f.read()
    count, offset = struct.unpack("<ii", data[4:12])
    lumps = {}
    for i in range(count):
        start, size, name = struct.unpack("<ii8s", data[offset + 16 * i:offset + 16 * i + 16])
        lumps[name.rstrip(b"\0").decode("ascii", "replace").upper()] = data[start:start + size]
    return lumps


def picture_mask(lump):
    """Which pixels of a Doom picture are drawn: a list of rows of booleans."""
    width, height = struct.unpack("<hh", lump[:4])
    mask = [[False] * width for _ in range(height)]
    for x in range(width):
        (column,) = struct.unpack("<I", lump[8 + 4 * x:12 + 4 * x])
        top = -1
        while True:
            row = lump[column]
            if row == 0xFF:
                break
            # tall patches: a top at or below the last one adds to it
            top = top + row if row <= top else row
            length = lump[column + 1]
            for y in range(top, top + length):
                if 0 <= y < height:
                    mask[y][x] = True
            column += 4 + length
    return mask


def traced_shape(mask):
    """The shape at SCALE times the size, padded and its stair steps rounded off."""
    height, width = len(mask), len(mask[0])
    big_w, big_h = (width + 2 * PAD) * SCALE, (height + 2 * PAD) * SCALE

    def drawn(x, y):
        sx, sy = x // SCALE - PAD, y // SCALE - PAD
        return 0 <= sx < width and 0 <= sy < height and mask[sy][sx]

    shape = []
    for y in range(big_h):
        row = []
        for x in range(big_w):
            near = sum(drawn(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
            row.append(near >= 5)
        shape.append(row)
    return shape


def grow(shape, radius):
    height, width = len(shape), len(shape[0])
    reach = [(dx, dy) for dx in range(-radius, radius + 1) for dy in range(-radius, radius + 1)
             if dx * dx + dy * dy <= radius * radius + radius]
    grown = [[False] * width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            if shape[y][x]:
                for dx, dy in reach:
                    if 0 <= x + dx < width and 0 <= y + dy < height:
                        grown[y + dy][x + dx] = True
    return grown


def filled(shape):
    """The shape with the holes inside it filled: only its outline is drawn, like World at War's."""
    height, width = len(shape), len(shape[0])
    outside = [[False] * width for _ in range(height)]
    todo = [(x, y) for x in range(width) for y in (0, height - 1)]
    todo += [(x, y) for y in range(height) for x in (0, width - 1)]
    while todo:
        x, y = todo.pop()
        if 0 <= x < width and 0 <= y < height and not outside[y][x] and not shape[y][x]:
            outside[y][x] = True
            todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return [[not outside[y][x] for x in range(width)] for y in range(height)]


def outline(mask, seed):
    """The chalk drawing of a sprite's mask, as rows of RGBA."""
    shape = filled(traced_shape(mask))
    line_out = grow(shape, LINE)
    edge_out = grow(line_out, EDGE)
    height, width = len(shape), len(shape[0])
    rows = []
    for y in range(height):
        row = []
        for x in range(width):
            if line_out[y][x] and not shape[y][x]:
                # chalk: grainy, a little lighter or darker from place to place, with a few gaps
                grain = noise(x, y, seed)
                streak = noise(x // 3, y // 2, seed + 7)
                light = 0.82 + 0.18 * grain - 0.12 * streak
                alpha = 255 if grain > 0.08 else 120
                row.append(tuple(min(255, int(c * light)) for c in CHALK_COLOR) + (alpha,))
            elif edge_out[y][x] and not line_out[y][x] or shape[y][x] and grow_edge(shape, x, y):
                row.append(EDGE_COLOR)
            else:
                row.append((0, 0, 0, 0))
        rows.append(row)
    return crop(rows)


def grow_edge(shape, x, y):
    """Whether a pixel of the shape lies just inside the line (the dark edge's inner side)."""
    height, width = len(shape), len(shape[0])
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < width and 0 <= ny < height and not shape[ny][nx]:
            return True
    return False


def crop(rows):
    used = [(x, y) for y, row in enumerate(rows) for x, pixel in enumerate(row) if pixel[3]]
    left = min(x for x, _ in used)
    right = max(x for x, _ in used) + 1
    top = min(y for _, y in used)
    bottom = max(y for _, y in used) + 1
    return [row[left:right] for row in rows[top:bottom]]


def write_png(path, rows, offsets=None):
    height, width = len(rows), len(rows[0])
    raw = b"".join(b"\0" + bytes(c for pixel in row for c in pixel) for row in rows)

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    if offsets is not None:
        png += chunk(b"grAb", struct.pack(">ii", *offsets))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)


def main():
    parser = argparse.ArgumentParser(description="Draw the chalk outlines of Doom's weapons.")
    parser.add_argument("--freedoom2", default=os.path.join(WADS, "freedoom2.wad"))
    parser.add_argument("--doom2", default=os.path.join(WADS, "DOOM2.WAD"))
    args = parser.parse_args()
    for iwad, sprite in SETS.items():
        lumps = read_wad(getattr(args, iwad))
        for seed, (letter, pickup) in enumerate(sorted(WEAPONS.items())):
            rows = outline(picture_mask(lumps[pickup]), seed)
            path = os.path.join(CHALK, f"{sprite}{letter}0.png".lower())
            # hung by its middle, flat on the wall
            write_png(path, rows, (len(rows[0]) // 2, len(rows) // 2))
            print(f"{path}: {len(rows[0])}x{len(rows)}, from {pickup}")


if __name__ == "__main__":
    main()
