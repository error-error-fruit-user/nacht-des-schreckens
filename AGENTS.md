# Nacht des Schreckens — agent context

## Start here

- Read `CLAUDE.md` for the detailed architecture, map TIDs and commands, and `../horde-hammer/CLAUDE.md` for ZScript style and multiplayer safety rules.
- A UZDoom remake of Nacht der Untoten, using World at War-derived assets. `nacht/` is the pk3 root; classes use `Nacht_`.
- The old `zmd` systems are already ported to Horde Hammer. Load Horde Hammer first as a separate dependency; implement general systems there, not as game-specific workarounds here.
- `nacht/scripts/nacht/` holds game-specific actors and defaults. World at War's weapons and zombie sounds are not in the repository: `install-nacht` (`installer/`) is built with doomify (the library in `../doomify-waw`, with `../hell-hound`) and rebuilds them from the player's running game into its artifacts' `nacht-waw/` (`published/artifacts/nacht-waw/` in place), packed into `wads/nacht-waw.pk3` and loaded after nacht. `doomify/` holds `doomify.toml` and a TOML per weapon and sound set, built into install-nacht as consts (`const_toml!`) and put in its artifacts' `doomify/`, which the weapons are built from; `Nacht_WorldAtWar` stops the game if `nacht-waw` isn't loaded.
- `acs/nacht.acs` owns intro/game-over logic and compiles to `nacht/acs/nacht.o`, loaded through LOADACS. Commit the compiled object alongside source changes.
- Leave vendored `nacht/scripts/weather/` and `*.0weather` lumps in upstream style; preserve `LICENSE-weather` and credits.

## Build and verify

Run from this project directory:

- Pack: `python3 publish.py --strict`.
- Compile after ZScript changes: `../horde-hammer/secrets/check.sh nacht published/artifacts/nacht-waw` (it exists once `install-nacht` has built the weapons in place, by `python3 publish-install.py`).
- ACS: `secrets/acc.sh acs/nacht.acs nacht/acs/nacht.o`.
- Headless: `../horde-hammer/secrets/run.sh -m MAP01 "netevent hh_repulse; wait 35; netevent hhtest_state; wait 2; quit" ../horde-hammer/test nacht published/artifacts/nacht-waw`. Nacht loads after test so its defaults win; repulse skips the intro.
- Multiplayer: use Horde Hammer's `secrets/net.sh`; compare peer state, not just exit status.

## Working rules

- Ask before editing project files; an explicit request authorizes only its scope.
- Use the engine's capitalization, explicit `self.`, four spaces, case-insensitively unique identifiers and the library's lockstep safety rules.
- Preserve the AI notice and asset/code credits in `readme.md`.
- Version control is jj colocated with git. For ChatGPT via OpenCode work, use `secrets/commit.sh "message" --opencode` when committing is requested. `--claude` remains available separately.
- Never read tokens or commit `secrets/` or `published/`.
- Current tasks and manual play checks: `secrets/TODO.md`; cross-project work: `../TODO.md`. Check them before planning work.
