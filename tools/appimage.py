#!/usr/bin/env python3
"""Build Linux AppImages of the programs next to this repository, for publish.py.

usage: python3 tools/appimage.py [--out FOLDER] [program...]

Builds nacht-install (installer/ here) with `cargo build --release`, and wraps the executable in
nacht-install.AppImage in FOLDER (default: published/releases/). The tools it needs (tdl,
tdl-install, doomify-waw) are not published with it: it takes them from beside it or downloads
them. They are command-line programs: the AppImage runs the program with its arguments, and its
desktop entry opens a terminal.

An AppImage is the runtime stub (secrets/appimage/runtime-x86_64, downloaded from
github.com/AppImage/type2-runtime the first time) followed by a squashfs of the program. Needs
cargo and mksquashfs (squashfs-tools). Linux only. Dependency-free Python 3.8+.
"""

import argparse
import os
import platform
import shutil
import struct
import subprocess
import sys
import tempfile
import urllib.request
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNTIME = os.path.join(ROOT, "secrets", "appimage", "runtime-x86_64")
# The target the Windows executables are cross-built for
WINDOWS = "x86_64-pc-windows-gnu"
RUNTIME_URL = "https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64"

# program -> (checkout next to this repository, its package when the checkout has several, and
# its Cargo.toml when that isn't the checkout's own)
PROGRAMS = {
    "nacht-install": ("nacht-des-schreckens", None, "installer/Cargo.toml"),
}

DESKTOP = """[Desktop Entry]
Type=Application
Name={name}
Exec={name}
Icon={name}
Categories=Utility;
Terminal=true
"""

APPRUN = """#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/{name}" "$@"
"""


def icon():
    """A plain 64x64 PNG, since an AppImage wants an icon."""
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))
    row = b"\x00" + bytes((0x7a, 0x1f, 0x1f)) * 64
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 64, 64, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(row * 64, 9)) + chunk(b"IEND", b""))


def runtime():
    if not os.path.isfile(RUNTIME):
        print(f"downloading {RUNTIME_URL}", flush=True)
        os.makedirs(os.path.dirname(RUNTIME), exist_ok=True)
        urllib.request.urlretrieve(RUNTIME_URL, RUNTIME + ".part")
        os.replace(RUNTIME + ".part", RUNTIME)
    return RUNTIME


def build(name, project, package, manifest, triple=None):
    """cargo build --release (for the target triple, if one is given), and the path of the
    executable."""
    folder = os.path.normpath(os.path.join(ROOT, "..", project))
    command = ["cargo"] + (["+stable"] if triple else []) + ["build", "--release"]
    command += ["--target", triple] if triple else []
    command += ["-p", package] if package else []
    target = os.path.join(folder, "target")
    if manifest:
        command += ["--manifest-path", manifest]
        target = os.path.join(folder, os.path.dirname(manifest), "target")
    print("+", " ".join(command), f"(in {project})", flush=True)
    subprocess.run(command, cwd=folder, check=True)
    return os.path.join(target, triple or "", "release", name + (".exe" if triple else ""))


def make(name, executable, target):
    with tempfile.TemporaryDirectory() as work:
        app = os.path.join(work, name + ".AppDir")
        os.makedirs(os.path.join(app, "usr", "bin"))
        shutil.copy(executable, os.path.join(app, "usr", "bin", name))
        with open(os.path.join(app, "AppRun"), "w") as f:
            f.write(APPRUN.format(name=name))
        with open(os.path.join(app, name + ".desktop"), "w") as f:
            f.write(DESKTOP.format(name=name))
        with open(os.path.join(app, name + ".png"), "wb") as f:
            f.write(icon())
        os.symlink(name + ".png", os.path.join(app, ".DirIcon"))
        os.chmod(os.path.join(app, "AppRun"), 0o755)
        os.chmod(os.path.join(app, "usr", "bin", name), 0o755)

        image = os.path.join(work, "image.squashfs")
        subprocess.run(["mksquashfs", app, image, "-root-owned", "-noappend", "-quiet",
                        "-comp", "gzip"], check=True, stdout=subprocess.DEVNULL)
        partial = target + ".tmp"
        with open(partial, "wb") as out:
            for part in (runtime(), image):
                with open(part, "rb") as f:
                    shutil.copyfileobj(f, out)
        os.chmod(partial, 0o755)
        os.replace(partial, target)


def rust_on_path():
    """Puts rustup's folder ($CARGO_HOME/bin, else ~/.cargo/bin) on the PATH when cargo isn't on
    it, as a shell that never ran rustup's profile line leaves it; everything this runs inherits it."""
    if shutil.which("cargo"):
        return
    home = os.environ.get("CARGO_HOME") or os.path.join(os.path.expanduser("~"), ".cargo")
    folder = os.path.join(home, "bin")
    if any(os.path.isfile(os.path.join(folder, name)) for name in ("cargo", "cargo.exe")):
        os.environ["PATH"] = folder + os.pathsep + os.environ.get("PATH", "")


def build_all(out, names=None):
    """Make the AppImages of names (default: all) in out. Returns the paths made."""
    rust_on_path()
    if platform.system() != "Linux":
        print("note: AppImages are Linux-only; skipped", file=sys.stderr)
        return []
    for tool in ("cargo", "mksquashfs"):
        if shutil.which(tool) is None:
            sys.exit(f"making AppImages needs {tool}")
    os.makedirs(out, exist_ok=True)
    made = []
    for name in names or PROGRAMS:
        project, package, manifest = PROGRAMS[name]
        if not os.path.isdir(os.path.join(ROOT, "..", project)):
            print(f"note: no ../{project} next to this repository; no {name} AppImage",
                  file=sys.stderr)
            continue
        target = os.path.join(out, f"{name}.AppImage")
        make(name, build(name, project, package, manifest), target)
        print(f"{target}: {os.path.getsize(target) / (1024 * 1024):.1f} MB")
        made.append(target)
    return made


def build_exes(out, names=None):
    """Cross-build the Windows executables of names (default: all) into out. Returns the paths."""
    rust_on_path()
    for tool in ("cargo",):
        if shutil.which(tool) is None:
            sys.exit(f"making the Windows executables needs {tool}")
    os.makedirs(out, exist_ok=True)
    made = []
    for name in names or PROGRAMS:
        project, package, manifest = PROGRAMS[name]
        if not os.path.isdir(os.path.join(ROOT, "..", project)):
            print(f"note: no ../{project} next to this repository; no {name}.exe", file=sys.stderr)
            continue
        target = os.path.join(out, name + ".exe")
        shutil.copy(build(name, project, package, manifest, WINDOWS), target)
        print(f"{target}: {os.path.getsize(target) / (1024 * 1024):.1f} MB")
        made.append(target)
    return made


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=os.path.join(ROOT, "published", "releases"), help="where to write them")
    parser.add_argument("programs", nargs="*", choices=list(PROGRAMS),
                        help="only these (default: all)")
    options = parser.parse_args()
    build_all(options.out, options.programs or None)


if __name__ == "__main__":
    main()
