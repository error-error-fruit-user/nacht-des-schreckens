#!/usr/bin/env python3
"""Publish Nacht des Schreckens, then install it with the nacht-install just published.

usage: python3 publish-install.py [nacht-install options]

Runs publish.py (the pk3s and nacht-install in published/releases/), then
published/releases/nacht-install (the AppImage, or the .exe on Windows), which installs the pk3s,
tdl (through tdl-install) and Blender, then offers to run doomify.py; it asks where to install
unless given --mode. Every option goes to nacht-install (--help lists them).

Dependency-free Python 3.8+.
"""

import os
import platform
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RELEASES = os.path.join(HERE, "published", "releases")


def run(command):
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True, cwd=HERE)


def main():
    run([sys.executable, "publish.py"])
    installer = "nacht-install.exe" if platform.system() == "Windows" else "nacht-install.AppImage"
    run([os.path.join(RELEASES, installer), *sys.argv[1:]])


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(f"publish-install failed: {error}")
