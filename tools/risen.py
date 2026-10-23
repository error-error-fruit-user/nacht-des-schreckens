#!/usr/bin/env python3
"""Draw Risen's drop and HUD icon (sprites/powerups/drops/risen/hhrna0.png, graphics/hh/hhirn.png).

usage: python3 tools/risen.py

Dependency-free Python 3.8+. The drop is drawn in the style of ZDL's power-up drops (a glowing
many-pointed burst with a pale emblem in the middle), blood red like the rain: a skeletal hand
reaching up out of a grave mound, rain falling around it. The HUD icon is nacht's own shield
(graphics/hh/hhiik.png's outline and colours) with the same hand in place of the skull.
Reproducible: no random seed, every pixel follows from its position.
"""

import math
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
NACHT = os.path.join(HERE, "..", "nacht")
DROP = os.path.join(NACHT, "sprites", "powerups", "drops", "risen", "hhrna0.png")
ICON = os.path.join(NACHT, "graphics", "hh", "hhirn.png")
SHIELD = os.path.join(NACHT, "graphics", "hh", "hhiik.png")

# The hand out of its mound, a pixel a cell
HAND = [
    "....#.#.#....",
    "..#.#.#.#....",
    "..#.#.#.#....",
    "..#.#.#.#.#..",
    "..#######.#..",
    "..#######.#..",
    "..#########..",
    "..########...",
    "...#######...",
    "...######....",
    "....#####....",
    "....#####....",
    "....#####....",
    ".#########...",
    "#############",
]
RAIN = [(-14, -12), (13, -15), (-11, 4), (15, 2), (-16, -2), (10, -6)]


def read_png(path):
    """An 8-bit RGBA, non-interlaced PNG as rows of (r, g, b, a)."""
    data = open(path, "rb").read()
    pos, raw, width, height = 8, b"", 0, 0
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        kind, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            width, height = struct.unpack(">II", body[:8])
        elif kind == b"IDAT":
            raw += body
    raw = zlib.decompress(raw)
    stride, rows, previous = width * 4, [], bytearray(width * 4)
    for y in range(height):
        kind, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            left = line[i - 4] if i >= 4 else 0
            up = previous[i]
            corner = previous[i - 4] if i >= 4 else 0
            if kind == 1:
                line[i] = (line[i] + left) & 255
            elif kind == 2:
                line[i] = (line[i] + up) & 255
            elif kind == 3:
                line[i] = (line[i] + (left + up) // 2) & 255
            elif kind == 4:
                p = left + up - corner
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - corner)
                line[i] = (line[i] + (left if pa <= pb and pa <= pc else up if pb <= pc else corner)) & 255
        rows.append([tuple(line[x * 4:x * 4 + 4]) for x in range(width)])
        previous = line
    return rows


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


def stamp(rows, cx, cy, scale, color, outline=None):
    """The hand, centered on cx, cy, `scale` pixels a cell, with a dark outline."""
    height, width = len(HAND) * scale, len(HAND[0]) * scale
    left, top = cx - width // 2, cy - height // 2

    def filled(x, y):
        cx_, cy_ = (x - left) // scale, (y - top) // scale
        return 0 <= cy_ < len(HAND) and 0 <= cx_ < len(HAND[0]) and HAND[cy_][cx_] == "#" and x >= left and y >= top

    for y in range(top - 1, top + height + 1):
        for x in range(left - 1, left + width + 1):
            if not (0 <= y < len(rows) and 0 <= x < len(rows[0])):
                continue
            if filled(x, y):
                # lit from the upper left: a little darker toward the lower right
                shade = 1.0 - 0.25 * ((x - left) + (y - top)) / (width + height)
                rows[y][x] = tuple(int(c * shade) for c in color[:3]) + (255,)
            elif outline and any(filled(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                rows[y][x] = outline


def drop():
    """The burst: a twelve-pointed star glowing from white-hot to deep red, fading at its tips."""
    width, height = 63, 59
    cx, cy = 31, 29
    rows = [[(0, 0, 0, 0)] * width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            dx, dy = x - cx, y - cy
            distance = math.hypot(dx, dy)
            angle = math.atan2(dy, dx)
            # points: the edge reaches out at 12 angles
            reach = 17 + 11 * abs(math.cos(angle * 6)) ** 3
            if distance > reach:
                continue
            t = distance / reach
            red = 255
            green = int(max(0, 210 * (1 - t) ** 2.2))
            blue = int(max(0, 160 * (1 - t) ** 3))
            alpha = int(255 * min(1, (1 - t) * 3))
            rows[y][x] = (red if t < 0.85 else int(255 - (t - 0.85) * 600), green, blue, alpha)
    # the dark disc the emblem sits on
    for y in range(height):
        for x in range(width):
            if math.hypot(x - cx, y - cy) <= 14:
                rows[y][x] = (40, 4, 8, 255)
    for rx, ry in RAIN:
        for k in range(3):
            x, y = cx + rx, cy + ry + k
            if math.hypot(x - cx, y - cy) <= 14:
                rows[y][x] = (210, 40, 50, 255)
    stamp(rows, cx, cy + 1, 2, (236, 226, 204), outline=(10, 0, 2, 255))
    return rows


def icon():
    """Nacht's shield, its skull painted over with the shield's own colour, and the hand."""
    rows = read_png(SHIELD)
    height, width = len(rows), len(rows[0])
    # The shield's body is its most common dark colour, the skull its lightest (its border is
    # nearly as light, and as common)
    counts = {}
    for row in rows:
        for pixel in row:
            if pixel[3] == 255:
                counts[pixel] = counts.get(pixel, 0) + 1
    body = max((p for p in counts if sum(p[:3]) < 384), key=counts.get)
    light = max(counts, key=lambda p: sum(p[:3]))
    # paint over everything inside the shield's border that isn't body coloured
    border = 3
    for y in range(border, height - border):
        for x in range(border, width - border):
            pixel = rows[y][x]
            inside = all(rows[y + dy][x + dx][3] == 255 for dx in (-border, border) for dy in (-border, border))
            if pixel[3] == 255 and inside and pixel == light:
                rows[y][x] = body
    stamp(rows, width // 2, height // 2 + 1, 2, light)
    return rows


def main():
    write_png(DROP, drop(), (31, 59))
    write_png(ICON, icon())


if __name__ == "__main__":
    main()
