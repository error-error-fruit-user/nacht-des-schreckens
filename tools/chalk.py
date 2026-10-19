#!/usr/bin/env python3
"""Draw a chalk outline wall buy for each weapon, traced from its pickup sprite.

usage: python3 tools/chalk.py

Dependency-free Python 3.8+. Each weapon's pickup sprite (sprites/weapons/<weapon>/pickup/) is
scaled down, its outline traced, and drawn in slightly uneven chalk white into
sprites/chalk_drawings/<sprite>a0.png, standing on its bottom center like the hand-drawn ones.
Reproducible: the chalk's unevenness comes from the pixel positions, not a random seed.
The weapons with hand-drawn outlines (the Kar98k, the M1 Carbine, the Thompson) are left alone.
"""

import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
NACHT = os.path.join(HERE, "..", "nacht")

# weapon folder: the drawing's sprite name, and how much of the pickup's size it keeps
DRAWINGS = {
    "colt": ("CLTD", 0.6),
    "magnum": ("MAGD", 0.6),
    "m1garand": ("GRND", 0.5),
    "double_barrel_shotgun": ("DBSD", 0.5),
    "ppsh": ("PPSD", 0.5),
    "type100": ("T10D", 0.5),
}
CHALK = (236, 236, 228)


def read_png(path):
    """The RGBA pixels of an 8-bit RGBA PNG, as rows of (r, g, b, a)."""
    data = open(path, "rb").read()
    width, height, depth, kind = struct.unpack(">IIBB", data[16:26])
    if depth != 8 or kind != 6:
        raise SystemExit(f"{path}: only 8-bit RGBA PNGs are supported")
    raw = b""
    position = 8
    while position + 8 <= len(data):
        length, name = struct.unpack(">I4s", data[position:position + 8])
        if name == b"IEND":
            break
        if name == b"IDAT":
            raw += data[position + 8:position + 8 + length]
        position += 12 + length
    raw = zlib.decompress(raw)
    stride = width * 4
    rows, previous = [], bytearray(stride)
    for y in range(height):
        start = y * (stride + 1)
        kind, line = raw[start], bytearray(raw[start + 1:start + 1 + stride])
        for x in range(stride):
            left = line[x - 4] if x >= 4 else 0
            up = previous[x]
            corner = previous[x - 4] if x >= 4 else 0
            if kind == 1:
                line[x] = (line[x] + left) & 255
            elif kind == 2:
                line[x] = (line[x] + up) & 255
            elif kind == 3:
                line[x] = (line[x] + (left + up) // 2) & 255
            elif kind == 4:
                guess = left + up - corner
                best = min((abs(guess - left), left), (abs(guess - up), up), (abs(guess - corner), corner))[1]
                line[x] = (line[x] + best) & 255
        rows.append([tuple(line[i:i + 4]) for i in range(0, stride, 4)])
        previous = line
    return rows


def write_png(path, rows, offsets):
    height, width = len(rows), len(rows[0])
    raw = b"".join(b"\0" + b"".join(bytes(p) for p in row) for row in rows)

    def chunk(name, body):
        return struct.pack(">I", len(body)) + name + body + struct.pack(">I", zlib.crc32(name + body))

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    png += chunk(b"grAb", struct.pack(">ii", *offsets)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)


def coverage(rows, scale):
    """How much of each pixel of the scaled-down picture the sprite covers (0 to 1)."""
    height, width = len(rows), len(rows[0])
    small_w, small_h = max(1, round(width * scale)), max(1, round(height * scale))
    cells = []
    for y in range(small_h):
        line = []
        for x in range(small_w):
            x0, x1 = int(x / scale), max(int(x / scale) + 1, int((x + 1) / scale))
            y0, y1 = int(y / scale), max(int(y / scale) + 1, int((y + 1) / scale))
            area = [rows[j][i][3] for j in range(y0, min(y1, height)) for i in range(x0, min(x1, width))]
            line.append(sum(1 for a in area if a > 128) / max(1, len(area)))
        cells.append(line)
    return cells


def noise(x, y):
    """A repeatable 0..1 value per pixel, for the chalk's unevenness."""
    value = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
    value = ((value ^ (value >> 13)) * 1274126177) & 0xFFFFFFFF
    return (value & 0xFFFF) / 0xFFFF


def chalk(rows, scale):
    cells = coverage(rows, scale)
    height, width = len(cells), len(cells[0])
    inside = [[cells[y][x] >= 0.4 for x in range(width)] for y in range(height)]

    def solid(x, y):
        return 0 <= x < width and 0 <= y < height and inside[y][x]

    out = [[(0, 0, 0, 0)] * width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            if not inside[y][x]:
                continue
            edge = not all(solid(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if edge:
                # Solid like the hand-drawn outlines, a little uneven like chalk
                out[y][x] = CHALK + (int(205 + 50 * noise(x, y)),)
    return out


def main():
    for weapon, (sprite, scale) in DRAWINGS.items():
        folder = os.path.join(NACHT, "sprites", "weapons", weapon, "pickup")
        source = os.path.join(folder, sorted(os.listdir(folder))[0])
        drawing = chalk(read_png(source), scale)
        target = os.path.join(NACHT, "sprites", "chalk_drawings", sprite.lower() + "a0.png")
        write_png(target, drawing, (len(drawing[0]) // 2, len(drawing)))
        print(f"{target}: {len(drawing[0])}x{len(drawing)}")


if __name__ == "__main__":
    main()
