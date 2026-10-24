#!/usr/bin/env python3
"""Draw nacht's menu theme: the title screen (graphics/titlepic.png), the console's background
(graphics/conback.png), the menus' selector (graphics/nachtsel.png, a drop of blood) and the pause
sign (graphics/nachtpau.png) and the main menu's title (graphics/nachtlog.png).

usage: python3 tools/theme.py

Dependency-free Python 3.8+. The title screen is nacht's bunker at night under its blood rain, drawn
in perspective from the south-west: weathered concrete, the two-storey wing and the long hall with
its roof caved in, boarded windows lit from inside, sandbags along the front and the crashed plane
(its own sprite) burning before it, under the name in flat, dripping capitals. The console is the
same rain over near-black. Reproducible: the rain and the weathering follow from pixel positions,
not a random seed.
"""

import math
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
NACHT = os.path.join(HERE, "..", "nacht")
GRAPHICS = os.path.join(NACHT, "graphics")
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


def title(rows, text, top, scale, color):
    """The name in blocky capitals of one flat colour, each letter dripping blood at the bottom."""
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
                rect(rows, x0, y0, scale, scale, color)
                # drips off the bottom of a letter's strokes
                if gy == 6 and noise(i, gx, 11) < 0.45:
                    drip = 2 + int(noise(i, gx, 12) * 6) * scale // 2
                    for k in range(drip):
                        x, y = x0 + scale // 2, y0 + scale + k
                        if y < HEIGHT:
                            rows[y][x] = color + (255,)


def read_png(path):
    """An 8-bit RGBA PNG (as the sprites are) as rows of pixels."""
    with open(path, "rb") as f:
        data = f.read()
    pos, packed = 8, b""
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            width, height, depth, color = struct.unpack(">IIBB", body[:10])
            assert depth == 8 and color == 6, f"{path} isn't 8-bit RGBA"
        elif kind == b"IDAT":
            packed += body
        pos += 12 + length
    raw = zlib.decompress(packed)
    stride, rows, previous, i = width * 4, [], bytearray(width * 4), 0
    for _ in range(height):
        kind, line = raw[i], bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            a = line[x - 4] if x >= 4 else 0
            b = previous[x]
            c = previous[x - 4] if x >= 4 else 0
            if kind == 1:
                line[x] = (line[x] + a) & 255
            elif kind == 2:
                line[x] = (line[x] + b) & 255
            elif kind == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif kind == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append([tuple(line[x:x + 4]) for x in range(0, stride, 4)])
        previous = line
    return rows


# The bunker on the title screen, drawn in perspective from the south-west: x runs east along its
# front, y north into the picture, z up, in rough feet. The camera stands at CAMERA, looking along
# YAW (degrees from east, counter-clockwise) and tipped down by PITCH; MIDDLE is how far down the
# picture its line of sight falls.
CAMERA = (-190.0, -430.0, 150.0)
YAW, PITCH, FOCAL, MIDDLE = 60.0, 13.0, 300.0, 0.62
CONCRETE = (88, 76, 72)
ROOF = (58, 50, 50)
BOARD = (40, 26, 16)
SANDBAG = (78, 66, 48)
# The blocks: west corner, east corner (x, y) and height
BLOCKS = [
    ((-80, 0), (0, 80), 108),      # the two-storey wing (the upstairs)
    ((0, 10), (170, 70), 56),      # the long hall
    ((62, -10), (98, 10), 44),     # the porch at the help door
]
# Windows on the fronts (south) and the west side: which block, which face, where along it (from
# its west or south end), how high, how wide and tall, boarded or not
WINDOWS = [
    (0, "south", 14, 22, 18, 16, True), (0, "south", 48, 22, 18, 16, False),
    (0, "south", 14, 70, 18, 16, False), (0, "south", 48, 70, 18, 16, True),
    (0, "west", 18, 22, 18, 16, True), (0, "west", 54, 22, 18, 16, True),
    (0, "west", 36, 70, 18, 16, False),
    (1, "south", 22, 20, 20, 15, True), (1, "south", 120, 20, 20, 15, False),
    (1, "south", 146, 20, 18, 15, True),
]
PLANE_AT = (-120.0, -70.0, 0.0)    # where the wreck lies, in front of the wing
PLANE_SIZE = 0.3                   # its sprite's pixels, in feet
# Its fires, as Nacht_Plane lights them: across its picture and up it, in its pixels
PLANE_FIRES = ((-106, 20), (-44, 46), (18, 12), (94, 60))


def project(point):
    """Where a point in the world falls in the picture, and how far in front of the camera."""
    x, y, z = (p - c for p, c in zip(point, CAMERA))
    yaw, pitch = math.radians(YAW), math.radians(PITCH)
    forward = x * math.cos(yaw) + y * math.sin(yaw)
    right = x * math.sin(yaw) - y * math.cos(yaw)
    depth = forward * math.cos(pitch) - z * math.sin(pitch)
    up = forward * math.sin(pitch) + z * math.cos(pitch)
    depth = max(depth, 1.0)
    return WIDTH / 2 + right * FOCAL / depth, HEIGHT * MIDDLE - up * FOCAL / depth, depth


def polygon(rows, corners, color):
    """Fills the convex polygon whose corners are world points."""
    points = [project(c)[:2] for c in corners]
    top = max(0, int(min(p[1] for p in points)))
    bottom = min(HEIGHT - 1, int(max(p[1] for p in points)))
    for y in range(top, bottom + 1):
        crossings = []
        for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1]):
            if (y0 <= y + 0.5) != (y1 <= y + 0.5):
                crossings.append(x0 + (y + 0.5 - y0) * (x1 - x0) / (y1 - y0))
        if len(crossings) >= 2:
            for x in range(max(0, int(min(crossings) + 0.5)), min(WIDTH, int(max(crossings) + 0.5))):
                rows[y][x] = (color(x, y) if callable(color) else color)[:3] + (255,)


def concrete(shade, seed):
    """Weathered concrete: the shade, mottled, with streaks running down it."""
    def pick(x, y):
        stain = 0.8 + 0.2 * noise(x // 2, y // 3, seed) - 0.15 * (noise(x, 0, seed + 1) < 0.15)
        return mix((10, 6, 6), shade, max(0.0, min(1.0, stain)))
    return pick


def face_point(block, face, along, up):
    """The world point `along` a block's face from its west (or south) end, `up` from the ground."""
    (x0, y0), (x1, y1), _ = BLOCKS[block]
    if face == "south":
        return (x0 + along, y0, up)
    return (x0, y0 + along, up)


def window(rows, block, face, along, up, wide, tall, boarded):
    """A window lit from inside, boarded over or broken open."""
    def corners(a, u, w, t):
        return [face_point(block, face, a, u), face_point(block, face, a + w, u),
                face_point(block, face, a + w, u + t), face_point(block, face, a, u + t)]
    polygon(rows, corners(along - 1.5, up - 1.5, wide + 3, tall + 3), (24, 18, 16))
    polygon(rows, corners(along, up, wide, tall),
            lambda x, y: mix(WINDOW, (120, 40, 10), 0.4 * noise(x, y, 5)))
    if boarded:
        for k in range(3):
            polygon(rows, corners(along - 2, up + 2 + k * 5, wide + 4, 2.5), BOARD)


def bunker(rows):
    """The bunker in front of the sky already in `rows`, with sandbags and the burning wreck."""
    # 🌑 the ground, darkening towards the viewer
    horizon = project((0, 5000, 0))[1]
    for y in range(max(0, int(horizon)), HEIGHT):
        for x in range(WIDTH):
            mud = 0.75 + 0.25 * noise(x // 3, y // 2, 21)
            ground = mix((34, 12, 10), (8, 3, 3), (y - horizon) / max(1, HEIGHT - horizon))
            rows[y][x] = mix((0, 0, 0), ground[:3], mud)
    # 🌲 the forest's black edge along the horizon
    for x in range(WIDTH):
        tall = 3 + int(5 * noise(x // 2, 0, 31)) + (4 if noise(x // 5, 1, 32) < 0.3 else 0)
        for y in range(int(horizon) - tall, int(horizon) + 1):
            if 0 <= y < HEIGHT:
                rows[y][x] = (12, 3, 4, 255)
    # 🪵 a broken fence across the field, its posts leaning
    for i in range(9):
        post = (-260 + i * 34, -200 + i * 6, 0)
        if noise(i, 3, 33) < 0.25:
            continue
        lean = (noise(i, 4, 34) - 0.5) * 6
        polygon(rows, [post, (post[0] + 2, post[1], 0), (post[0] + 2 + lean, post[1], 16),
                       (post[0] + lean, post[1], 16)], (26, 16, 12))
    # 🧱 each block's back first: its west side and front, then its roof with a broken edge
    for number, ((x0, y0), (x1, y1), height) in sorted(enumerate(BLOCKS), key=lambda b: -b[1][1][1]):
        polygon(rows, [(x0, y0, 0), (x0, y1, 0), (x0, y1, height), (x0, y0, height)],
                concrete(mix((0, 0, 0), CONCRETE, 0.55)[:3], number * 3))
        polygon(rows, [(x0, y0, 0), (x1, y0, 0), (x1, y0, height), (x0, y0, height)],
                concrete(CONCRETE, number * 3 + 1))
        polygon(rows, [(x0, y0, height), (x1, y0, height), (x1, y1, height), (x0, y1, height)], ROOF + (255,))
        # a parapet along the front of the roof
        polygon(rows, [(x0, y0, height), (x1, y0, height), (x1, y0, height + 3), (x0, y0, height + 3)],
                mix((0, 0, 0), CONCRETE, 0.8)[:3] + (255,))
        for item in WINDOWS:
            if item[0] == number:
                window(rows, *item)
    # the hall's roof is caved in at one end: a dark hole with jagged edges
    polygon(rows, [(118, 22, 56), (150, 18, 56), (160, 40, 56), (138, 58, 56), (112, 46, 56)], (14, 8, 8))
    # the help door in the porch, ajar
    polygon(rows, [(72, -10, 0), (86, -10, 0), (86, -10, 30), (72, -10, 30)], (30, 18, 10))
    polygon(rows, [(72, -10, 0), (77, -10, 0), (77, -10, 30), (72, -10, 30)],
            lambda x, y: mix(WINDOW, (90, 30, 8), 0.5))
    # 🛡️ sandbags piled along the front
    for i in range(16):
        bx = -76 + i * 10
        if 60 < bx < 100:
            continue
        for row, (height, shift) in enumerate(((0, 0), (5, 5))):
            if row and i % 3 == 0:
                continue
            x = bx + shift
            polygon(rows, [(x, -22, height), (x + 9, -22, height), (x + 9, -22, height + 5),
                           (x + 7, -22, height + 6), (x + 2, -22, height + 6), (x, -22, height + 5)],
                    lambda px, py, s=i * 7 + row: mix(SANDBAG, (20, 14, 10), 0.4 * noise(px, py, s)))
    plane(rows)


def plane(rows):
    """The crashed plane, its own sprite, lying where it fell and burning where it burns in game."""
    sprite = read_png(os.path.join(NACHT, "sprites", "decorations", "plnea0.png"))
    foot_x, foot_y, depth = project(PLANE_AT)
    scale = PLANE_SIZE * FOCAL / depth
    wide, tall = len(sprite[0]), len(sprite)
    for j in range(int(tall * scale)):
        for i in range(int(wide * scale)):
            x, y = int(foot_x - wide * scale / 2 + i), int(foot_y - tall * scale + j)
            pixel = sprite[int(j / scale)][int(i / scale)]
            if 0 <= x < WIDTH and 0 <= y < HEIGHT and pixel[3] > 128:
                rows[y][x] = mix(pixel[:3], (0, 0, 0), 0.45)
    flame = int(30 * scale) + 3
    for across, up in PLANE_FIRES:
        x0, y0 = int(foot_x + across * scale), int(foot_y - up * scale)
        # the fire's light on the ground and the wreck around it
        for y in range(y0 - flame * 2, y0 + flame * 2):
            for x in range(x0 - flame * 3, x0 + flame * 3):
                if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                    near = max(0.0, 1 - math.hypot((x - x0) / 3, y - y0) / (flame * 1.2))
                    rows[y][x] = mix(rows[y][x][:3], (240, 120, 30), 0.35 * near * near)
        for k in range(flame):
            for spread in range(-3, 4):
                x, y = x0 + spread + int(1.5 * math.sin(k * 0.9 + across)), y0 - k
                if abs(spread) <= 3 - k * 3 // flame and 0 <= x < WIDTH and 0 <= y < HEIGHT:
                    rows[y][x] = FIRE[min(2, k * 3 // flame)] + (255,)


def titlepic():
    rows = blank()
    sky(rows, (70, 6, 8), (30, 4, 4))
    # a pale moon behind the clouds
    for y in range(20, 60):
        for x in range(250, 290):
            d = math.hypot(x - 270, y - 40)
            if d < 18:
                rows[y][x] = mix(rows[y][x][:3], (200, 120, 110), 0.6 * (1 - d / 18) ** 0.5)
    bunker(rows)
    rain(rows, 0.035, BLOOD_LIT)
    title(rows, "NACHT DES", 14, 3, BLOOD_LIT)
    title(rows, "SCHRECKENS", 40, 3, BLOOD_LIT)
    return rows


def conback():
    rows = blank()
    sky(rows, (24, 2, 3), (2, 0, 0))
    rain(rows, 0.03, BLOOD)
    title(rows, "NACHT DES SCHRECKENS", 176, 2, (90, 12, 14))
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
        title(rows, text, top, scale, BLOOD_LIT)
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
