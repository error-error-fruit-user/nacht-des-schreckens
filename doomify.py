#!/usr/bin/env python3
"""Rebuilds Nacht des Schreckens' World at War weapons and sounds from your own game.

World at War's assets can't be shared, so they aren't in this repository. This makes them from your
own copy of Call of Duty: World at War, into nacht-waw/: a pk3 folder that UZDoom loads after nacht.
Run it before playing for the first time, and again after nacht's weapons change:

  1. Start World at War and, in Zombies (solo), load Der Riese. Stay in the map.
  2. python3 doomify.py

It needs Blender (blender.org), which renders the weapons. It runs doomify-waw: built from the
workspace's own doomify-waw checkout when this one sits beside it (../doomify-waw, with
../hell-hound), so it is never older than the workspace; else the one in its artifacts (in this
checkout published/artifacts/, where nacht-install's copy has it beside this), or doomify-waw on
your PATH, or (with --source, or when there is neither) doomify-waw
built from its repository with git and Rust's cargo, which it offers to install when they are
missing and can all be installed at once. Released executables are on doomify-waw's
GitHub releases. Anything after the options goes to doomify-waw build (--help lists them: --force
renders everything again, --blender PATH picks Blender).

  python3 doomify.py [--source | --no-build] [--pack] [--computer-speak] [-- doomify-waw build options]

Before installing anything it says, under a red warning, exactly what will run, and asks once:
"Are you sure? [y/n]" (--accept installs without asking; run by nacht-install, whose own question
covers it, it never asks). It speaks in a voice from installation-groans (its submodule here, or
beside nacht-install's copy), Toiling Through Hell unless --computer-speak.
--no-build never builds doomify-waw (nor installs what building needs): it uses the one in its
artifacts or on the PATH. Everything it makes but the weapons (doomify-waw built from source, its
sources, its journal) goes in its artifacts.
"""

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
# --accept: what building needs is installed without asking (nacht-install's one question covers it)
ACCEPT = False
# The folder holding this project and its neighbours, whose checkouts come before any download
WORKSPACE = os.path.dirname(HERE)
FOLDER = os.path.join(HERE, "doomify")
# Everything this makes but the weapons (doomify-waw built from source, its sources, the journal):
# in a checkout, the project's published/artifacts/; in nacht-install's copy, which is in the
# install's artifacts already, beside this
ARTIFACTS = (os.path.join(HERE, "published", "artifacts")
             if os.path.isfile(os.path.join(HERE, "publish.py")) else HERE)
OUTPUT = os.path.join(HERE, "nacht-waw")
REPOSITORIES = {
    "doomify-waw": "https://github.com/error-error-fruit-user/doomify-waw.git",
    "hell-hound": "https://github.com/error-error-fruit-user/hell-hound.git",
}
# The oldest Rust that builds them (their rust-version)
RUST = (1, 88)


GROANS_GITHUB = "https://raw.githubusercontent.com/error-error-fruit-user/installation-groans/main/"


def load_groans():
    """installation-groans' groans.py, which this speaks through: this checkout's installation-groans
    submodule, the workspace's checkout beside it, the groans/ folder nacht-install puts beside this
    copy, or one fetched from its GitHub into the artifacts."""
    places = [os.path.join(HERE, "installation-groans"), os.path.join(WORKSPACE, "installation-groans"),
              os.path.join(HERE, "groans"), os.path.join(ARTIFACTS, "groans")]
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
            sys.exit(f"installation-groans couldn't be found or fetched ({error}): run "
                     "git submodule update --init beside this script.")
    if folder not in sys.path:
        sys.path.insert(0, folder)
    import groans
    return groans


groans = load_groans()
JOURNAL = os.path.join(ARTIFACTS, "doomify.log")


def executable_name():
    return "doomify-waw.exe" if platform.system() == "Windows" else "doomify-waw"



def installed():
    """The doomify-waw in the artifacts (where nacht-install puts one), or the one on the PATH; None
    without either."""
    beside = os.path.join(ARTIFACTS, executable_name())
    return beside if os.path.isfile(beside) else shutil.which("doomify-waw")


def rust_on_path():
    """Puts rustup's folder ($CARGO_HOME/bin, else ~/.cargo/bin) on the PATH when cargo isn't on
    it, as a shell that never ran rustup's profile line leaves it; everything this runs inherits it."""
    if shutil.which("cargo"):
        return
    home = os.environ.get("CARGO_HOME") or os.path.join(os.path.expanduser("~"), ".cargo")
    folder = os.path.join(home, "bin")
    if any(os.path.isfile(os.path.join(folder, name)) for name in ("cargo", "cargo.exe")):
        os.environ["PATH"] = folder + os.pathsep + os.environ.get("PATH", "")


def rust_ok():
    """Whether cargo is there and new enough for doomify-waw and hell-hound (RUST)."""
    rust_on_path()
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
    if plan is None:
        sys.exit(f"Building doomify-waw needs {wanted}: install them (git-scm.com, rustup.rs) and run"
                 f" this again, or put doomify-waw from its GitHub releases in {ARTIFACTS}")
    groans.warning([f"Building doomify-waw needs {wanted}. Saying yes will run:"]
                   + [f"  - {' '.join(command)}: {explain(command)}" for command in plan]
                   + ["", "To skip this: install them yourself, or pass --no-build to use only a "
                          f"doomify-waw that is already in {ARTIFACTS} or on your PATH."])
    if groans.confirm(ACCEPT) is None:
        groans.declined()
    for command in plan:
        groans.run(command)
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
    groans.run(["cargo", "build", "--release", "--manifest-path", os.path.join(project, "Cargo.toml")])
    return os.path.join(project, "target", "release", executable_name())


def from_source():
    """doomify-waw built from its repository, cloned (or updated) into the artifacts' doomify-src/
    with hell-hound, which it is built against, next to it."""
    get_tools()
    sources = os.path.join(ARTIFACTS, "doomify-src")
    os.makedirs(sources, exist_ok=True)
    for name, url in REPOSITORIES.items():
        path = os.path.join(sources, name)
        if os.path.isdir(os.path.join(path, ".git")):
            groans.run(["git", "-C", path, "pull", "--ff-only"])
        else:
            groans.run(["git", "clone", "--depth", "1", url, path])
    return build(os.path.join(sources, "doomify-waw"))


def pack(target=None):
    """nacht-waw/ zipped into `target` (nacht-waw.pk3 beside it by default), for launchers that take
    only pk3s, saying how far it has got every thousand files."""
    target = target or OUTPUT + ".pk3"
    files = [os.path.join(root, name) for root, _, names in sorted(os.walk(OUTPUT))
             for name in sorted(names)]
    groans.other(f"Packing {OUTPUT} into {target}")
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    with zipfile.ZipFile(target + ".part", "w", zipfile.ZIP_DEFLATED) as archive:
        for number, path in enumerate(files, 1):
            archive.write(path, os.path.relpath(path, OUTPUT).replace(os.sep, "/"))
            if number % 1000 == 0:
                groans.other(f"Packed {number}/{len(files)} files")
    os.replace(target + ".part", target)
    groans.built(target, len(files))


def find_tdl():
    """tdl, the workspace's first (../tdl/published/releases/), else the one beside nacht-install
    put it (the install's folder), else the one on the PATH."""
    names = ["tdl.exe"] if platform.system() == "Windows" else ["tdl", "tdl.AppImage"]
    for folder in (os.path.join(WORKSPACE, "tdl", "published", "releases"), WORKSPACE):
        for name in names:
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                return os.path.normpath(path)
    return shutil.which("tdl")


def set_up_schreckens():
    """Sets up the Nacht des Schreckens profile in nacht's loadout with `tdl setup setup-waw.toml`,
    then says, in a big way, that it can be played."""
    setup = os.path.join(HERE, "setup-waw.toml")
    tdl = find_tdl()
    if not os.path.isfile(setup) or tdl is None:
        groans.note(f"no Nacht des Schreckens profile: setup-waw.toml there {os.path.isfile(setup)}, "
                    f"tdl {tdl}")
        return
    groans.section("setup")
    try:
        groans.run([tdl, "setup", setup])
    except subprocess.CalledProcessError as error:
        groans.other(f"note: tdl setup setup-waw.toml failed ({error.returncode})", sys.stderr)
        return
    loadout = os.path.join(HERE, "published", "artifacts", "loadout")
    command = f'{tdl} --loadout {loadout} launch "Nacht des Schreckens"'
    groans.section("play")
    groans.say("ready", f"Nacht des Schreckens is ready to play: {command}",
               what="Nacht des Schreckens", command=command)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--source", action="store_true",
                        help="build doomify-waw from its repository instead of using an installed "
                             "one (the workspace's checkout is always built first when there is one)")
    parser.add_argument("--no-build", action="store_true",
                        help="never build doomify-waw (or install what building needs): use the one "
                             "in the artifacts or on the PATH")
    parser.add_argument("--pack", action="store_true", help="also zip nacht-waw/ into nacht-waw.pk3")
    parser.add_argument("--pack-to", metavar="PK3",
                        help="also zip nacht-waw/ into this pk3 (nacht-install's wad pool)")
    parser.add_argument("--computer-speak", action="store_true",
                        help="say what it does plainly and formally, rather than as a descent through hell")
    parser.add_argument("--no-setup", action="store_true",
                        help="don't set up the Nacht des Schreckens profile (setup-waw.toml)")
    parser.add_argument("rest", nargs="*", help="options for doomify-waw build, after --")
    parser.add_argument("--rerender", action="store_true",
                        help="pull and render every weapon again, though the cache has them "
                             "(doomify-waw's --force)")
    parser.add_argument("--accept", action="store_true",
                        help="install what building doomify-waw needs without asking")
    args = parser.parse_args()
    global ACCEPT
    ACCEPT = args.accept
    groans.start(JOURNAL, args.computer_speak)
    groans.say("begin", "Rebuilding Nacht des Schreckens' World at War weapons",
               what="Der Riese's weapons", place=OUTPUT)
    groans.section("weapons")

    workspace = None if args.no_build else workspace_project()
    groans.note(f"workspace doomify-waw: {workspace}; installed one: {installed()}")
    if args.no_build:
        executable = installed()
        if executable is None:
            sys.exit(f"--no-build: there is no doomify-waw in {ARTIFACTS} or on the PATH")
    elif workspace is not None:
        groans.say("found", f"Building doomify-waw from the workspace: {workspace}",
                   what="the workspace's doomify-waw", place=workspace)
        get_tools(git=False)
        executable = build(workspace)
    else:
        executable = None if args.source else installed()
    if executable is None:
        if not args.source:
            groans.other(f"note: no doomify-waw in {ARTIFACTS} or on the PATH: building it from source")
        executable = from_source()
    groans.note(f"using doomify-waw: {executable}")
    groans.run([executable, "build", FOLDER, *(["--force"] if args.rerender else []), *args.rest])
    if args.pack or args.pack_to:
        pack(args.pack_to)
    if not args.no_setup:
        set_up_schreckens()
    groans.other("Load nacht-waw after Horde Hammer and nacht, for example: "
                 "uzdoom -iwad freedoom2.wad -file horde-hammer.pk3 nacht nacht-waw")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        groans.finish("Der Riese's weapons", ok=False,
                      error=f"{' '.join(map(str, error.cmd))} ended with code {error.returncode}")
        sys.exit(1)
    except SystemExit as stop:
        if isinstance(stop.code, str):
            groans.say("problem", stop.code, problem=stop.code)
            sys.exit(1)
        raise
    groans.finish("Der Riese's weapons")
