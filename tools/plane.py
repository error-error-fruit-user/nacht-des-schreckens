#!/usr/bin/env python3
"""Draw the crashed plane outside (sprites/decorations/plnea0.png).

usage: python3 tools/plane.py

Dependency-free Python 3.8+. A wrecked olive drab transport seen from the side, broken in two:
the nose ploughed into the ground, the tail propped up on the break, the far wing snapped off and
sticking up behind it, an engine with a bent propeller, holes, scorch marks and scrap around it.
300x150 standing on its bottom center, so Nacht_Plane's fires (scripts/nacht/plane.zs) land on it.
Reproducible: the weathering comes from the pixel positions, not a random seed.
"""

import math
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "..", "nacht", "sprites", "decorations", "plnea0.png")
WIDTH, HEIGHT = 300, 150

# Olive drab from lit to shadowed, the dark inside of the hull, glass, the insignia, dirt
OLIVE = [(112, 114, 70), (90, 94, 54), (72, 76, 42), (56, 59, 33), (41, 43, 25), (27, 28, 17)]
INSIDE = [(40, 36, 30), (26, 23, 19), (14, 12, 10)]
GLASS = [(78, 90, 92), (46, 54, 58), (26, 30, 34)]
METAL = [(150, 146, 132), (110, 106, 96), (72, 70, 64), (44, 42, 38)]
INSIGNIA_BLUE, INSIGNIA_WHITE = (40, 48, 70), (176, 172, 156)
DIRT = [(92, 74, 52), (70, 56, 40), (50, 40, 29)]
SOOT = (18, 16, 13)
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def noise(x, y, seed=0):
    """A repeatable 0..1 value per pixel."""
    value = (x * 374761393 + y * 668265263 + seed * 2246822519) & 0xFFFFFFFF
    value = ((value ^ (value >> 13)) * 1274126177) & 0xFFFFFFFF
    return (value & 0xFFFF) / 0xFFFF


def smooth_noise(x, y, size, seed=0):
    """Blotchy noise, for weathering and scorch edges."""
    gx, gy = x / size, y / size
    x0, y0 = math.floor(gx), math.floor(gy)
    fx, fy = gx - x0, gy - y0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    top = noise(x0, y0, seed) * (1 - fx) + noise(x0 + 1, y0, seed) * fx
    bottom = noise(x0, y0 + 1, seed) * (1 - fx) + noise(x0 + 1, y0 + 1, seed) * fx
    return top * (1 - fy) + bottom * fy


def shade(ramp, light, x, y):
    """A ramp color for a 0 (dark) to 1 (lit) light, with ordered dithering between steps."""
    level = (1 - max(0.0, min(1.0, light))) * (len(ramp) - 1)
    step = int(level)
    if step < len(ramp) - 1 and level - step > (BAYER[y % 4][x % 4] + 0.5) / 16:
        step += 1
    return ramp[step]


class Canvas:
    def __init__(self):
        self.pixels = [[None] * WIDTH for _ in range(HEIGHT)]

    def put(self, x, y, color):
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            self.pixels[y][x] = color

    def get(self, x, y):
        return self.pixels[y][x] if 0 <= x < WIDTH and 0 <= y < HEIGHT else None

    def polygon(self, points, paint):
        """Fills a polygon, calling paint(x, y) for each pixel's color (None leaves it)."""
        top = max(0, int(min(p[1] for p in points)))
        bottom = min(HEIGHT - 1, int(max(p[1] for p in points)) + 1)
        for y in range(top, bottom + 1):
            middle = y + 0.5
            crossings = []
            for (ax, ay), (bx, by) in zip(points, points[1:] + points[:1]):
                if (ay <= middle) != (by <= middle):
                    crossings.append(ax + (middle - ay) * (bx - ax) / (by - ay))
            crossings.sort()
            for left, right in zip(crossings[::2], crossings[1::2]):
                for x in range(max(0, round(left)), min(WIDTH, round(right))):
                    color = paint(x, y)
                    if color is not None:
                        self.put(x, y, color)

    def ellipse(self, cx, cy, rx, ry, paint):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                u, v = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
                if u * u + v * v <= 1:
                    color = paint(x, y, u, v)
                    if color is not None:
                        self.put(x, y, color)

    def line(self, x0, y0, x1, y1, color, thickness=1):
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(steps + 1):
            x, y = x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps
            for dy in range(thickness):
                for dx in range(thickness):
                    self.put(int(x + dx - thickness // 2), int(y + dy - thickness // 2), color)


class Tube:
    """A stretch of fuselage: a spine from p0 to p1, its radius going from r0 to r1."""

    def __init__(self, p0, p1, r0, r1):
        self.p0, self.p1, self.r0, self.r1 = p0, p1, r0, r1
        self.dx, self.dy = p1[0] - p0[0], p1[1] - p0[1]
        self.length = math.hypot(self.dx, self.dy)
        self.ux, self.uy = self.dx / self.length, self.dy / self.length

    def local(self, x, y):
        """How far along the spine (0 to 1) and across it (-1 top to 1 bottom) a pixel is."""
        px, py = x + 0.5 - self.p0[0], y + 0.5 - self.p0[1]
        along = (px * self.ux + py * self.uy) / self.length
        across = -px * self.uy + py * self.ux
        radius = self.r0 + (self.r1 - self.r0) * max(0.0, min(1.0, along))
        return along, across / radius

    def point(self, along, across):
        radius = self.r0 + (self.r1 - self.r0) * along
        return (self.p0[0] + self.dx * along - self.uy * across * radius,
                self.p0[1] + self.dy * along + self.ux * across * radius)

    def outline(self, steps=24):
        top = [self.point(i / steps, -1) for i in range(steps + 1)]
        bottom = [self.point(i / steps, 1) for i in range(steps, -1, -1)]
        return top + bottom


def hull_light(across, x, y):
    """Light on the hull: lit from above, a dull shine along the upper side, grime blotches."""
    light = 0.62 - 0.42 * across
    light += 0.18 * math.exp(-((across + 0.55) / 0.18) ** 2)
    light -= 0.22 * max(0.0, smooth_noise(x, y, 9, 1) - 0.55)
    light += 0.06 * (noise(x, y, 2) - 0.5)
    return light


def paint_tube(tube, x, y):
    _, across = tube.local(x, y)
    return shade(OLIVE, hull_light(across, x, y), x, y)


def draw_wing(canvas):
    # The far wing, snapped off and leaning up behind the fuselage, its underside to us
    edge = [(122, 118), (150, 112), (110, 30), (92, 36)]
    canvas.polygon(edge, lambda x, y: shade(OLIVE, 0.28 + 0.25 * (x - 92) / 58 - 0.05 * noise(x, y, 3), x, y))
    # Its torn tip, ribs showing
    canvas.polygon([(92, 36), (110, 30), (106, 26), (101, 32), (97, 27), (94, 33)],
                   lambda x, y: INSIDE[1])
    for i in range(6):
        t = 0.12 + i * 0.14
        ax, ay = 92 + (122 - 92) * t, 36 + (118 - 36) * t
        bx, by = 110 + (150 - 110) * t, 30 + (112 - 30) * t
        canvas.line(ax + 2, ay, bx - 2, by, OLIVE[4])
    # The aileron's hinge line
    canvas.line(94, 40, 126, 114, OLIVE[5])


def draw_rear(canvas):
    rear = Tube((150, 117), (276, 82), 28, 9)
    canvas.polygon(rear.outline(), lambda x, y: paint_tube(rear, x, y))
    # The fin and rudder
    fin = [(232, 80), (256, 34), (270, 26), (280, 30), (284, 78), (272, 84)]
    canvas.polygon(fin, lambda x, y: shade(OLIVE, 0.72 - 0.004 * (y - 26) - 0.18 * max(0, smooth_noise(x, y, 7, 4) - 0.5), x, y))
    canvas.line(270, 27, 274, 82, OLIVE[4])
    canvas.line(256, 34, 280, 30, OLIVE[2])
    # A bite torn out of the rudder
    for y in range(44, 63):
        for x in range(277, 286):
            if x > 279 + 2 * math.sin(y * 1.3):
                canvas.put(x, y, None)
    # The near tailplane, seen nearly edge on
    canvas.polygon([(244, 86), (290, 76), (294, 79), (252, 92)],
                   lambda x, y: shade(OLIVE, 0.55 - 0.1 * (y - 76) / 16, x, y))
    canvas.line(252, 92, 294, 79, OLIVE[5])
    # The cargo door's outline and the insignia: a faded white star on blue
    for (ax, ay), (bx, by) in (((196, 92), (214, 87)), ((214, 87), (216, 117)), ((198, 122), (216, 117)), ((196, 92), (198, 122))):
        canvas.line(ax, ay, bx, by, OLIVE[4])
    draw_star(canvas, 232, 96, 9)
    # Windows
    for i, x in enumerate((164, 178, 188)):
        y = int(rear.point((x - 150) / 126, -0.35)[1])
        dark = i == 1
        canvas.polygon([(x, y), (x + 6, y - 1), (x + 6, y + 5), (x, y + 6)],
                       lambda px, py, dark=dark: INSIDE[2] if dark else shade(GLASS, 0.7 - 0.12 * (py - y), px, py))
    return rear


def draw_star(canvas, cx, cy, radius):
    canvas.ellipse(cx, cy, radius, radius * 0.9,
                   lambda x, y, u, v: INSIGNIA_BLUE if noise(x, y, 5) > 0.12 else OLIVE[3])
    points = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        reach = radius * (0.92 if i % 2 == 0 else 0.38)
        points.append((cx + reach * math.cos(angle), cy + reach * math.sin(angle) * 0.9))
    canvas.polygon(points, lambda x, y: INSIGNIA_WHITE if noise(x, y, 6) > 0.18 else (140, 136, 122))


def draw_front(canvas):
    front = Tube((30, 122), (152, 116), 25, 30)

    def paint(x, y):
        along, across = front.local(x, y)
        if along < 0:
            # The crumpled, rounded nose
            reach = -along * front.length / (front.r0 * 0.9)
            if reach * reach + across * across > 1 - 0.18 * noise(x // 2, y // 2, 7):
                return None
        return shade(OLIVE, hull_light(across, x, y) - (0.15 if along < 0 else 0), x, y)

    nose = [front.point(0, -1)] + [(30 - 22 * math.cos(a), 122 - 25 * math.sin(a)) for a in
                                   [math.pi / 2 - i * math.pi / 12 for i in range(13)]] + [front.point(0, 1)]
    canvas.polygon(front.outline() + nose[::-1], paint)
    # Cockpit glass
    for i in range(3):
        x = 30 + i * 9
        top = 104 - i
        cracked = i == 1
        canvas.polygon([(x, top + 4), (x + 3, top), (x + 10, top - 1), (x + 9, top + 6)],
                       lambda px, py, cracked=cracked: (INSIDE[2] if cracked and noise(px, py, 8) > 0.35
                                                         else shade(GLASS, 0.85 - 0.12 * (py - top), px, py)))
    canvas.line(31, 110, 58, 107, OLIVE[4])
    # The crew door and a row of windows
    for x in (64, 84, 104, 124):
        y = int(front.point((x - 30) / 122, -0.4)[1])
        canvas.polygon([(x, y), (x + 7, y), (x + 7, y + 6), (x, y + 6)],
                       lambda px, py, y=y: shade(GLASS, 0.75 - 0.13 * (py - y), px, py))
    # Panel lines around the hull
    for x in (48, 78, 116, 140):
        along = (x - 30) / 122
        a, b = front.point(along, -0.95), front.point(along, 0.95)
        canvas.line(a[0], a[1], b[0], b[1], OLIVE[3])
    # The torn end where it broke: the dark inside of the hull and its ribs, a jagged rim
    canvas.ellipse(152, 116, 8, 29, lambda x, y, u, v: INSIDE[0] if u < -0.2 else INSIDE[2] if noise(x, y // 3, 9) > 0.3 else INSIDE[1])
    for y in range(90, 144, 7):
        canvas.line(146, y, 153, y + 1, INSIDE[0])
    for y in range(86, 147):
        rim = 149 + 6 * smooth_noise(0, y, 4, 10)
        canvas.put(int(rim), y, METAL[2])
        canvas.put(int(rim) + 1, y, METAL[3])
    return front


def draw_engine(canvas):
    # The near engine, torn from its wing and lying against the nose
    canvas.ellipse(92, 132, 31, 15, lambda x, y, u, v: OLIVE[5])
    canvas.ellipse(92, 132, 29, 13, lambda x, y, u, v: shade(OLIVE, 0.38 - 0.45 * v - 0.15 * u + 0.2 * math.exp(-((v + 0.5) / 0.2) ** 2), x, y))
    canvas.ellipse(66, 132, 7, 14, lambda x, y, u, v: shade(METAL, 0.4 - 0.35 * v, x, y) if u > -0.6 else METAL[3])
    for x in (78, 96, 108):
        canvas.line(x, 120, x, 145, OLIVE[4])
    # Exhaust stub
    canvas.polygon([(104, 140), (118, 141), (118, 145), (104, 144)], lambda x, y: METAL[3])
    # The propeller: hub and three blades bent by the crash
    blade = lambda x, y: shade(METAL, 0.6 - 0.02 * abs(y - 132), x, y)
    canvas.polygon([(59, 132), (64, 128), (54, 102), (46, 92), (47, 104)], blade)
    canvas.polygon([(58, 133), (60, 139), (38, 147), (24, 146), (40, 140)], blade)
    canvas.polygon([(62, 136), (65, 137), (64, 149), (59, 149)], blade)
    canvas.ellipse(62, 132, 5, 6, lambda x, y, u, v: shade(METAL, 0.8 - 0.4 * (u + v), x, y))


def scorch(canvas, spots):
    """Soot around where the fires burn, blotchy at the edges."""
    for y in range(HEIGHT):
        for x in range(WIDTH):
            color = canvas.get(x, y)
            if color is None:
                continue
            heat = max(1 - math.hypot((x - sx) / rx, (y - sy) / ry) for sx, sy, rx, ry in spots)
            heat += 0.35 * (smooth_noise(x, y, 4, 12) - 0.5)
            if heat > 0.7:
                canvas.put(x, y, SOOT if noise(x, y, 13) > 0.3 else INSIDE[1])
            elif heat > 0.15:
                mix = ((heat - 0.15) / 0.55) ** 1.5 * 0.85
                canvas.put(x, y, tuple(int(c * (1 - mix) + s * mix) for c, s in zip(color, SOOT)))


def holes(canvas, spots):
    """Jagged holes through the skin, ribs showing through them."""
    for cx, cy, rx, ry in spots:
        for y in range(int(cy - ry) - 2, int(cy + ry) + 3):
            for x in range(int(cx - rx) - 2, int(cx + rx) + 3):
                if canvas.get(x, y) is None:
                    continue
                reach = math.hypot((x - cx) / rx, (y - cy) / ry) + 0.35 * (noise(x // 2, y // 2, 14) - 0.5)
                if reach < 0.75:
                    canvas.put(x, y, INSIDE[0] if (x + y // 3) % 6 == 0 else INSIDE[2])
                elif reach < 1:
                    canvas.put(x, y, METAL[2] if noise(x, y, 15) > 0.5 else OLIVE[5])


def ground(canvas):
    # Dirt ploughed up in front of the nose and under the break, and scrap lying about
    canvas.ellipse(22, 149, 24, 8, lambda x, y, u, v: shade(DIRT, 0.7 - 0.5 * v + 0.2 * noise(x, y, 16), x, y) if canvas.get(x, y) is None or v > 0 else None)
    canvas.ellipse(160, 149, 22, 5, lambda x, y, u, v: shade(DIRT, 0.55 - 0.5 * v + 0.2 * noise(x, y, 17), x, y))
    for points in ([(176, 149), (183, 141), (192, 144), (189, 149)],
                   [(236, 149), (240, 145), (252, 146), (250, 149)],
                   [(128, 149), (131, 144), (138, 145), (136, 149)]):
        canvas.polygon(points, lambda x, y: shade(OLIVE, 0.5 - 0.04 * (y - 141), x, y))
    canvas.line(200, 149, 214, 140, METAL[2], 2)
    canvas.line(266, 149, 272, 143, METAL[3], 2)


def finish(canvas):
    """Darkens the silhouette's edge, so it reads against the ground and sky."""
    out = [[(0, 0, 0, 0)] * WIDTH for _ in range(HEIGHT)]
    for y in range(HEIGHT):
        for x in range(WIDTH):
            color = canvas.get(x, y)
            if color is None:
                continue
            edge = any(canvas.get(x + dx, y + dy) is None for dx, dy in ((1, 0), (-1, 0), (0, -1)))
            if edge and y < HEIGHT - 1:
                color = tuple(int(c * 0.6) for c in color)
            out[y][x] = color + (255,)
    return out


def write_png(path, rows, offsets):
    height, width = len(rows), len(rows[0])
    raw = b"".join(b"\0" + b"".join(bytes(p) for p in row) for row in rows)

    def chunk(name, body):
        return struct.pack(">I", len(body)) + name + body + struct.pack(">I", zlib.crc32(name + body))

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    png += chunk(b"grAb", struct.pack(">ii", *offsets)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)


def main():
    canvas = Canvas()
    draw_wing(canvas)
    draw_rear(canvas)
    draw_front(canvas)
    draw_engine(canvas)
    holes(canvas, [(120, 128, 7, 5), (176, 128, 6, 4), (226, 108, 5, 3)])
    scorch(canvas, [(44, 124, 20, 14), (106, 102, 20, 24), (168, 124, 18, 16), (244, 84, 22, 18)])
    ground(canvas)
    write_png(TARGET, finish(canvas), (WIDTH // 2, HEIGHT))
    print(f"{TARGET}: {WIDTH}x{HEIGHT}")


if __name__ == "__main__":
    main()
