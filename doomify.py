#!/usr/bin/env python3
"""Rebuilds Nacht des Schreckens' World at War weapons and sounds from your own game.

World at War's assets can't be shared, so they aren't in this repository. This makes them from your
own copy of Call of Duty: World at War, into nacht-waw/: a pk3 folder that UZDoom loads after nacht.
Run it before playing for the first time, and again after nacht's weapons change:

  1. Start World at War and, in Zombies (solo), load Der Riese. Stay in the map.
  2. python3 doomify.py

It needs Blender (blender.org), which renders the weapons. It runs doomify-waw: built from the
workspace's own doomify-waw checkout when this one sits beside it (../doomify-waw, with
../hell-hound), so it is never older than the workspace; else the one nacht-install put in
doomify/, or doomify-waw on your PATH, or (with --source, or when there is neither) doomify-waw
built from its repository with git and Rust's cargo, which it offers to install when they are
missing and can all be installed at once. Released executables are on doomify-waw's
GitHub releases. Anything after the options goes to doomify-waw build (--help lists them: --force
renders everything again, --blender PATH picks Blender).

  python3 doomify.py [--source | --no-build] [--pack] [-- doomify-waw build options]

Before installing anything it says, under a red warning, exactly what will run, and asks.
--no-build never builds doomify-waw (nor installs what building needs): it uses the one in
doomify/ or on the PATH.
"""

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import textwrap
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
# The folder holding this project and its neighbours, whose checkouts come before any download
WORKSPACE = os.path.dirname(HERE)
FOLDER = os.path.join(HERE, "doomify")
OUTPUT = os.path.join(HERE, "nacht-waw")
REPOSITORIES = {
    "doomify-waw": "https://github.com/error-error-fruit-user/doomify-waw.git",
    "hell-hound": "https://github.com/error-error-fruit-user/hell-hound.git",
}
# The oldest Rust that builds them (their rust-version)
RUST = (1, 88)


def executable_name():
    return "doomify-waw.exe" if platform.system() == "Windows" else "doomify-waw"


def run(command, **options):
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True, **options)


def installed():
    """The doomify-waw nacht-install put in doomify/, or the one on the PATH; None without either."""
    beside = os.path.join(FOLDER, executable_name())
    return beside if os.path.isfile(beside) else shutil.which("doomify-waw")


def rust_ok():
    """Whether cargo is there and new enough for doomify-waw and hell-hound (RUST)."""
    cargo = shutil.which("cargo")
    if cargo is None:
        return False
    found = re.search(r"(\d+)\.(\d+)", subprocess.run([cargo, "--version"], capture_output=True,
                                                    text=True).stdout)
    return found is not None and (int(found[1]), int(found[2])) >= RUST


def install_plan(missing_git, missing_rust):
    """The commands that install everything missing in one go, or None when this system can't."""
    commands = []
    if missing_git:
        managers = {
            "apt-get": ["sudo", "apt-get", "install", "-y", "git"],
            "dnf": ["sudo", "dnf", "install", "-y", "git"],
            "pacman": ["sudo", "pacman", "-S", "--needed", "git"],
            "zypper": ["sudo", "zypper", "install", "-y", "git"],
            "brew": ["brew", "install", "git"],
        }
        manager = next((m for m in managers if shutil.which(m)), None)
        if platform.system() == "Windows" or manager is None:
            return None
        commands.append(managers[manager])
    if missing_rust:
        if shutil.which("rustup"):
            commands.append(["rustup", "update", "stable"])
        elif platform.system() == "Windows" or shutil.which("curl") is None:
            # rustup on Windows also needs Visual Studio's build tools: not one step
            return None
        else:
            # rustup.rs's own installer: distributions' cargo is often older than doomify-waw needs
            commands.append(["sh", "-c", "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs"
                                         " | sh -s -- -y"])
    return commands


def warning(lines):
    """`lines` under a red '--- Warning ---' (plain where the output isn't a terminal)."""
    if platform.system() == "Windows":
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


def explain(command):
    """What one of install_plan's commands does, in words."""
    if command[0] == "rustup":
        return "updates your Rust to the newest stable release"
    if command[0] == "sh":
        return ("downloads rustup.rs's installer and runs it, which installs Rust's stable toolchain "
                "into ~/.rustup and ~/.cargo and adds ~/.cargo/bin to your PATH in your shell's "
                "profile")
    manager = command[1] if command[0] == "sudo" else command[0]
    return (f"installs git with your system's package manager ({manager})"
            + (", as root, asking for your password" if command[0] == "sudo" else ""))


def get_tools(git=True):
    """git (unless not needed) and a new enough cargo, installed after asking when they can all be
    at once."""
    missing_git = git and shutil.which("git") is None
    missing_rust = not rust_ok()
    if not missing_git and not missing_rust:
        return
    needed = (("git", missing_git), (f"Rust {RUST[0]}.{RUST[1]} or newer", missing_rust))
    wanted = " and ".join(name for name, gone in needed if gone)
    plan = install_plan(missing_git, missing_rust)
    if plan is None or not sys.stdin.isatty():
        sys.exit(f"Building doomify-waw needs {wanted}: install them (git-scm.com, rustup.rs) and run"
                 " this again, or put doomify-waw from its GitHub releases in doomify/")
    warning([f"Building doomify-waw needs {wanted}. Saying yes will run:"]
            + [f"  - {' '.join(command)}: {explain(command)}" for command in plan]
            + ["", "To skip this: install them yourself, or pass --no-build to use only a "
                   "doomify-waw that is already in doomify/ or on your PATH."])
    if input("Install them now? [y/N] ").strip().lower() not in ("y", "yes"):
        sys.exit("Not installed: doomify-waw can't be built without them.")
    for command in plan:
        run(command)
    # rustup's installer puts cargo in ~/.cargo/bin, which this shell's PATH may not have yet
    os.environ["PATH"] += os.pathsep + os.path.join(os.path.expanduser("~"), ".cargo", "bin")
    if shutil.which("git") is None or not rust_ok():
        sys.exit(f"{wanted} still can't be found: open a new terminal and run this again.")


def workspace_project():
    """The workspace's doomify-waw checkout, when it and hell-hound (which it is built against, from
    beside it) are both there; None otherwise."""
    project = os.path.join(WORKSPACE, "doomify-waw")
    found = all(os.path.isfile(os.path.join(WORKSPACE, name, "Cargo.toml")) for name in REPOSITORIES)
    return project if found else None


def build(project):
    """doomify-waw built in the checkout `project`."""
    run(["cargo", "build", "--release", "--manifest-path", os.path.join(project, "Cargo.toml")])
    return os.path.join(project, "target", "release", executable_name())


def from_source():
    """doomify-waw built from its repository, cloned (or updated) into doomify/src with hell-hound,
    which it is built against, next to it."""
    get_tools()
    sources = os.path.join(FOLDER, "src")
    os.makedirs(sources, exist_ok=True)
    for name, url in REPOSITORIES.items():
        path = os.path.join(sources, name)
        if os.path.isdir(os.path.join(path, ".git")):
            run(["git", "-C", path, "pull", "--ff-only"])
        else:
            run(["git", "clone", "--depth", "1", url, path])
    return build(os.path.join(sources, "doomify-waw"))


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
                        help="build doomify-waw from its repository instead of using an installed "
                             "one (the workspace's checkout is always built first when there is one)")
    parser.add_argument("--no-build", action="store_true",
                        help="never build doomify-waw (or install what building needs): use the one "
                             "in doomify/ or on the PATH")
    parser.add_argument("--pack", action="store_true", help="also zip nacht-waw/ into nacht-waw.pk3")
    parser.add_argument("rest", nargs="*", help="options for doomify-waw build, after --")
    args = parser.parse_args()

    workspace = None if args.no_build else workspace_project()
    if args.no_build:
        executable = installed()
        if executable is None:
            sys.exit("--no-build: there is no doomify-waw in doomify/ or on the PATH")
    elif workspace is not None:
        print(f"Building doomify-waw from the workspace: {workspace}")
        get_tools(git=False)
        executable = build(workspace)
    else:
        executable = None if args.source else installed()
    if executable is None:
        if not args.source:
            print("No doomify-waw in doomify/ or on the PATH: building it from source.")
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
