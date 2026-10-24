#!/usr/bin/env python3
"""Pack the mod folder into a playable .pk3 (a zip with another extension) in published/releases/.

usage: python3 publish.py [--out FILE] [--strict] [--no-library] [--no-appimages]

When Horde Hammer's repository is next to this one (../horde-hammer), it is packed too, into its own
published/releases/ only, so its pk3 there always matches nacht (a library older than nacht stops UZDoom at
startup with "unknown actor property"). --no-library skips that.
With the default output, published/releases/ also gets a copy of horde-hammer.pk3. (doomify.py and the doomify/ TOMLs are embedded in nacht-install, not published.)
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
import re
import shutil
import subprocess
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import appimage  # noqa: E402

# The folder that becomes the root of the pk3, and the name of the pk3
PACKAGE = "nacht"
NAME = "nacht.pk3"
# Copied next to the pk3 and into it under licenses/
LICENSES = ["LICENSE-weather"]

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


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", help=f"where to write the pk3 (default: {OUT}/{NAME}, and the "
                        f"licenses next to it); any other path writes only the pk3")
    parser.add_argument("--strict", action="store_true", help="fail on warnings")
    parser.add_argument("--no-library", action="store_true", help="don't pack Horde Hammer too")
    parser.add_argument("--no-appimages", action="store_true", help="don't build the AppImages")
    options = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)
    if not os.path.isdir(PACKAGE):
        sys.exit(f"no {PACKAGE}/ folder next to publish.py")

    files = gather(PACKAGE)
    files += [(license, f"licenses/{license}.txt") for license in LICENSES]

    found = warnings(files)
    for warning in found:
        print("warning: " + warning, file=sys.stderr)
    if found and options.strict:
        sys.exit(f"{len(found)} warning(s), and --strict was given")

    if options.out:
        target = options.out
        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    else:
        shutil.rmtree(OUT, ignore_errors=True)
        os.makedirs(OUT)
        target = os.path.join(OUT, NAME)
        for license in LICENSES:
            shutil.copy(license, OUT)

    pack(files, target)
    size = os.path.getsize(target) / (1024 * 1024)
    print(f"{target}: {len(files)} files, {size:.1f} MB")

    # The library's own published/ is refreshed too (and left there), so it never lags behind nacht
    library_script = os.path.join(LIBRARY, "publish.py")
    if not options.no_library and os.path.isfile(library_script):
        subprocess.run([sys.executable, "-I", "publish.py"], cwd=LIBRARY, check=True)

    if not options.out:
        library_pk3 = os.path.join(LIBRARY, "published", "releases", LIBRARY_PK3)
        if not options.no_library and os.path.isfile(library_pk3):
            shutil.copy(library_pk3, OUT)
            print(f"{os.path.join(OUT, LIBRARY_PK3)}: copied")
        if os.path.isdir(WAW):
            waw_target = os.path.join(ARTIFACTS, WAW_NAME)
            os.makedirs(ARTIFACTS, exist_ok=True)
            waw_files = gather(WAW)
            pack(waw_files, waw_target)
            size = os.path.getsize(waw_target) / (1024 * 1024)
            print(f"{waw_target}: {len(waw_files)} files, {size:.1f} MB")
        else:
            print(f"note: no {WAW}/ folder to pack; run doomify.py first", file=sys.stderr)
        if not options.no_appimages:
            appimage.build_all(OUT)
            appimage.build_exes(OUT)


if __name__ == "__main__":
    main()
