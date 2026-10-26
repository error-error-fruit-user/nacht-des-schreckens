#!/usr/bin/env python3
"""Publish Nacht des Schreckens, then install it with install-nacht as cargo builds it now.

usage: python3 publish-install.py [--accept] [--no-build | --source] [install-nacht options]

First it says, under a red warning, exactly what it will do, and asks once: "Are you sure? [y/n]".
The answer can carry any of its flags after the y (`y --mode user --desktop-shortcut`), which win
over the same flags on the command line; --accept goes ahead without asking, with what the command
line says and the defaults for the rest (in place, no shortcuts). Then it builds the release with
publish.py (the pk3s, and install-nacht for Windows and as an AppImage, into published/releases/;
install-nacht is built with doomify, from the workspace's ../doomify-waw and ../hell-hound), or with
--source the pk3s only, or with --no-build nothing at all, having rebuilt the workspace's tdl
releases first if their sources are newer (--no-build too); and runs install-nacht with
`cargo run --release` in installer/ (built again whenever it, doomify or hell-hound changed, so it
is never an older one, --no-build or not) on the release in published/releases/ (`--from`), which
installs the pk3s, tdl, Blender and the songs where --mode says, puts doomify's settings in its artifacts' doomify/, builds the weapons
with doomify (World at War running, or everything in its cache) and sets up the install's loadout. --mode, --dir, --no-tdl, --no-uzdoom, --no-freedoom,
--no-blender, --no-doomify, --no-song, --waw, --blender, --desktop-shortcut and --menu-entry go
to install-nacht (see its --help).

It speaks in a voice from ../installation-groans (Toiling Through Hell, or --computer-speak), and
everything it and what it runs did is in published/artifacts/publish-install.log.

Dependency-free Python 3.8+.
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RELEASES = os.path.join(HERE, "published", "releases")
JOURNAL = os.path.join(HERE, "published", "artifacts", "publish-install.log")
WINDOWS = platform.system() == "Windows"
NAME = "nacht-des-schreckens"
# The workspace's tools install-nacht takes from their releases, the checkouts each is built from,
# and the release files it needs
TOOLS = {
    "tdl": (["tdl"], ["tdl", "install-tdl"]),
}
# What install-nacht is built from besides this checkout: doomify and hell-hound, which it links
BUILT_WITH = ["horde-hammer", "doomify-waw", "hell-hound"]
GROANS_GITHUB = "https://raw.githubusercontent.com/error-error-fruit-user/installation-groans/main/"


def load_groans():
    """installation-groans' groans.py, which these scripts speak through: the project's
    installation-groans submodule, else the workspace's checkout beside the project, else a copy
    fetched from its GitHub into published/artifacts/groans/."""
    project = HERE
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


def check_owner(folders):
    """Stops, saying how to take them back, when anything in `folders` isn't this user's (a run
    with sudo leaves root's files behind)."""
    if WINDOWS or as_root():
        return
    folders = [folder for folder in folders if os.path.isdir(folder)]
    for folder in folders:
        for root, dirs, files in os.walk(folder):
            for path in [root] + [os.path.join(root, name) for name in dirs + files]:
                try:
                    stranger = os.lstat(path).st_uid != os.getuid()
                except OSError:
                    continue
                if stranger:
                    import getpass
                    fix = "sudo chown -R " + getpass.getuser() + " " + " ".join(folders)
                    groans.say("problem", f"{path} isn't yours (a run with sudo left it)",
                               problem=f"{path} isn't yours")
                    sys.exit(f"Something in published/ belongs to another user, root most likely: "
                             f"nothing can replace it. Take it back with:\n  {fix}")


def ask(flags, args, plan):
    """The warning, then the one question; returns the arguments, with any flags given with the
    y parsed after the command line's so they win. Stops if the answer is no."""
    groans.warning(plan(args))
    names = [name for action in flags._actions for name in action.option_strings
             if name not in ("-h", "--help", "--accept")]
    added = groans.confirm(args.accept, names)
    if added is None:
        groans.note("not going ahead: nothing was done")
        groans.declined()
    if added:
        groans.note(f"with the flags given at the question: {' '.join(added)}")
        return flags.parse_args(sys.argv[1:] + added)
    return args


def plan(args):
    """What saying yes does, step by step."""
    pk3s = ("pack nacht/ into published/releases/nacht.pk3 (with LICENSE-weather) and "
            "../horde-hammer into horde-hammer.pk3 (in its published/releases/, and a copy here)")
    lines = ["Saying yes will:"]
    lines.append("  - rebuild the workspace's releases of tdl (its publish.py) if its sources are "
                 "newer than them, for install-nacht to take")
    if args.no_build:
        lines.append("  - publish nothing, and install the pk3s published/releases/ has now")
    else:
        lines.append(f"  - {pk3s}, replacing what is there")
        if not args.source:
            lines.append("  - build install-nacht, with doomify in it, into published/releases/: as an AppImage (needs "
                         "mksquashfs) and cross-built for Windows (Rust's x86_64-pc-windows-gnu target)")
    lines.append("  - run install-nacht with cargo run --release in installer/ (built again if it, "
                 "doomify or hell-hound changed) on the release in published/releases/, which:")
    user = f"%LOCALAPPDATA%\\Programs\\{NAME}" if WINDOWS else f"~/.local/opt/{NAME}"
    lines.append({
        "in-place": "    - installs in published/releases/ itself (or --dir)",
        "user": f"    - installs in {user} (or --dir)",
    }[args.mode])
    art = ("artifacts/ in --dir" if args.dir else
           "published/artifacts/" if args.mode == "in-place" else "artifacts/ there")
    lines.append("    - puts horde-hammer.pk3 and nacht.pk3, the payload, in its wads/, and "
                 f"everything else, its artifacts, in {art}: tdl, Blender, the song, the loadout, "
                 "its log, doomify's settings in doomify/ (yours to rewrite, kept until a newer "
                 "install-nacht brings its own) and the weapons built from them")
    if not args.no_tdl:
        tdl = ("    - runs install-tdl (the workspace's ../tdl/published/releases/, or else "
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
        lines.append("    - downloads Blender 4.2.9 LTS into blender/ in the artifacts, checked against "
                     "its published hash, if no Blender 4.0 or newer is installed")
    if not args.no_song:
        lines.append("    - pulls Beauty of Annihilation out of your World at War"
                     + (f" (at {args.waw})" if args.waw else " (found in your Steam libraries)")
                     + " into songs/ in the artifacts and makes it tdl's song, for every loadout. It is "
                     "heavy metal: tdl's splash will open on down-tuned riffs and screaming, so mind "
                     "your speakers (--no-song keeps the music you have). Lullaby for a Dead Man "
                     "(Verrückt's) and The One (Shi No Numa's) are pulled too, for tdl to know: they "
                     "play only if you pick one (J/K on the song in tdl's settings)")
    if not args.no_doomify and args.rerender:
        lines.append("    - pulls and renders every weapon again from World at War (--rerender), though "
                     "they are built and in the cache: an hour or more")
    if not args.no_doomify:
        lines.append("    - rebuilds the weapons from your game with doomify into wads/nacht-waw.pk3, if "
                     "World at War is running with Der Riese loaded or everything is in doomify's "
                     "cache (about an hour the first time)")
    for flag, where_to in (("desktop_shortcut", "a shortcut on your desktop"),
                           ("menu_entry", "an entry in your app menu")):
        if getattr(args, flag):
            lines.append(f"    - makes {where_to} for Nacht des Schreckens (tdl on the install's "
                         "loadout), with the system's lock icon")
    lines.append("    - sets up the install's loadout and opens tdl on it")
    lines.append("")
    lines.append("To change that, here or after the y: --no-build installs what is published already, "
                 "--source builds only for this machine, --no-tdl, --no-uzdoom, --no-freedoom, "
                 "--no-blender, --no-doomify and --no-song leave those out, --waw DIR says where World "
                 "at War is, --blender PATH uses your Blender, --mode in-place|user and --dir "
                 "say where, --desktop-shortcut and --menu-entry make shortcuts, --reinstall does it all again, --rerender renders every weapon again, and --computer-speak "
                 "speaks plainly.")
    return lines


def refresh_tools():
    """Rebuilds the workspace's releases of tdl (its publish.py) when its sources are newer than
    them, so install-nacht never takes an old one from the workspace."""
    workspace = os.path.dirname(HERE)
    suffix = ".exe" if WINDOWS else ".AppImage"
    for project, (checkouts, programs) in TOOLS.items():
        folder = os.path.join(workspace, project)
        if not os.path.isfile(os.path.join(folder, "publish.py")):
            continue
        releases = [os.path.join(folder, "published", "releases", name + suffix) for name in programs]
        if groans.up_to_date(releases, [os.path.join(workspace, checkout) for checkout in checkouts]):
            groans.note(f"{project}'s release is newer than its sources")
            continue
        check_owner([os.path.join(folder, "published")])
        groans.run([sys.executable, "publish.py"], cwd=folder, voiced=True)


def build(args):
    groans.section("build")
    refresh_tools()
    if args.no_build:
        return
    if not args.reinstall and not args.source and groans.up_to_date([os.path.join(RELEASES, name) for name in ("nacht.pk3", "horde-hammer.pk3", "install-nacht" + (".exe" if WINDOWS else ".AppImage"))], [HERE] + [os.path.join(os.path.dirname(HERE), name) for name in BUILT_WITH]):
        groans.say("skip", "The release is newer than its sources: nothing to build "
                   "(--reinstall builds it again)", what="Nacht des Schreckens's release", place=RELEASES)
        return

    if args.source:
        groans.run([sys.executable, "publish.py", "--no-appimages"], cwd=HERE, voiced=True)
        return
    groans.run([sys.executable, "publish.py"], cwd=HERE, voiced=True)


def installer():
    """install-nacht as `cargo run --release` builds it from installer/ (again whenever it, doomify
    or hell-hound changed), run on the release in published/releases/ as if it were there."""
    for pk3 in ("horde-hammer.pk3", "nacht.pk3"):
        if not os.path.isfile(os.path.join(RELEASES, pk3)):
            sys.exit(f"There is no {pk3} in published/releases/: publish it (leave out --no-build).")
    return ["cargo", "run", "--release", "--manifest-path",
            os.path.join(HERE, "installer", "Cargo.toml"), "--", "--from", RELEASES]


def parser():
    flags = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    flags.add_argument("--accept", action="store_true",
                       help="go ahead without asking, with the defaults for what isn't given")
    build_how = flags.add_mutually_exclusive_group()
    build_how.add_argument("--no-build", action="store_true",
                           help="install the pk3s published/releases/ has now, publishing nothing "
                                "(install-nacht is still cargo's current build)")
    build_how.add_argument("--source", action="store_true",
                           help="publish the pk3s only, without install-nacht's AppImage and .exe")
    passed = flags.add_argument_group("passed to install-nacht")
    passed.add_argument("--mode", choices=["in-place", "user"], default="in-place")
    passed.add_argument("--dir")
    for flag in ("--no-tdl", "--no-uzdoom", "--no-freedoom", "--no-blender", "--no-doomify",
                 "--no-song", "--rerender", "--desktop-shortcut", "--menu-entry"):
        passed.add_argument(flag, action="store_true")
    passed.add_argument("--blender", metavar="PATH")
    passed.add_argument("--waw", metavar="DIR")
    flags.add_argument("--reinstall", action="store_true",
                       help="build and install everything again, where a run picks up where the last "
                            "one left off")
    flags.add_argument("--computer-speak", action="store_true",
                       help="say what it does plainly and formally, rather than as a descent through "
                            "hell (and have install-nacht do the same)")
    return flags


def main():
    rust_on_path()
    flags = parser()
    args = flags.parse_args()
    groans.start(JOURNAL, args.computer_speak)
    if as_root():
        groans.note("run as root: refused")
        sys.exit("Don't run this with sudo: it builds and installs for you (or in place), and root "
                 "would leave files in published/ and an install that only root can change.")
    args = ask(flags, args, plan)
    check_owner([os.path.join(HERE, "published"),
                 os.path.join(os.path.dirname(HERE), "horde-hammer", "published")])
    build(args)
    groans.section("install")
    command = installer() + ["--accept", "--mode", args.mode]
    for flag, value in (("--dir", args.dir), ("--blender", args.blender), ("--waw", args.waw)):
        if value:
            command += [flag, value]
    command += [flag for flag, on in (("--no-tdl", args.no_tdl), ("--no-uzdoom", args.no_uzdoom),
                                      ("--no-freedoom", args.no_freedoom),
                                      ("--no-blender", args.no_blender),
                                      ("--no-doomify", args.no_doomify),
                                      ("--no-song", args.no_song),
                                      ("--reinstall", args.reinstall),
                                      ("--rerender", args.rerender),
                                      ("--desktop-shortcut", args.desktop_shortcut),
                                      ("--menu-entry", args.menu_entry)) if on]
    groans.run(command, cwd=HERE, voiced=True)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        groans.finish("Nacht des Schreckens", ok=False,
                      error=f"{' '.join(map(str, error.cmd))} ended with code {error.returncode}")
        sys.exit(1)
    except SystemExit as stop:
        if isinstance(stop.code, str):
            groans.say("problem", stop.code, problem=stop.code)
            sys.exit(1)
        raise
    groans.finish("Nacht des Schreckens")
