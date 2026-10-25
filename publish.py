#!/usr/bin/env python3
"""Pack the mod folder into a playable .pk3 (a zip with another extension) in published/releases/.

usage: python3 publish.py [--out FILE] [--strict] [--no-library] [--no-appimages]

When Horde Hammer's repository is next to this one (../horde-hammer), it is packed too, into its own
published/releases/ only, so its pk3 there always matches nacht (a library older than nacht stops UZDoom at
startup with "unknown actor property"). --no-library skips that.
With the default output, published/releases/ also gets a copy of horde-hammer.pk3 and config.ini (nacht's keyboard controls). (doomify.py and the doomify/ TOMLs are embedded in nacht-install, not published.)
The nacht-waw/ folder is packed as published/artifacts/nacht-waw.pk3, outside that folder (when doomify.py has
built it), so it never ships with the rest. nacht-waw is made from the player's own game: it is for
them alone, never share it.
nacht-install is built there too, as an AppImage (tools/appimage.py; needs cargo and mksquashfs)
and as a Windows executable (cross-built for x86_64-pc-windows-gnu). The tools it installs (tdl,
doomify-waw...) are not published here. --no-appimages skips both.

Dependency-free Python 3.8+. The pk3 is reproducible: files go in sorted order with a fixed
timestamp, so the same folder always packs to the same bytes (and tdl hashes it the same).
Editor leftovers (Ultimate Doom Builder's .dbs and .backup files, OS junk) are left out.

It also warns about things UZDoom gets wrong silently:
  - two paths that differ only in case (lookups in a pk3 ignore case, so one hides the other)
  - lumps in a namespace folder (sprites/, graphics/, ...) whose name is longer than 8 characters
    before the extension, which the engine truncates into lump names that can collide (sounds and
    music are left alone: SNDINFO and MAPINFO can name them by full path)
  - sprite files whose names aren't a sprite frame (4 letters, then frame and rotation pairs)
  - SNDINFO entries naming a file by path that isn't in the pk3
--strict turns the warnings into a failure.
"""

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
GROANS_GITHUB = "https://raw.githubusercontent.com/error-error-fruit-user/installation-groans/main/"


def load_groans():
    """installation-groans' groans.py, which these scripts speak through: the project's
    installation-groans submodule, else the workspace's checkout beside the project, else a copy
    fetched from its GitHub into published/artifacts/groans/."""
    project = os.path.dirname(os.path.abspath(__file__))
    places = [os.path.join(project, "installation-groans"),
              os.path.join(os.path.dirname(project), "installation-groans"),
              os.path.join(project, "published", "artifacts", "groans")]
    folder = next((place for place in places if os.path.isfile(os.path.join(place, "groans.py"))), None)
    if folder is None:
        folder = places[-1]
        try:
            import urllib.request
            os.makedirs(folder, exist_ok=True)
            for name in ("groans.py", "toiling-through-hell.toml", "computer-speak.toml"):
                with urllib.request.urlopen(GROANS_GITHUB + name, timeout=10) as answer:
                    with open(os.path.join(folder, name), "wb") as out:
                        out.write(answer.read())
        except Exception as error:
            sys.exit(f"installation-groans isn't beside {os.path.basename(project)}, and couldn't be "
                     f"fetched ({error}): clone it beside it.")
    if folder not in sys.path:
        sys.path.insert(0, folder)
    import groans
    return groans


groans = load_groans()


import appimage  # noqa: E402

# The folder that becomes the root of the pk3, and the name of the pk3
PACKAGE = "nacht"
NAME = "nacht.pk3"
# Copied next to the pk3 and into it under licenses/
LICENSES = ["LICENSE-weather"]
# nacht's keyboard controls, the ini a tdl profile is given: copied next to the pk3
INI = "config.ini"

OUT = os.path.join("published", "releases")
# What running the installed game makes (nacht-waw, from the player's own game), next to OUT
ARTIFACTS = os.path.join("published", "artifacts")
# The library nacht runs on, packed alongside it when its repository is here
LIBRARY = os.path.join("..", "horde-hammer")
LIBRARY_PK3 = "horde-hammer.pk3"
# Built by doomify.py, loaded after nacht; packed as a pk3 in ARTIFACTS, outside OUT
WAW = "nacht-waw"
WAW_NAME = "nacht-waw.pk3"

# 1980-01-01, the earliest time a zip can hold
EPOCH = (1980, 1, 1, 0, 0, 0)

SKIPPED_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
SKIPPED_SUFFIXES = (".dbs", ".bak", ".tmp", "~")
# map01.wad.backup1, map01.wad.autosave1 and friends from Ultimate Doom Builder
SKIPPED_PATTERN = re.compile(r"\.wad\.\w+$", re.IGNORECASE)

# Folders whose files are found by lump name (up to 8 characters)
NAMESPACES = {"sprites", "flats", "textures", "patches", "graphics", "hires", "colormaps",
              "acs", "voxels"}
SPRITE = re.compile(r"^[a-z0-9_\[\]\\^-]{4}([a-z\[\]\\^][0-9a-g]){1,2}$", re.IGNORECASE)


def skipped(name):
    return (name in SKIPPED_NAMES or name.startswith(".") or name.endswith(SKIPPED_SUFFIXES)
            or SKIPPED_PATTERN.search(name) is not None)


def gather(root):
    """Every file under root to pack, as (path on disk, path in the pk3), sorted by pk3 path."""
    files = []
    for folder, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for name in names:
            if skipped(name):
                continue
            path = os.path.join(folder, name)
            files.append((path, os.path.relpath(path, root).replace(os.sep, "/")))
    return sorted(files, key=lambda f: f[1].lower())


def warnings(files):
    found = []
    seen = {}
    for _, inside in files:
        other = seen.setdefault(inside.lower(), inside)
        if other != inside:
            found.append(f"{inside} and {other} differ only in case, so one hides the other")
    for _, inside in files:
        parts = inside.split("/")
        if len(parts) < 2 or parts[0].lower() not in NAMESPACES:
            continue
        stem = os.path.splitext(parts[-1])[0]
        if len(stem) > 8:
            found.append(f"{inside}: lump names are at most 8 characters, the engine sees {stem[:8]}")
        if parts[0].lower() == "sprites" and not SPRITE.match(stem):
            found.append(f"{inside}: not a sprite frame name (like PLNEA0 or PLNEA2A8)")
    found += missing_sounds(files)
    return found


def missing_sounds(files):
    """SNDINFO lines like `logical/name path/to/file` whose file isn't packed. A path may leave
    out the extension, and case doesn't matter."""
    packed = set()
    for _, inside in files:
        packed.add(inside.lower())
        packed.add(os.path.splitext(inside)[0].lower())
    found = []
    for path, inside in files:
        # SNDINFO lumps at the root, and the files they $include (like weapons/colt/sndinfo.txt)
        if os.path.splitext(os.path.basename(inside))[0].lower() != "sndinfo":
            continue
        with open(path, errors="replace") as f:
            for number, line in enumerate(f, 1):
                words = line.split("//")[0].split()
                if len(words) == 2 and not words[0].startswith("$") and "/" in words[1]:
                    if words[1].strip('"').lower() not in packed:
                        found.append(f"{inside}:{number}: {words[0]} names {words[1]}, which isn't packed")
    return found


def pack(files, target):
    """Write the pk3 next to target and rename it into place, so a half-written pk3 never
    replaces a good one."""
    partial = target + ".tmp"
    with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as pk3:
        for path, inside in files:
            info = zipfile.ZipInfo(inside, EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(path, "rb") as f:
                pk3.writestr(info, f.read())
    with zipfile.ZipFile(partial) as pk3:
        bad = pk3.testzip()
        if bad is not None:
            sys.exit(f"{partial} is corrupt at {bad}")
    os.replace(partial, target)


def find_tdl():
    """tdl, the workspace's first (../tdl/published/releases/), else the one on the PATH."""
    releases = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tdl", "published", "releases")
    names = ["tdl.exe"] if platform.system() == "Windows" else ["tdl", "tdl.AppImage"]
    for name in names:
        path = os.path.join(releases, name)
        if os.path.isfile(path):
            return os.path.normpath(path)
    return shutil.which("tdl")


def set_up_platzhalters():
    """Sets up nacht's loadout and its Nacht des Platzhalters profile with `tdl setup setup.toml`,
    then says, in a big way, that it can be played."""
    groans.section("setup")
    tdl = find_tdl()
    if tdl is None:
        groans.other("note: no tdl to set up Nacht des Platzhalters with (../tdl/published/releases/ "
                     "or the PATH); with tdl, run: tdl setup setup.toml", sys.stderr)
        return
    try:
        groans.run([tdl, "setup", "setup.toml"])
    except subprocess.CalledProcessError as error:
        groans.other(f"note: tdl setup setup.toml failed ({error.returncode})", sys.stderr)
        return
    groans.section("play")
    command = f'{tdl} --loadout published/artifacts/loadout launch "Nacht des Platzhalters"'
    groans.say("ready", f"Nacht des Platzhalters is ready to play: {command}",
               what="Nacht des Platzhalters", command=command)
    groans.other("Doom's weapons stand in for World at War's, in a loadout of nacht's own; for "
                 "Nacht des Schreckens, start World at War on Der Riese and run doomify.py.")


def clear(folder):
    """Empties `folder` for the new release. One that can't be emptied, left by a run with sudo,
    is said, with how to take it back, rather than failed on."""
    try:
        shutil.rmtree(folder)
    except FileNotFoundError:
        pass
    except PermissionError as error:
        import getpass
        sys.exit(f"{folder} can't be replaced ({error.strerror}: {error.filename}). It was left by "
                 "another user, root most likely, by a run with sudo. Take it back with:\n"
                 f"  sudo chown -R {getpass.getuser()} {os.path.abspath(os.path.dirname(folder))}")
    os.makedirs(folder)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", help=f"where to write the pk3 (default: {OUT}/{NAME}, and the "
                        f"licenses next to it); any other path writes only the pk3")
    parser.add_argument("--strict", action="store_true", help="fail on warnings")
    parser.add_argument("--no-library", action="store_true", help="don't pack Horde Hammer too")
    parser.add_argument("--no-appimages", action="store_true", help="don't build the AppImages")
    parser.add_argument("--no-setup", action="store_true",
                        help="don't set up the Nacht des Platzhalters profile (setup.toml)")
    parser.add_argument("--computer-speak", action="store_true",
                        help="say what it does plainly and formally, rather than as a descent "
                             "through hell")
    options = parser.parse_args()
    groans.start(None, options.computer_speak)
    groans.say("begin", "Publishing Nacht des Schreckens", what="Nacht des Schreckens", place=os.path.join("published", "releases"))
    groans.section("pack")

    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)
    if not os.path.isdir(PACKAGE):
        sys.exit(f"no {PACKAGE}/ folder next to publish.py")

    files = gather(PACKAGE)
    files += [(license, f"licenses/{license}.txt") for license in LICENSES]

    found = warnings(files)
    for warning in found:
        groans.other("warning: " + warning, sys.stderr)
    if found and options.strict:
        sys.exit(f"{len(found)} warning(s), and --strict was given")

    if options.out:
        target = options.out
        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    else:
        clear(OUT)
        target = os.path.join(OUT, NAME)
        for license in LICENSES:
            shutil.copy(license, OUT)
        shutil.copy(INI, OUT)

    pack(files, target)
    groans.built(target, len(files))

    # The library's own published/ is refreshed too (and left there), so it never lags behind nacht
    library_script = os.path.join(LIBRARY, "publish.py")
    if not options.no_library and os.path.isfile(library_script):
        library = [sys.executable, "-I", "publish.py"]
        if options.computer_speak:
            library.append("--computer-speak")
        groans.run(library, cwd=LIBRARY, voiced=True)

    if not options.out:
        library_pk3 = os.path.join(LIBRARY, "published", "releases", LIBRARY_PK3)
        if not options.no_library and os.path.isfile(library_pk3):
            shutil.copy(library_pk3, OUT)
            groans.built(os.path.join(OUT, LIBRARY_PK3))
        if os.path.isdir(WAW):
            waw_target = os.path.join(ARTIFACTS, WAW_NAME)
            os.makedirs(ARTIFACTS, exist_ok=True)
            waw_files = gather(WAW)
            pack(waw_files, waw_target)
            groans.built(waw_target, len(waw_files))
        else:
            groans.other(f"note: no {WAW}/ folder to pack; run doomify.py first", sys.stderr)
        if not options.no_appimages:
            appimage.build_all(OUT)
            appimage.build_exes(OUT)
        if not options.no_setup:
            set_up_platzhalters()


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        groans.finish("Nacht des Schreckens", ok=False,
                      error=f"{' '.join(map(str, error.cmd))} ended with code {error.returncode}")
        sys.exit(1)
    except SystemExit as stop:
        # 🗣️ a reason to stop is said in the voice too
        if isinstance(stop.code, str):
            groans.say("problem", stop.code, problem=stop.code)
            sys.exit(1)
        raise
    groans.finish("Nacht des Schreckens")
