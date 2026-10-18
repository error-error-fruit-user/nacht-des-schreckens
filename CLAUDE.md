# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**Nacht des Schreckens** is a GZDoom/UZDoom mod: a remake of Call of Duty: World at War's first zombies map (Nacht der Untoten) on Doom 2, with assets taken from or based on World at War. Everything the engine loads is in `nacht/`, which is the root of the pk3. User-facing docs are in `readme.md`. Planned work is in `secrets/TODO.md` (local, untracked); work that spans the projects in `..` (Horde Hammer, tdl) is in `../TODO.md`.

The zombies systems are hard-coded here as `zmd` (prefix `zmd_`). They are moving into **Horde Hammer** (`../horde-hammer`, prefix `HH_`), a separate library pk3 that nacht will then load before itself and depend on. After the move, nacht keeps only what is its own: the map, the intro, the plane, the barrel, the weather, World at War's weapons and assets, and its map scripts. Until then, read `../horde-hammer/CLAUDE.md` before changing `zmd`, since new code there should already follow the library's rules.

## Commands

- Pack: `python3 publish.py` zips `nacht/` into `published/nacht.pk3` (with `LICENSE-weather` next to it and inside it under `licenses/`); `--out FILE` writes only the pk3 somewhere else (like `../tdl/secrets/wads/nacht.pk3`). Dependency-free Python 3.8+, reproducible (same folder, same bytes), skips editor leftovers (`.dbs`, `.wad.backup*`), and warns about case collisions, lump names over 8 characters, bad sprite names and SNDINFO entries naming missing files; `--strict` fails on them.
- Play without packing: GZDoom/UZDoom load a folder with `-file nacht` (`run-linux/launch.sh` already does). `../tdl/uzdoom.sh` wraps the flatpak UZDoom; `run-linux/*.sh` still expect a Windows GZDoom under wine at `../../gzdoom/` and need updating (see `secrets/TODO.md`).
- Multiplayer on one machine: one instance with `-host 2`, another with `-join 127.0.0.1`, both with the same files.
- ACS: `secrets/acc.sh source.acs output.o` compiles with the ACC kept in `secrets/acc/` (through Wine), with Horde Hammer's `acs/` (for `hh.acs`) on the include path.
- Headless testing: Horde Hammer's `secrets/check.sh`, `run.sh` and `net.sh` take extra files to load after the library, so `../horde-hammer/secrets/check.sh nacht` compiles both together.
- Logs: `+logfile nacht.log` (or `-stdout`) and `+developer 1`. A VM abort prints a ZScript stack trace; start there for any crash.
- Version control is **jj** (colocated with git; the remote is `origin`, `main` tracks `main@origin`). `secrets/commit.sh "msg" [--claude]` commits and moves the `main` bookmark; use `--claude` for work Claude helped write (adds the Co-Authored-By trailer). `secrets/push.sh` pushes `main` as `error-error-fruit-user` with `secrets/token.txt` or, if there is none, the shared `../token.txt`. Both run from anywhere in the project.

## Layout

- `nacht/zscript.zs` (`version "4.14.2"`) includes `scripts/zmd/zmd.zs` (which includes the rest of zmd), `scripts/misc/` (nacht's own: `intro.zs`, `plane.zs`, `barrel.zs`) and `scripts/weather/`.
- `scripts/weather/` and the `*.0weather` lumps are **Boondorl's Weather library** (vendored, `LICENSE-weather`). Leave its code as upstream wrote it (no restyling, no renames), so it can be updated; nacht uses it through `wthrinfo.lmp` (`BloodRain`).
- Lumps are lowercase with `.lmp` (`mapinfo.lmp`, `sndinfo.lmp`, `cvarinfo.lmp`, `menudef.lmp`, `textures.lmp`). Files at the pk3 root whose names differ only in extension load as the same lump, which is how `mapinfo.lmp` and `mapinfo.0weather` both apply. `mapinfo.lmp` sets the player classes, `zmd_Hud`, every event handler and the DoomEdNums (zmd things 1003–1015, nacht's 1005/1014/1016, wall drawings 1050–1052).
- `maps/map01.wad` is UDMF (`TEXTMAP`, `ZNODES`) with a `BEHAVIOR` lump but no `SCRIPTS` lump, so the ACS source of whatever is compiled in it isn't in the repo. Edit it with Ultimate Doom Builder; its `.dbs` and backups are ignored.
- The map and the code meet through TIDs that are hard-coded on both sides: player spots 100 + player number, 1 box locations, 5 initial spawners, 11 game over camera, 13 intro camera, 15 live players, 20 activated at the start, 25 intro sway target, 115 spawned zombies **and** the intro zombie (the same TID). Changing one in the map without the code, or the other way around, breaks the game quietly.
- `sprites/`, `sounds/` are World at War assets (and placeholders like the plane's red rectangle `sprites/decorations/plnea0.png`). `sprites/` also holds HUD icons (`dtic`, `revfore`, ...) that aren't sprite frames; they belong in `graphics/`.

## Conventions

Code moving toward Horde Hammer follows the engine's style, as `../horde-hammer/CLAUDE.md` describes: PascalCase classes, methods and engine calls (`A_StartSound`, `Level.CreateActorIterator`), UPPER_CASE constants and flags, uppercase sprite names in states, lumps renamed to uppercase `.txt` (`MAPINFO.txt`). The existing zmd code is all lowercase; restyle a file when it is ported or rewritten, not piecemeal. nacht's own classes keep the `nacht_` prefix (or `Nacht_`, once restyled), and once zmd is gone nothing in nacht should be named `zmd_`.

The multiplayer rules in `../horde-hammer/CLAUDE.md` apply here too (no `consolePlayer` in play scope, null checks on every lookup, `MAXPLAYERS`-long arrays, named RNGs, input through network events). The crashes found so far are listed in `secrets/TODO.md`.

## Working in this repo

- Ask before editing project files (standing preference of the repo owner).
- `secrets/` (`commit.sh`, `push.sh`, `TODO.md`, any token) and `published/` are local/untracked; don't commit them, and never read `token.txt` (here or in `..`).
- Keep the AI notice at the top of `readme.md`, and the credits there up to date when code or assets come from elsewhere.
