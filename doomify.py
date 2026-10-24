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

Before installing anything it says, under a red warning, exactly what will run, and asks.
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
import textwrap
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
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


# The journal: everything this does, with the time since it began (what it plans and is told,
# every command and all it prints, every file it puts somewhere), added to JOURNAL on each run.
JOURNAL = os.path.join(ARTIFACTS, "doomify.log")
BEGAN = time.monotonic()
# Blender's line for every frame it renders, which would bury the rest
CHATTER = ("Fra:", "Saved:", "Time:", "Read blend")


def note(line):
    """Writes `line` down in the journal."""
    os.makedirs(os.path.dirname(JOURNAL), exist_ok=True)
    with open(JOURNAL, "a", encoding="utf-8") as journal:
        for part in line.splitlines() or [""]:
            journal.write(f"[{time.monotonic() - BEGAN:8.3f}s] {part}\n")


# The voice it speaks in, from installation-groans: the workspace's checkout beside nacht, else the
# groans/ folder nacht-install put beside this, else GitHub. Toiling Through Hell unless told
# --computer-speak; without one (or Python older than 3.11, which can't read TOML), plain lines.
GROANS = "https://raw.githubusercontent.com/error-error-fruit-user/installation-groans/main/"
VOICE = {}


def speak_in(name):
    """Speaks in the installation-groans voice `name` (a file name) from now on, if it is found."""
    global VOICE
    try:
        import tomllib
    except ImportError:
        return
    text = None
    for folder in (os.path.join(WORKSPACE, "installation-groans"), os.path.join(HERE, "groans")):
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as source:
                text = source.read()
            break
    if text is None:
        try:
            import urllib.request
            with urllib.request.urlopen(GROANS + name, timeout=5) as answer:
                text = answer.read().decode()
        except Exception:
            return
    try:
        VOICE = tomllib.loads(text)
    except Exception:
        VOICE = {}


def tell(event, plain, **fills):
    """Says `event` as one of the voice's phrases for it, picked at random and filled from `fills`,
    or `plain` without one; the journal keeps the plain line either way. Now and then the voice
    interjects (its [interjection])."""
    import random
    phrases = VOICE.get("phrases", {}).get(event) or []
    if not phrases:
        print(plain, flush=True)
        note(plain)
        return
    said = random.choice(phrases)
    for name, value in fills.items():
        said = said.replace("{" + name + "}", str(value))
    said = said[:1].upper() + said[1:]
    print(said, flush=True)
    note(f"{said}  ({plain})")
    interjection = VOICE.get("interjection", {})
    if interjection.get("phrases") and random.random() < float(interjection.get("chance", 0)):
        colors = {"yellow": 33, "green": 32, "blue": 34, "magenta": 35, "cyan": 36, "white": 37}
        code = colors.get(interjection.get("color", "red"), 31)
        shout = random.choice(interjection["phrases"])
        tty = sys.stdout.isatty() and "NO_COLOR" not in os.environ
        print(f"\033[1;{code}m{shout}\033[0m" if tty else shout, flush=True)
        note(shout)


def run(command, cwd=HERE):
    """Runs `command`, its output shown as it comes (prompts included) and written down, with how it
    ended. Raises CalledProcessError if it failed."""
    shown = " ".join(str(part) for part in command)
    tell("run", f"+ {shown}", command=shown)
    note(f"  (in {cwd})")
    process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    pending, quiet = b"", 0
    while True:
        chunk = process.stdout.read1(4096)
        if not chunk:
            break
        sys.stdout.buffer.write(chunk)
        sys.stdout.buffer.flush()
        *lines, pending = (pending + chunk).split(b"\n")
        for line in lines:
            text = line.decode(errors="replace").rstrip("\r")
            if text.startswith(CHATTER):
                quiet += 1
            else:
                note("  | " + text)
    if pending:
        note("  | " + pending.decode(errors="replace"))
    code = process.wait()
    if quiet:
        note(f"  ({quiet} lines of Blender's frame by frame progress left out)")
    note(f"  ended with code {code}")
    if code:
        raise subprocess.CalledProcessError(code, command)


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


def warning(lines):
    """`lines` under a red '--- Warning ---' (plain where the output isn't a terminal)."""
    if platform.system() == "Windows":
        os.system("")  # lets the Windows console show colors
    color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
    print("\033[31m--- Warning ---\033[0m" if color else "--- Warning ---")
    note("--- Warning ---")
    for line in lines:
        note(line)
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
                 f" this again, or put doomify-waw from its GitHub releases in {ARTIFACTS}")
    warning([f"Building doomify-waw needs {wanted}. Saying yes will run:"]
            + [f"  - {' '.join(command)}: {explain(command)}" for command in plan]
            + ["", "To skip this: install them yourself, or pass --no-build to use only a "
                   f"doomify-waw that is already in {ARTIFACTS} or on your PATH."])
    answer = input("Install them now? [y/N] ").strip()
    note(f"asked to install {wanted}, the answer was {answer!r}")
    if answer.lower() not in ("y", "yes"):
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
    """doomify-waw built from its repository, cloned (or updated) into the artifacts' doomify-src/
    with hell-hound, which it is built against, next to it."""
    get_tools()
    sources = os.path.join(ARTIFACTS, "doomify-src")
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
    note(f"packed {OUTPUT} into {target}")
    print("Packed", target)


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
        note(f"no Nacht des Schreckens profile: setup-waw.toml there {os.path.isfile(setup)}, tdl {tdl}")
        return
    try:
        run([tdl, "setup", setup])
    except subprocess.CalledProcessError as error:
        print(f"note: tdl setup setup-waw.toml failed ({error.returncode})", file=sys.stderr)
        return
    color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
    loud = "\033[1;31m" if color else ""
    plain = "\033[0m" if color else ""
    loadout = os.path.join(HERE, "published", "artifacts", "loadout")
    print()
    print(f"{loud}--- Nacht des Schreckens is ready to play ---{plain}")
    print("Der Riese's weapons, rebuilt from your own World at War, in nacht's loadout:")
    print(f"  {tdl} --loadout {loadout} launch \"Nacht des Schreckens\"")
    print()
    note("set up the Nacht des Schreckens profile")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--source", action="store_true",
                        help="build doomify-waw from its repository instead of using an installed "
                             "one (the workspace's checkout is always built first when there is one)")
    parser.add_argument("--no-build", action="store_true",
                        help="never build doomify-waw (or install what building needs): use the one "
                             "in the artifacts or on the PATH")
    parser.add_argument("--pack", action="store_true", help="also zip nacht-waw/ into nacht-waw.pk3")
    parser.add_argument("--computer-speak", action="store_true",
                        help="say what it does plainly and formally, rather than as a descent through hell")
    parser.add_argument("--no-setup", action="store_true",
                        help="don't set up the Nacht des Schreckens profile (setup-waw.toml)")
    parser.add_argument("rest", nargs="*", help="options for doomify-waw build, after --")
    args = parser.parse_args()
    note(f"=== doomify.py {' '.join(sys.argv[1:])} ===")
    speak_in("computer-speak.toml" if args.computer_speak else "toiling-through-hell.toml")
    tell("begin", "Rebuilding Nacht des Schreckens' World at War weapons", what="Der Riese's weapons",
         place=OUTPUT)

    workspace = None if args.no_build else workspace_project()
    note(f"workspace doomify-waw: {workspace}; installed one: {installed()}")
    if args.no_build:
        executable = installed()
        if executable is None:
            sys.exit(f"--no-build: there is no doomify-waw in {ARTIFACTS} or on the PATH")
    elif workspace is not None:
        print(f"Building doomify-waw from the workspace: {workspace}")
        get_tools(git=False)
        executable = build(workspace)
    else:
        executable = None if args.source else installed()
    if executable is None:
        if not args.source:
            print(f"No doomify-waw in {ARTIFACTS} or on the PATH: building it from source.")
        executable = from_source()
    tell("found", f"Using doomify-waw: {executable}", what="doomify-waw", place=executable)
    run([executable, "build", FOLDER, *args.rest])
    if args.pack:
        pack()
    if not args.no_setup:
        set_up_schreckens()
    print("\nDone. Load nacht-waw after Horde Hammer and nacht, for example:")
    print("  uzdoom -iwad freedoom2.wad -file horde-hammer.pk3 nacht nacht-waw")


if __name__ == "__main__":
    try:
        main()
        tell("done", "Done.", what="Der Riese's weapons")
    except subprocess.CalledProcessError as error:
        tell("problem", f"doomify failed: {error}", problem=error)
        tell("journal", f"What it did is in {JOURNAL}", place=JOURNAL)
        sys.exit(1)
    tell("journal", f"What it did is in {JOURNAL}", place=JOURNAL)
