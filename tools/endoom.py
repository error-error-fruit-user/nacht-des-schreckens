#!/usr/bin/env python3
"""Draw nacht's ENDOOM (nacht/ENDOOM.lmp): the text screen UZDoom shows as it exits (showendoom).

usage: python3 tools/endoom.py

Dependency-free Python 3.8+. An ENDOOM is the 80x25 text screen of DOS: for each cell a code page
437 character and an attribute byte (foreground in the low four bits, background in the next
three). This one is the title in blood with whispers from the bunker under it. The whispers are
hints, never instructions: what they hint at is for players to find.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "nacht", "ENDOOM.lmp")
COLUMNS, ROWS = 80, 25

# The text mode colours used
BLACK, RED, GRAY, DARK_GRAY, LIGHT_RED, WHITE = 0, 4, 7, 8, 12, 15
FULL, DRIP, SHADE = 0xDB, 0xDF, 0xB1

WHISPERS = [
    "The box keeps more than it gives. Wound both its flanks, then kick it.",
    "A boot can change the box's mind, or knock its gift into the dirt.",
    "What the box shows, a kick may claim. Claims are forgotten when you leave.",
    "The box has no love for explosions. It will move to get away from them.",
    "Not every bottle on the floor is a gift. Someone here likes a joke.",
    "What you carry beside your guns has a button of its own.",
    "The box hides a red key. It opens a door, if you hit the door with it.",
    "Go down with the twin pistols in hand and they will keep you company.",
    "The dead may lift you off burning ground. Do not stay there to thank them.",
    "Those who have risen find the red key easier to come by.",
]


def cell(char, foreground, background=BLACK):
    return bytes([char if isinstance(char, int) else ord(char), foreground | background << 4])


def screen():
    cells = [[cell(" ", GRAY)] * COLUMNS for _ in range(ROWS)]

    def write(row, column, text, foreground, background=BLACK):
        for i, char in enumerate(text):
            if 0 <= column + i < COLUMNS:
                cells[row][column + i] = cell(char, foreground, background)

    def centred(row, text, foreground, background=BLACK):
        write(row, (COLUMNS - len(text)) // 2, text, foreground, background)

    # 🩸 a band of blood across the top, the name in it, dripping off its bottom edge
    for row in range(3):
        write(row, 0, " " * COLUMNS, WHITE, RED)
    centred(1, "N A C H T   D E S   S C H R E C K E N S", WHITE, RED)
    for column in range(COLUMNS):
        # drips of different lengths, from the column alone, so it is the same every time
        mixed = (column * 374761393 + 668265263) & 0xFFFFFFFF
        length = ((mixed ^ (mixed >> 13)) * 1274126177 >> 16) % 7
        if length < 3:
            for k in range(length + 1):
                cells[3 + k][column] = cell(DRIP if k == length else FULL, RED)
    centred(6, "whispers from the bunker", DARK_GRAY)
    for i, whisper in enumerate(WHISPERS):
        write(8 + i, 2, chr(SHADE), RED)
        write(8 + i, 4, whisper, LIGHT_RED if i % 2 == 0 else GRAY)
    centred(20, "The dead are patient. They will be here when you come back.", DARK_GRAY)
    centred(23, "Nacht des Schreckens, on Horde Hammer, in UZDoom", RED)
    return b"".join(b"".join(row) for row in cells)


def main():
    for whisper in WHISPERS:
        assert len(whisper) <= COLUMNS - 5, f"too long for a line: {whisper}"
    data = screen()
    assert len(data) == COLUMNS * ROWS * 2
    with open(OUT, "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
