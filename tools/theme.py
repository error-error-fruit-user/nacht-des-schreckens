#!/usr/bin/env python3
"""Draw nacht's menu theme: the title screen (graphics/titlepic.png), the console's background
(graphics/conback.png), the menus' selector (graphics/nachtsel.png, a drop of blood) and the pause
sign (graphics/nachtpau.png) and the main menu's title (graphics/nachtlog.png).

usage: python3 tools/theme.py

Dependency-free Python 3.8+. The title screen is the map at night under its blood rain: the
building's black silhouette against a red sky, its windows lit, the crashed plane burning in front,
and the name in dripping capitals. The console is the same rain over near-black. Reproducible: the
rain and the weathering follow from pixel positions, not a random seed.
"""

import math
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
GRAPHICS = os.path.join(HERE, "..", "nacht", "graphics")
WIDTH, HEIGHT = 320, 200

BLOOD = (150, 10, 14)
BLOOD_LIT = (220, 40, 36)
BONE = (214, 204, 178)
WINDOW = (236, 170, 70)
FIRE = [(255, 210, 90), (240, 120, 30), (170, 40, 10)]

# 5x7 capitals for the name
LETTERS = {
    "N": ["10001", "11001", "10101", "10101", "10011", "10001", "10001"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    " ": ["00000"] * 7,
}


def noise(x, y, seed=0):
    n = (x * 374761393 + y * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 0xFFFF


def blank(color=(0, 0, 0, 0)):
    return [[color] * WIDTH for _ in range(HEIGHT)]


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)


def sky(rows, top, bottom):
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        for x in range(WIDTH):
            rows[y][x] = mix(top, bottom, t * t)


def rain(rows, density, color, length=6):
    """Blood rain: thin streaks falling slightly to the left."""
    for x in range(0, WIDTH, 2):
        for y in range(0, HEIGHT, 3):
            if noise(x, y, 7) < density:
                for k in range(length):
                    px, py = x - k // 3, y + k
                    if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                        fade = 1 - k / length
                        rows[py][px] = mix(rows[py][px][:3], color, 0.4 * fade)


def rect(rows, x, y, w, h, color):
    for py in range(max(0, y), min(HEIGHT, y + h)):
        for px in range(max(0, x), min(WIDTH, x + w)):
            rows[py][px] = color + (255,) if len(color) == 3 else color


def building(rows, ground):
    """The two storeys, a gabled roof and lit windows, in black against the sky."""
    dark = (8, 4, 4)
    left, right = 70, 250
    rect(rows, left, ground - 70, right - left, 70, dark)
    # roof
    for i in range(36):
        rect(rows, left - 6 + i * 2, ground - 70 - i, right - left + 12 - i * 4, 1, dark)
    # chimney
    rect(rows, 214, ground - 112, 10, 30, dark)
    for wx in (86, 118, 150, 196, 228):
        for wy in (ground - 60, ground - 30):
            # some windows are boarded: lit only between the planks
            for py in range(wy, wy + 14):
                for px in range(wx, wx + 10):
                    plank = (py - wy) % 5 == 2 and noise(wx, wy) < 0.6
                    flicker = 0.75 + 0.25 * noise(px, py, 3)
                    rows[py][px] = dark + (255,) if plank else mix(dark, WINDOW, flicker)
    # the door, ajar
    rect(rows, 170, ground - 26, 14, 26, (30, 18, 10))


def plane(rows, ground):
    """The crashed plane in front: a broken fuselage and a tail fin, burning."""
    dark = (14, 12, 8)
    for i in range(70):
        top = ground - 10 - int(6 * math.sin(i / 70 * math.pi))
        rect(rows, 10 + i, top, 1, ground - top, dark)
    for i in range(14):
        rect(rows, 72 + i, ground - 8 - i * 2, 3, 6, dark)
    for fx in (24, 46, 66):
        for k in range(18):
            for spread in range(-3, 4):
                px, py = fx + spread + int(2 * math.sin(k * 0.9 + fx)), ground - 6 - k
                if abs(spread) <= 3 - k // 6 and 0 <= py < HEIGHT:
                    rows[py][px] = FIRE[min(2, k // 6)] + (255,)


def ground_line(rows, ground):
    for y in range(ground, HEIGHT):
        for x in range(WIDTH):
            rows[y][x] = mix((20, 6, 6), (4, 2, 2), (y - ground) / (HEIGHT - ground))


def title(rows, text, top, scale, color, shade):
    """The name in blocky capitals, each letter dripping blood at the bottom."""
    width = len(text) * 6 * scale - scale
    left = (WIDTH - width) // 2
    # a shadow under every stroke first, so no letter's shadow covers another's colour
    for i, letter in enumerate(text):
        for gy, row in enumerate(LETTERS[letter]):
            for gx, bit in enumerate(row):
                if bit == "1":
                    x0, y0 = left + (i * 6 + gx) * scale, top + gy * scale
                    rect(rows, x0 + 1, y0 + 1, scale, scale, (0, 0, 0))
    for i, letter in enumerate(text):
        glyph = LETTERS[letter]
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit != "1":
                    continue
                x0, y0 = left + (i * 6 + gx) * scale, top + gy * scale
                for py in range(scale):
                    for px in range(scale):
                        x, y = x0 + px, y0 + py
                        rows[y][x] = mix(color, shade, py / scale * 0.6)
                # drips off the bottom of a letter's strokes
                if gy == 6 and noise(i, gx, 11) < 0.45:
                    drip = 2 + int(noise(i, gx, 12) * 6) * scale // 2
                    for k in range(drip):
                        x, y = x0 + scale // 2, y0 + scale + k
                        if y < HEIGHT:
                            rows[y][x] = mix(color, shade, 0.5)


def titlepic():
    rows = blank()
    sky(rows, (70, 6, 8), (30, 4, 4))
    # a pale moon behind the clouds
    for y in range(20, 60):
        for x in range(250, 290):
            d = math.hypot(x - 270, y - 40)
            if d < 18:
                rows[y][x] = mix(rows[y][x][:3], (200, 120, 110), 0.6 * (1 - d / 18) ** 0.5)
    ground = 168
    building(rows, ground)
    ground_line(rows, ground)
    plane(rows, ground)
    rain(rows, 0.035, BLOOD_LIT)
    title(rows, "NACHT DES", 14, 3, BLOOD_LIT, BLOOD)
    title(rows, "SCHRECKENS", 40, 3, BLOOD_LIT, BLOOD)
    return rows


def conback():
    rows = blank()
    sky(rows, (24, 2, 3), (2, 0, 0))
    rain(rows, 0.03, BLOOD)
    title(rows, "NACHT DES SCHRECKENS", 176, 2, (90, 12, 14), (50, 6, 8))
    return rows


def selector():
    """A drop of blood, 9 wide and 13 tall, centred on its left of the item."""
    w, h = 9, 13
    rows = [[(0, 0, 0, 0)] * w for _ in range(h)]
    cx = 4
    for y in range(h):
        for x in range(w):
            if y < 6:
                inside = abs(x - cx) <= y * 0.6
            else:
                inside = math.hypot(x - cx, y - 8.5) <= 4.2
            if inside:
                light = 1 - (x + y) / (w + h)
                rows[y][x] = mix(BLOOD, BLOOD_LIT, light)
    rows[8][3] = BONE + (255,)
    return rows


def lettering(width, height, lines):
    """Words in the title's dripping capitals on their own, a line at each (text, top, scale)."""
    global WIDTH, HEIGHT
    saved = WIDTH, HEIGHT
    WIDTH, HEIGHT = width, height
    rows = blank()
    for text, top, scale in lines:
        title(rows, text, top, scale, BLOOD_LIT, BLOOD)
    WIDTH, HEIGHT = saved
    return rows


def pause_sign():
    return lettering(110, 34, [("PAUSED", 4, 3)])


def logo():
    """The main menu's title."""
    return lettering(196, 56, [("NACHT DES", 2, 3), ("SCHRECKENS", 26, 3)])


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
    write_png(os.path.join(GRAPHICS, "titlepic.png"), titlepic())
    write_png(os.path.join(GRAPHICS, "conback.png"), conback())
    write_png(os.path.join(GRAPHICS, "nachtsel.png"), selector())
    write_png(os.path.join(GRAPHICS, "nachtpau.png"), pause_sign())
    write_png(os.path.join(GRAPHICS, "nachtlog.png"), logo())


if __name__ == "__main__":
    main()
