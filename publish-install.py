#!/usr/bin/env python3
"""Publish Nacht des Schreckens, then install it with the nacht-install just published.

usage: python3 publish-install.py [--accept] [--no-build | --source] [--no-shortcuts]
                                  [nacht-install options]

First it says, under a red warning, exactly what it will do, and asks before doing any of it
(--accept goes ahead without asking). Then it builds the release with publish.py (the pk3s, and
nacht-install for Windows and as an AppImage, into published/releases/), or with --source the pk3s
and nacht-install for this machine only (cargo build --release), or with --no-build nothing at
all; and runs the nacht-install in published/releases/, which installs the pk3s, tdl and Blender
where it is asked to (--mode) and offers to run doomify.py. --mode, --dir, --yes, --no-tdl,
--no-uzdoom, --no-freedoom, --no-blender, --no-doomify, --no-song, --waw and --blender go to nacht-install (see its
--help). Right after the warning it asks whether to make a Nacht des Schreckens shortcut (the app
menu and the desktop, or the Start menu and the desktop on Windows) with the system's lock icon,
opening the install's tdl on its loadout; --no-shortcuts makes none without asking.

Dependency-free Python 3.8+.
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import textwrap
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RELEASES = os.path.join(HERE, "published", "releases")
WINDOWS = platform.system() == "Windows"
WHAT = "Nacht des Schreckens"
# The installer it runs, which takes --computer-speak too
INSTALLER = 'nacht-install'
EXE = ".exe" if WINDOWS else ""
NAME = "nacht-des-schreckens"


# The journal: everything this does, with the time since it began (what it plans and is told,
# every command and all it prints, every file it puts somewhere), added to JOURNAL on each run.
JOURNAL = os.path.join(HERE, "published", "artifacts", "publish-install.log")
BEGAN = time.monotonic()
# Blender's line for every frame it renders, which would bury the rest
CHATTER = ("Fra:", "Saved:", "Time:", "Read blend")


def note(line):
    """Writes `line` down in the journal."""
    os.makedirs(os.path.dirname(JOURNAL), exist_ok=True)
    with open(JOURNAL, "a", encoding="utf-8") as journal:
        for part in line.splitlines() or [""]:
            journal.write(f"[{time.monotonic() - BEGAN:8.3f}s] {part}\n")


# The voice it speaks in, from installation-groans: the workspace's checkout beside this project,
# else GitHub. Toiling Through Hell unless told --computer-speak; without one (or Python older than
# 3.11, which can't read TOML), plain lines.
GROANS = "https://raw.githubusercontent.com/error-error-fruit-user/installation-groans/main/"
VOICE = {}


def speak_in(name):
    """Speaks in the installation-groans voice `name` (a file name) from now on, if it is found."""
    global VOICE
    try:
        import tomllib
    except ImportError:
        return
    path = os.path.join(os.path.dirname(HERE), "installation-groans", name)
    try:
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as source:
                text = source.read()
        else:
            import urllib.request
            with urllib.request.urlopen(GROANS + name, timeout=5) as answer:
                text = answer.read().decode()
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


def not_mine(folders):
    """The first file in `folders` (and the folders themselves) owned by someone else, as a run
    with sudo leaves them; None when every one is this user's."""
    if WINDOWS:
        return None
    for folder in folders:
        for root, dirs, files in os.walk(folder):
            for path in [root] + [os.path.join(root, name) for name in dirs + files]:
                try:
                    if os.lstat(path).st_uid != os.getuid():
                        return path
                except OSError:
                    pass
    return None


def check_owner(folders):
    """Stops, saying how to take them back, when anything in `folders` isn't this user's."""
    if WINDOWS or os.getuid() == 0:
        return
    stranger = not_mine(folders)
    if stranger is not None:
        import getpass
        fix = "sudo chown -R " + getpass.getuser() + " " + " ".join(folders)
        tell("problem", f"{stranger} isn't yours (a run with sudo left it)", problem=f"{stranger} isn't yours")
        sys.exit(f"Something in published/ belongs to another user, root most likely (a run with sudo "
                 f"leaves it): nothing can replace it. Take it back with:\n  {fix}")


def run(command, cwd=HERE):
    """Runs `command`, its output shown as it comes (prompts included) and written down, with how it
    ended. Raises CalledProcessError if it failed."""
    shown = " ".join(str(part) for part in command)
    tell("run", f"+ {shown}", command=shown)
    note(f"+ {shown}  (in {cwd})")
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



def warning(lines):
    """`lines` under a red '--- Warning ---' (plain where the output isn't a terminal)."""
    if WINDOWS:
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


def agreed(accept):
    if accept:
        note("--accept: going ahead without asking")
        return True
    if not sys.stdin.isatty():
        note("no one to ask, and no --accept: nothing was done")
        sys.exit("There is no one to ask, so nothing was done: pass --accept to go ahead.")
    answer = input("Go ahead? [y/N] ").strip()
    note(f"asked to go ahead, the answer was {answer!r}")
    return answer.lower() in ("y", "yes")



# The system's lock icon for every shortcut: the icon theme's on Linux, shell32.dll's padlock on Windows
LOCK_ICON = "system-lock-screen"
WINDOWS_LOCK_ICON = r"%SystemRoot%\System32\shell32.dll,47"


def shortcut_places():
    """Where shortcuts go on Linux: the app menu, and the desktop if there is one."""
    home = os.path.expanduser("~")
    data = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    places = [os.path.join(data, "applications")]
    try:
        desktop = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True,
                                 text=True).stdout.strip()
    except OSError:
        desktop = ""
    desktop = desktop or os.path.join(home, "Desktop")
    if os.path.isdir(desktop) and os.path.abspath(desktop) != os.path.abspath(home):
        places.append(desktop)
    return places


def wants_shortcuts(args, what):
    """Asks, right after the warning, whether to make shortcuts for `what` (--no-shortcuts: no,
    without asking)."""
    if args.no_shortcuts:
        note("--no-shortcuts: no shortcuts, and no question about them")
        return False
    if not sys.stdin.isatty():
        note("no one to ask about shortcuts: none are made")
        return False
    if WINDOWS:
        where = "your Start menu and desktop"
    else:
        where = " and ".join(place.replace(os.path.expanduser("~"), "~", 1)
                             for place in shortcut_places())
    answer = input(f"Make shortcuts for {what} in {where}, with the system's lock icon? "
                   "[y/N] ").strip()
    note(f"asked about shortcuts for {what}, the answer was {answer!r}")
    return answer.lower() in ("y", "yes")


def exec_quoted(arg):
    """`arg` as a desktop entry's Exec line wants it."""
    if arg and not any(c in arg for c in " \t\n\"'\\><~|&;$*?#()`"):
        return arg
    return '"' + "".join("\\" + c if c in '"`$\\' else c for c in arg) + '"'


def make_shortcut(title, file_id, command, comment):
    """A shortcut called `title` that runs `command` in a terminal, with the lock icon: a desktop
    entry `file_id`.desktop in each of `shortcut_places()` on Linux, a .lnk in the Start menu and on
    the desktop on Windows."""
    if WINDOWS:
        def ps(text):
            return "'" + text.replace("'", "''") + "'"
        script = (
            "$shell = New-Object -ComObject WScript.Shell\n"
            "foreach ($folder in @([Environment]::GetFolderPath('Programs'), "
            "[Environment]::GetFolderPath('Desktop'))) {\n"
            f"  $link = $shell.CreateShortcut((Join-Path $folder {ps(title + '.lnk')}))\n"
            f"  $link.TargetPath = {ps(command[0])}\n"
            f"  $link.Arguments = {ps(subprocess.list2cmdline(command[1:]))}\n"
            f"  $link.WorkingDirectory = {ps(os.path.dirname(os.path.abspath(command[0])))}\n"
            f"  $link.Description = {ps(comment)}\n"
            f"  $link.IconLocation = {ps(WINDOWS_LOCK_ICON)}\n"
            "  $link.Save()\n"
            "  Write-Output (Join-Path $folder " + ps(title + ".lnk") + ")\n"
            "}\n")
        run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script])
        return
    exec_line = " ".join(exec_quoted(arg) for arg in command)
    entry = ("[Desktop Entry]\nType=Application\n"
             f"Name={title}\nComment={comment}\n"
             f"Exec={exec_line.replace(chr(92), chr(92) * 2).replace('%', '%%')}\n"
             f"Icon={LOCK_ICON}\nTerminal=true\nCategories=Game;\n")
    for place in shortcut_places():
        os.makedirs(place, exist_ok=True)
        path = os.path.join(place, file_id + ".desktop")
        with open(path, "w", encoding="utf-8") as file:
            file.write(entry)
        os.chmod(path, 0o755)
        # a desktop launches only the shortcuts it is told to trust
        if not path.startswith(shortcut_places()[0]) and shutil.which("gio"):
            subprocess.run(["gio", "set", path, "metadata::trusted", "true"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        note(f"made the shortcut {path}: {exec_line}")
        print("Shortcut:", path)


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
    if not args.no_build:
        lines.append("  - rebuild the workspace's releases of tdl and doomify-waw (their publish.py) if "
                     "their sources are newer than them, for nacht-install to take")
    lines.append("  - run nacht-install from published/releases/, which:")
    if WINDOWS:
        user, system = (f"%LOCALAPPDATA%\\Programs\\{NAME}", f"%ProgramFiles%\\{NAME}")
    else:
        user, system = (f"~/.local/opt/{NAME}", f"/opt/{NAME}")
    where = {
        "in-place": "    - installs in published/releases/ itself (or --dir)",
        "user": f"    - installs in {user} (or --dir)",
        "system": f"    - installs in {system} (or --dir), which needs "
                  f"{'administrator' if WINDOWS else 'root: the installer runs with sudo'}",
    }
    lines.append(where.get(args.mode) or
                 f"    - asks where to install: in place, for you ({user}) or for everyone "
                 f"({system}, {'needs administrator' if WINDOWS else 'the installer run with sudo'}); "
                 "asked before the build")
    if args.dir:
        art = "artifacts/ in --dir"
    elif args.mode == "in-place":
        art = "published/artifacts/"
    else:
        art = "artifacts/ there (published/artifacts/ if it installs in place here)"
    lines.append("    - puts horde-hammer.pk3 and nacht.pk3, the payload, in its wads/, and "
                 f"everything else, its artifacts, in {art}: tdl, Blender, the song, the loadout, "
                 "its log, and doomify.py with its "
                 f"settings in {NAME}/, with a doomify-waw: the one beside it, the workspace's "
                 "(../doomify-waw/published/releases/) or else downloaded from doomify-waw's latest "
                 "GitHub release")
    if not args.no_tdl:
        tdl = ("    - runs tdl-install (beside it, the workspace's ../tdl/published/releases/, or else "
               "downloaded from tdl's latest GitHub release), which puts tdl in the artifacts")
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
        lines.append("    - downloads Blender 4.2.9 LTS into blender/ in the artifacts, checked against its "
                     "published hash, if no Blender 4.0 or newer is installed"
                     + (" (--yes: without asking)" if args.yes else ", after asking"))
    if not args.no_song:
        lines.append("    - pulls Beauty of Annihilation out of your World at War"
                     + (f" (at {args.waw})" if args.waw else " (found in your Steam libraries)")
                     + " into songs/ in the artifacts and makes it tdl's song, for every loadout. It is heavy "
                     "metal: tdl's splash will open on down-tuned riffs and screaming, so mind your "
                     "speakers (--no-song keeps the music you have)")
    if not args.no_doomify:
        lines.append("    - if World at War is running with Der Riese loaded, runs doomify.py"
                     + (" (--yes: without asking)" if args.yes else ", after asking")
                     + ", which rebuilds the weapons from your game into nacht-waw.pk3 (about an "
                     "hour the first time)")
    lines.append("")
    lines.append("To change that: --no-build installs what is published already, --source builds only "
                 "for this machine, --no-tdl, --no-uzdoom, --no-freedoom, --no-blender and "
                 "--no-doomify and --no-song leave those out, --waw DIR says where World at War is, --blender PATH uses your Blender, --yes answers "
                 "nacht-install's questions, --mode and --dir say where, and --no-shortcuts doesn't "
                 "ask about shortcuts.")
    return lines


# The workspace's tools nacht-install takes from their releases, the checkouts each is built from,
# and the release files it needs
TOOLS = {
    "tdl": (["tdl"], ["tdl", "tdl-install"]),
    "doomify-waw": (["doomify-waw", "hell-hound"], ["doomify-waw"]),
}


def newest_source(checkout):
    """When the newest file the checkout tracks (by git) was changed; 0 if it can't tell."""
    listed = subprocess.run(["git", "-C", checkout, "ls-files", "-z"], capture_output=True)
    if listed.returncode != 0:
        return 0
    newest = 0
    for name in listed.stdout.decode(errors="replace").split("\0"):
        try:
            newest = max(newest, os.path.getmtime(os.path.join(checkout, name)))
        except OSError:
            pass
    return newest


def refresh_tools():
    """Rebuilds the workspace's releases of tdl and doomify-waw (their publish.py) when their
    sources are newer than them, so nacht-install never takes an old one from the workspace."""
    workspace = os.path.dirname(HERE)
    suffix = ".exe" if WINDOWS else ".AppImage"
    for project, (checkouts, programs) in TOOLS.items():
        folder = os.path.join(workspace, project)
        if not os.path.isfile(os.path.join(folder, "publish.py")):
            continue
        releases = [os.path.join(folder, "published", "releases", name + suffix) for name in programs]
        built = min((os.path.getmtime(path) for path in releases if os.path.isfile(path)), default=0)
        if len(releases) == sum(os.path.isfile(path) for path in releases) and built >= max(
                newest_source(os.path.join(workspace, checkout)) for checkout in checkouts):
            note(f"{project}'s release is newer than its sources")
            continue
        check_owner([path for path in (os.path.join(folder, "published"),) if os.path.isdir(path)])
        run([sys.executable, "publish.py"], cwd=folder)


def build(args):
    if args.no_build:
        return
    refresh_tools()
    if args.source:
        run([sys.executable, "publish.py", "--no-appimages"])
        run(["cargo", "build", "--release"], cwd=os.path.join(HERE, "installer"))
        shutil.copy2(os.path.join(HERE, "installer", "target", "release", "nacht-install" + EXE),
                     os.path.join(RELEASES, "nacht-install" + EXE))
        note(f"copied the release build into {RELEASES}")
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


def artifacts_of(folder):
    """The artifacts of an install in `folder`: published/artifacts/ for one in place here, else
    artifacts/ in it."""
    if os.path.abspath(folder) == os.path.abspath(RELEASES):
        return os.path.join(HERE, "published", "artifacts")
    return os.path.join(folder, "artifacts")


def install_dir(args):
    """Where nacht-install just installed: --dir, or where --mode puts it, or (when it asked) the
    newest of those places with a loadout in its artifacts."""
    if args.dir:
        return args.dir
    if WINDOWS:
        user = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", NAME)
        system = os.path.join(os.environ.get("ProgramFiles", ""), NAME)
    else:
        user = os.path.join(os.path.expanduser("~"), ".local", "opt", NAME)
        system = os.path.join("/opt", NAME)
    modes = {"in-place": RELEASES, "user": user, "system": system}
    if args.mode:
        return modes[args.mode]
    def loadout(folder):
        return os.path.join(artifacts_of(folder), "loadout")

    found = [folder for folder in modes.values() if os.path.isdir(loadout(folder))]
    return max(found, key=lambda folder: os.path.getmtime(loadout(folder))) if found else None


def shortcut(args):
    """The Nacht des Schreckens shortcut: the install's tdl (or the one on the PATH) on its loadout,
    as nacht-install opens it at the end."""
    folder = install_dir(args)
    if folder is None or not os.path.isdir(os.path.join(artifacts_of(folder), "loadout")):
        print("Made no shortcut: nacht-install's folder, with its loadout, isn't where this can "
              "find it.")
        return
    folder = os.path.abspath(folder)
    art = os.path.abspath(artifacts_of(folder))
    names = ["tdl.exe"] if WINDOWS else ["tdl", "tdl.AppImage"]
    tdl = next((os.path.join(art, name) for name in names
                if os.path.isfile(os.path.join(art, name))), None) or shutil.which("tdl")
    if tdl is None:
        print("Made no shortcut: there is no tdl in nacht's artifacts or on your PATH.")
        return
    make_shortcut("Nacht des Schreckens", NAME,
                  [tdl, "--session", "--loadout", os.path.join(art, "loadout"),
                   "--wads", os.path.join(folder, "wads")],
                  "World at War's Nacht der Untoten on Doom 2, in tdl")


def rust_on_path():
    """Puts rustup's folder ($CARGO_HOME/bin, else ~/.cargo/bin) on the PATH when cargo isn't on
    it, as a shell that never ran rustup's profile line leaves it; everything this runs inherits it."""
    if shutil.which("cargo"):
        return
    home = os.environ.get("CARGO_HOME") or os.path.join(os.path.expanduser("~"), ".cargo")
    folder = os.path.join(home, "bin")
    if any(os.path.isfile(os.path.join(folder, name)) for name in ("cargo", "cargo.exe")):
        os.environ["PATH"] = folder + os.pathsep + os.environ.get("PATH", "")


def as_root():
    return not WINDOWS and os.geteuid() == 0


def refuse_root_build(args):
    """Building as root (sudo) leaves files in published/ that only root can change: refused."""
    if as_root() and not args.no_build:
        note("run as root: refused to build")
        sys.exit("Don't run this with sudo: building as root leaves files in published/ that only "
                 "root can change. Run it as yourself; to install for everyone, it runs only the "
                 "installer with sudo.")


def ask_mode(args):
    """Where to install, asked here when --mode doesn't say, so an install for everyone can run the
    installer with sudo instead of failing for want of root."""
    if args.mode or not sys.stdin.isatty():
        return
    choices = {"": "in-place", "1": "in-place", "2": "user", "3": "system"}
    print(f"Where should Nacht des Schreckens be installed?\n"
          "  1) In place, in published/releases/ (default)\n"
          "  2) For you\n"
          "  3) For everyone (the installer runs with sudo, which asks for your password)")
    while True:
        answer = input("Choice [1]: ").strip()
        if answer in choices:
            args.mode = choices[answer]
            note(f"asked where to install, the answer was {answer!r}: {args.mode}")
            return
        print("1, 2 or 3")


def elevated(command, args):
    """`command`, run with sudo for an install for everyone when this isn't root already."""
    if args.mode == "system" and not WINDOWS and not as_root():
        print("Installing for everyone needs root: running the installer with sudo")
        note("running the installer with sudo")
        return ["sudo", *command]
    return command


def main():
    rust_on_path()
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
    for flag in ("--no-tdl", "--no-uzdoom", "--no-freedoom", "--no-blender", "--no-doomify",
                 "--no-song"):
        passed.add_argument(flag, action="store_true")
    passed.add_argument("--blender", metavar="PATH")
    passed.add_argument("--waw", metavar="DIR")
    parser.add_argument("--no-shortcuts", action="store_true",
                        help="make no shortcuts, and don't ask about them")
    parser.add_argument("--computer-speak", action="store_true",
                        help="say what it does plainly and formally, rather than as a descent "
                             "through hell" + (" (and have the installer do the same)" if INSTALLER else ""))
    args = parser.parse_args()
    speak_in("computer-speak.toml" if args.computer_speak else "toiling-through-hell.toml")
    note(f"=== {os.path.basename(__file__)} {' '.join(sys.argv[1:])} ===")
    refuse_root_build(args)

    warning(plan(args))
    shortcuts = wants_shortcuts(args, "Nacht des Schreckens")
    if not agreed(args.accept):
        note("not going ahead: nothing was done")
        sys.exit("Nothing was done.")
    check_owner([folder for folder in (os.path.normpath(os.path.join(HERE, "published")), os.path.normpath(os.path.join(HERE, "../horde-hammer/published")),) if os.path.isdir(folder)])
    tell("begin", f"Publishing and installing {WHAT}", what=WHAT, place=os.path.join(HERE, "published"))
    ask_mode(args)
    build(args)
    command = [installer()] + (["--computer-speak"] if args.computer_speak else [])
    for flag, value in (("--mode", args.mode), ("--dir", args.dir), ("--blender", args.blender),
                        ("--waw", args.waw)):
        if value:
            command += [flag, value]
    command += [flag for flag, on in (("--yes", args.yes), ("--no-tdl", args.no_tdl),
                                      ("--no-uzdoom", args.no_uzdoom),
                                      ("--no-freedoom", args.no_freedoom),
                                      ("--no-blender", args.no_blender),
                                      ("--no-doomify", args.no_doomify),
                                      ("--no-song", args.no_song)) if on]
    run(elevated(command, args))
    if shortcuts:
        shortcut(args)


if __name__ == "__main__":
    try:
        main()
        note("done")
    except subprocess.CalledProcessError as error:
        note(f"failed: {error}")
        tell("problem", f"publish-install failed: {error}", problem=error)
        tell("journal", f"What it did is in {JOURNAL}", place=JOURNAL)
        sys.exit(1)
    tell("done", "Done.", what=WHAT)
    tell("journal", f"What it did is in {JOURNAL}", place=JOURNAL)
