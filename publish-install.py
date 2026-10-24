#!/usr/bin/env python3
"""Publish Nacht des Schreckens, then install it with the nacht-install just published.

usage: python3 publish-install.py [--accept] [--no-build | --source] [nacht-install options]

First it says, under a red warning, exactly what it will do, and asks before doing any of it
(--accept goes ahead without asking). Then it builds the release with publish.py (the pk3s, and
nacht-install for Windows and as an AppImage, into published/releases/), or with --source the pk3s
and nacht-install for this machine only (cargo build --release), or with --no-build nothing at
all; and runs the nacht-install in published/releases/, which installs the pk3s, tdl and Blender
where it is asked to (--mode) and offers to run doomify.py. --mode, --dir, --yes, --no-tdl,
--no-uzdoom, --no-freedoom, --no-blender, --no-doomify and --blender go to nacht-install (see its
--help).

Dependency-free Python 3.8+.
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
RELEASES = os.path.join(HERE, "published", "releases")
WINDOWS = platform.system() == "Windows"
EXE = ".exe" if WINDOWS else ""
NAME = "nacht-des-schreckens"


def run(command, cwd=HERE):
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True, cwd=cwd)


def warning(lines):
    """`lines` under a red '--- Warning ---' (plain where the output isn't a terminal)."""
    if WINDOWS:
        os.system("")  # lets the Windows console show colors
    color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
    print("\033[31m--- Warning ---\033[0m" if color else "--- Warning ---")
    width = min(shutil.get_terminal_size().columns, 100)
    for line in lines:
        # a step's later lines line up under its text
        hang = len(line) - len(line.lstrip(" -"))
        print(textwrap.fill(line, width, subsequent_indent=" " * hang,
                            break_on_hyphens=False, break_long_words=False) if line else "")
    print()


def agreed(accept):
    if accept:
        return True
    if not sys.stdin.isatty():
        sys.exit("There is no one to ask, so nothing was done: pass --accept to go ahead.")
    return input("Go ahead? [y/N] ").strip().lower() in ("y", "yes")


def plan(args):
    """What saying yes does, step by step."""
    pk3s = ("pack nacht/ into published/releases/nacht.pk3 (with LICENSE-weather) and "
            "../horde-hammer into horde-hammer.pk3 (in its published/releases/, and a copy here), "
            "and nacht-waw/ into published/artifacts/nacht-waw.pk3 if doomify.py has built it")
    lines = ["Saying yes will:"]
    if args.no_build:
        lines.append("  - build nothing, and install what published/releases/ has now")
    elif args.source:
        lines.append(f"  - {pk3s}, replacing what is there")
        lines.append(f"  - build nacht-install{EXE} for this machine (cargo build --release in "
                     "installer/) and copy it into published/releases/")
    else:
        lines.append(f"  - {pk3s}, replacing what is there")
        lines.append("  - build nacht-install into published/releases/: as an AppImage (needs "
                     "mksquashfs) and cross-built for Windows (Rust's x86_64-pc-windows-gnu target)")
    lines.append("  - run nacht-install from published/releases/, which:")
    if WINDOWS:
        user, system = (f"%LOCALAPPDATA%\\Programs\\{NAME}", f"%ProgramFiles%\\{NAME}")
    else:
        user, system = (f"~/.local/opt/{NAME}", f"/opt/{NAME}")
    where = {
        "in-place": "    - installs in published/releases/ itself (or --dir)",
        "user": f"    - installs in {user} (or --dir)",
        "system": f"    - installs in {system} (or --dir), which needs "
                  f"{'administrator' if WINDOWS else 'root'}",
    }
    lines.append(where.get(args.mode) or
                 f"    - asks where to install: in place, for you ({user}) or for everyone "
                 f"({system}, needs {'administrator' if WINDOWS else 'root'})")
    lines.append("    - puts horde-hammer.pk3 and nacht.pk3 in its wads/, and doomify.py with its "
                 f"settings in {NAME}/ there, with a doomify-waw: the one beside it, the workspace's "
                 "(../doomify-waw/published/releases/) or else downloaded from doomify-waw's latest "
                 "GitHub release")
    if not args.no_tdl:
        tdl = ("    - runs tdl-install (beside it, the workspace's ../tdl/published/releases/, or else "
               "downloaded from tdl's latest GitHub release), which puts tdl there")
        if args.mode != "in-place":
            tdl += " with the tdl command on the PATH"
        downloads = [name for name, left_out in (("UZDoom 5.0.3", args.no_uzdoom),
                                                 ("Freedoom 0.13.0", args.no_freedoom)) if not left_out]
        if downloads:
            tdl += f" and downloads {' and '.join(downloads)} beside it"
        lines.append(tdl)
    if args.blender:
        lines.append(f"    - renders with the Blender at {args.blender}")
    elif not args.no_blender:
        lines.append("    - downloads Blender 4.2.9 LTS into blender/ there, checked against its "
                     "published hash, if no Blender 4.0 or newer is installed"
                     + (" (--yes: without asking)" if args.yes else ", after asking"))
    if not args.no_doomify:
        lines.append("    - if World at War is running with Der Riese loaded, runs doomify.py"
                     + (" (--yes: without asking)" if args.yes else ", after asking")
                     + ", which rebuilds the weapons from your game into nacht-waw.pk3 (about an "
                     "hour the first time)")
    lines.append("")
    lines.append("To change that: --no-build installs what is published already, --source builds only "
                 "for this machine, --no-tdl, --no-uzdoom, --no-freedoom, --no-blender and "
                 "--no-doomify leave those out, --blender PATH uses your Blender, --yes answers "
                 "nacht-install's questions, and --mode and --dir say where.")
    return lines


def build(args):
    if args.no_build:
        return
    if args.source:
        run([sys.executable, "publish.py", "--no-appimages"])
        run(["cargo", "build", "--release"], cwd=os.path.join(HERE, "installer"))
        shutil.copy2(os.path.join(HERE, "installer", "target", "release", "nacht-install" + EXE),
                     os.path.join(RELEASES, "nacht-install" + EXE))
        return
    run([sys.executable, "publish.py"])
    # 🧹 a plain nacht-install left by --source would be taken over the AppImage just built
    leftover = os.path.join(RELEASES, "nacht-install")
    if not WINDOWS and os.path.isfile(leftover):
        os.remove(leftover)


def installer():
    """The nacht-install in published/releases/: the .exe on Windows, else the plain one --source
    built or the AppImage."""
    names = ["nacht-install.exe"] if WINDOWS else ["nacht-install", "nacht-install.AppImage"]
    for name in names:
        path = os.path.join(RELEASES, name)
        if os.path.isfile(path):
            return path
    sys.exit("There is no nacht-install in published/releases/: build it (leave out --no-build).")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--accept", action="store_true", help="go ahead without asking")
    build_how = parser.add_mutually_exclusive_group()
    build_how.add_argument("--no-build", action="store_true",
                           help="install what published/releases/ has now, building nothing")
    build_how.add_argument("--source", action="store_true",
                           help="build the pk3s and nacht-install for this machine only")
    passed = parser.add_argument_group("passed to nacht-install")
    passed.add_argument("--mode", choices=["in-place", "user", "system"])
    passed.add_argument("--dir")
    passed.add_argument("--yes", action="store_true", help="answer yes to nacht-install's questions")
    for flag in ("--no-tdl", "--no-uzdoom", "--no-freedoom", "--no-blender", "--no-doomify"):
        passed.add_argument(flag, action="store_true")
    passed.add_argument("--blender", metavar="PATH")
    args = parser.parse_args()

    warning(plan(args))
    if not agreed(args.accept):
        sys.exit("Nothing was done.")
    build(args)
    command = [installer()]
    for flag, value in (("--mode", args.mode), ("--dir", args.dir), ("--blender", args.blender)):
        if value:
            command += [flag, value]
    command += [flag for flag, on in (("--yes", args.yes), ("--no-tdl", args.no_tdl),
                                      ("--no-uzdoom", args.no_uzdoom),
                                      ("--no-freedoom", args.no_freedoom),
                                      ("--no-blender", args.no_blender),
                                      ("--no-doomify", args.no_doomify)) if on]
    run(command)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(f"publish-install failed: {error}")
