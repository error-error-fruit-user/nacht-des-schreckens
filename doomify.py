#!/usr/bin/env python3
"""Rebuilds Nacht des Schreckens' World at War weapons and sounds from your own game.

World at War's assets can't be shared, so they aren't in this repository. This makes them from your
own copy of Call of Duty: World at War, into nacht-waw/: a pk3 folder that UZDoom loads after nacht.
Run it before playing for the first time, and again after nacht's weapons change:

  1. Start World at War and, in Zombies (solo), load Der Riese. Stay in the map.
  2. python3 doomify.py

It needs Blender (blender.org), which renders the weapons. It runs doomify-waw: the executable in
doomify/ for this system, or (with --source, or when there is none) doomify-waw built from its
repository with Rust's cargo. Anything after the options goes to doomify-waw build (--help lists
them: --force renders everything again, --blender PATH picks Blender).

  python3 doomify.py [--source] [--pack] [-- doomify-waw build options]
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.join(HERE, "doomify")
OUTPUT = os.path.join(HERE, "nacht-waw")
REPOSITORIES = {
    "doomify-waw": "https://github.com/error-error-fruit-user/doomify-waw.git",
    "hell-hound": "https://github.com/error-error-fruit-user/hell-hound.git",
}


def executable_name():
    return "doomify-waw.exe" if platform.system() == "Windows" else "doomify-waw"


def run(command, **options):
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True, **options)


def from_source():
    """doomify-waw built from its repository, cloned (or updated) into doomify/src with hell-hound,
    which it is built against, next to it."""
    for tool in ("git", "cargo"):
        if shutil.which(tool) is None:
            sys.exit(f"Building doomify-waw needs {tool} (git-scm.com, rustup.rs)")
    sources = os.path.join(FOLDER, "src")
    os.makedirs(sources, exist_ok=True)
    for name, url in REPOSITORIES.items():
        path = os.path.join(sources, name)
        if os.path.isdir(os.path.join(path, ".git")):
            run(["git", "-C", path, "pull", "--ff-only"])
        else:
            run(["git", "clone", "--depth", "1", url, path])
    project = os.path.join(sources, "doomify-waw")
    run(["cargo", "build", "--release", "--manifest-path", os.path.join(project, "Cargo.toml")])
    return os.path.join(project, "target", "release", executable_name())


def pack():
    """nacht-waw/ zipped into nacht-waw.pk3, for launchers that take only pk3s."""
    target = OUTPUT + ".pk3"
    with zipfile.ZipFile(target + ".part", "w", zipfile.ZIP_DEFLATED) as archive:
        for root, _, files in sorted(os.walk(OUTPUT)):
            for name in sorted(files):
                path = os.path.join(root, name)
                archive.write(path, os.path.relpath(path, OUTPUT).replace(os.sep, "/"))
    os.replace(target + ".part", target)
    print("Packed", target)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--source", action="store_true",
                        help="build doomify-waw from its repository instead of using doomify/'s")
    parser.add_argument("--pack", action="store_true", help="also zip nacht-waw/ into nacht-waw.pk3")
    parser.add_argument("rest", nargs="*", help="options for doomify-waw build, after --")
    args = parser.parse_args()

    executable = os.path.join(FOLDER, executable_name())
    if args.source or not os.path.isfile(executable):
        if not args.source:
            print(f"No {executable_name()} in doomify/ for this system: building it from source.")
        executable = from_source()
    run([executable, "build", FOLDER, *args.rest])
    if args.pack:
        pack()
    print("\nDone. Load nacht-waw after Horde Hammer and nacht, for example:")
    print("  uzdoom -iwad freedoom2.wad -file horde-hammer.pk3 nacht nacht-waw")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(f"doomify failed: {error}")
