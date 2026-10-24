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
--no-uzdoom, --no-freedoom, --no-blender, --no-doomify and --blender go to nacht-install (see its
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
EXE = ".exe" if WINDOWS else ""
NAME = "nacht-des-schreckens"


# The journal: everything this does, with the time since it began (what it plans and is told,
# every command and all it prints, every file it puts somewhere), added to JOURNAL on each run.
JOURNAL = os.path.join(HERE, "published", "publish-install.log")
BEGAN = time.monotonic()
# Blender's line for every frame it renders, which would bury the rest
CHATTER = ("Fra:", "Saved:", "Time:", "Read blend")


def note(line):
    """Writes `line` down in the journal."""
    os.makedirs(os.path.dirname(JOURNAL), exist_ok=True)
    with open(JOURNAL, "a", encoding="utf-8") as journal:
        for part in line.splitlines() or [""]:
            journal.write(f"[{time.monotonic() - BEGAN:8.3f}s] {part}\n")


def run(command, cwd=HERE):
    """Runs `command`, its output shown as it comes (prompts included) and written down, with how it
    ended. Raises CalledProcessError if it failed."""
    shown = " ".join(str(part) for part in command)
    print("+", shown, flush=True)
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
                 "nacht-install's questions, --mode and --dir say where, and --no-shortcuts doesn't "
                 "ask about shortcuts.")
    return lines


def build(args):
    if args.no_build:
        return
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


def install_dir(args):
    """Where nacht-install just installed: --dir, or where --mode puts it, or (when it asked) the
    newest of those places with a loadout."""
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
    found = [folder for folder in modes.values() if os.path.isdir(os.path.join(folder, "loadout"))]
    return max(found, key=lambda folder: os.path.getmtime(os.path.join(folder, "loadout"))) \
        if found else None


def shortcut(args):
    """The Nacht des Schreckens shortcut: the install's tdl (or the one on the PATH) on its loadout,
    as nacht-install opens it at the end."""
    folder = install_dir(args)
    if folder is None or not os.path.isdir(os.path.join(folder, "loadout")):
        print("Made no shortcut: nacht-install's folder, with its loadout, isn't where this can "
              "find it.")
        return
    folder = os.path.abspath(folder)
    names = ["tdl.exe"] if WINDOWS else ["tdl", "tdl.AppImage"]
    tdl = next((os.path.join(folder, name) for name in names
                if os.path.isfile(os.path.join(folder, name))), None) or shutil.which("tdl")
    if tdl is None:
        print("Made no shortcut: there is no tdl beside nacht or on your PATH.")
        return
    make_shortcut("Nacht des Schreckens", NAME,
                  [tdl, "--session", "--loadout", os.path.join(folder, "loadout"),
                   "--wads", os.path.join(folder, "wads")],
                  "World at War's Nacht der Untoten on Doom 2, in tdl")


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
    parser.add_argument("--no-shortcuts", action="store_true",
                        help="make no shortcuts, and don't ask about them")
    args = parser.parse_args()
    note(f"=== {os.path.basename(__file__)} {' '.join(sys.argv[1:])} ===")

    warning(plan(args))
    shortcuts = wants_shortcuts(args, "Nacht des Schreckens")
    if not agreed(args.accept):
        note("not going ahead: nothing was done")
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
    if shortcuts:
        shortcut(args)


if __name__ == "__main__":
    try:
        main()
        note("done")
    except subprocess.CalledProcessError as error:
        note(f"failed: {error}")
        sys.exit(f"publish-install failed: {error}\nWhat it did is in {JOURNAL}")
    print(f"What it did is in {JOURNAL}")
