# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**Nacht des Schreckens** is a UZDoom mod: a remake of Call of Duty: World at War's first zombies map (Nacht der Untoten) on Doom 2, with assets taken from or based on World at War. Everything the engine loads is in `nacht/`, which is the root of the pk3. User-facing docs are in `readme.md`. Planned work is in `secrets/TODO.md` (local, untracked); work that spans the projects in `..` is in `../TODO.md`.

The zombies mode is **Horde Hammer** (`../horde-hammer`, prefix `HH_`), a separate library pk3 loaded before nacht; nacht's old hard-coded `zmd` code became it. Nacht keeps only what is its own: the map and its intro, the plane, the barrel, the weather, World at War's weapons, zombie, perk machines and drops, and its art and sounds. Read `../horde-hammer/CLAUDE.md` (and its README) before changing anything that touches the library; a change the library needs is made there, not worked around here.

## Commands

- Pack: `python3 publish.py` zips `nacht/` into `published/nacht.pk3` (with `LICENSE-weather` next to it and inside it under `licenses/`); `--out FILE` writes only the pk3 somewhere else (like `../tdl/secrets/wads/nacht.pk3`). The library isn't in it: players load `horde-hammer.pk3` first. Dependency-free, reproducible, and warns about case collisions, lump names over 8 characters, bad sprite names and SNDINFO entries naming missing files; `--strict` fails on them.
- Play without packing: `uzdoom -iwad freedoom2.wad -file ../horde-hammer/hh nacht` (folders load like pk3s). Players use tdl (`../tdl`) to play and to host or join; `config.ini` is nacht's control layout, for a tdl profile's ini (`../tdl/secrets/nacht.ini` is the owner's).
- Check and test with Horde Hammer's tools, which take extra files to load after the library: `../horde-hammer/secrets/check.sh nacht` compiles both; `../horde-hammer/secrets/run.sh -m MAP01 "commands; wait 2; quit" ../horde-hammer/test nacht` plays the map headless (load `test` before nacht so nacht's `HH_Defaults` wins, and its `hhtest_*` events work: `netevent hh_repulse` skips the intro); `../horde-hammer/secrets/net.sh` does the same with two players.
- ACS: nacht's map logic is `acs/nacht.acs` (text, not packed); `secrets/acc.sh acs/nacht.acs nacht/acs/nacht.o` compiles it with the ACC kept in `secrets/acc/` (through Wine), with Horde Hammer's `acs/` (for `hh.acs`) on the include path. Commit the `.o` with the source; `nacht/LOADACS.txt` loads it on every map.
- Version control is **jj** (colocated with git; the remote is `origin`, `main` tracks `main@origin`). `secrets/commit.sh "msg" [--claude]` commits and moves the `main` bookmark; use `--claude` for work Claude helped write (adds the Co-Authored-By trailer). Commit each finished piece as you go. `secrets/push.sh` pushes `main` as `error-error-fruit-user` with `secrets/token.txt` or, if there is none, the shared `../token.txt`. Both run from anywhere in the project.

## Layout

- `nacht/ZSCRIPT.zs` (`version "5.0.0"`) includes `scripts/nacht/` (nacht's own: `defaults.zs` with `Nacht_Defaults : HH_Defaults`, the player, zombie, perk machines and drinks, drops, doors, the intro's title and sway target, the burning plane and the barrel) and `scripts/weather/`.
- The intro and game over are ACS (`acs/nacht.acs`): it listens to Horde Hammer's `repulse_pressed` (the skip) and `game_over` events, views the intro camera on ENTER, and starts round 1 with `HH_MoveAllToSpawn()` and `HH_StartGame()` after 1015 tics or a skip. `Nacht_IntroHandler` only draws the title, until the game has started.
- The plane (`Nacht_Plane`, a wreck drawn by `python3 tools/plane.py`) lights four `Nacht_PlaneFire`s along itself; more can be placed (1017). They use the IWAD's Arch-vile `FIRE` frames, a flicker light in `GLDEFS.txt` and smoke particles.
- **Weapons are drop-in packages**: each has `zscript.<weapon>` and `sndinfo.<weapon>` at the pk3 root (all ZSCRIPT and SNDINFO lumps load), and its art and sounds in `sprites/weapons/<weapon>/` and `sounds/weapons/<weapon>/`. They subclass `HH_Weapon` (`Nacht_Colt`, ...), with box weights and last stand ranks; every weapon but the Ray Gun has a chalk wall drawing in its package (DoomEdNums 1050-1058). The Kar98k's, M1 Carbine's and Thompson's are hand-drawn; the rest are traced from the pickup sprites by `python3 tools/chalk.py`. The player's slots and start items are `Nacht_Player`.
- Lumps are uppercase `.txt` (`MAPINFO.txt` with the player classes, `HH_Hud`, the intro handler and nacht's DoomEdNums; `SNDINFO.txt`, which also points the library's `hh/...` sounds at nacht's; `MENUDEF.txt`, `LANGUAGE.txt`, `WTHRINFO.txt`).
- `scripts/weather/` and the `*.0weather` lumps are **Boondorl's Weather library** (vendored, `LICENSE-weather`). Leave its code as upstream wrote it (no restyling, no renames), so it can be updated.
- Art that stands in for the library's placeholders uses the library's names: perk, power-up and revive pictures in `graphics/hh/` (`hhijg.png`, ...), the box in `sprites/mystery_box/hhbx?0.png`, the unknown pickup `hhnla0.png`. The lock the box shows when it moves is still the library's placeholder.
- `maps/map01.wad` is UDMF with an empty `BEHAVIOR` (nacht's ACS is the LOADACS library, not map scripts). Library things use the library's numbers (spawners 27000 with zones 0-2 in arg 0, box locations 27001, the spectator spot 27008, respawn spots 27011 for players 1-4); nacht's own things keep 1005-1017 and 1050-1058. The help door and boxes open zones in their args. TIDs the ACS uses: 13 the intro camera, 20 the intro's actor mover, 25 the intro's sway target, 116 the intro zombie, 11 the game over camera. Edit it with Ultimate Doom Builder; its `.dbs` and backups are ignored.

## Conventions

Nacht's ZScript follows Horde Hammer's (see `../horde-hammer/CLAUDE.md`): the engine's capitalization, explicit `self.`, 4 spaces, names that don't clash in any case, and the multiplayer rules. Nacht's classes are `Nacht_`. Nacht never names anything `zmd_` any more.

## Working in this repo

- Ask before editing project files (standing preference of the repo owner).
- `secrets/` (`commit.sh`, `push.sh`, `acc/`, `acc.sh`, `TODO.md`, any token) and `published/` are local/untracked; don't commit them, and never read `token.txt` (here or in `..`).
- Keep the AI notice at the top of `readme.md`, and the credits there up to date when code or assets come from elsewhere.
