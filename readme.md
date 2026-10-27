# Nacht des Schreckens

> **AI notice:** this project is developed with the help of AI. The history up to July 2025 was written by hand; since October 2026, much of the code and documentation is written with [Claude](https://claude.ai) (Anthropic), working under my direction and review. Commits that Claude helped write carry a `Co-Authored-By: Claude` trailer, so you can see which ones in the history.

A remake of Nacht der Untoten, the first zombies map of 'Call of Duty: World at War', as a Doom 2 mod for the [UZDoom](https://github.com/UZDoom/UZDoom) source port. It brings the features and spirit of the classic 'Call of Duty Zombies' maps to Doom 2: hold out against endless rounds of zombies, earn points, buy weapons off the walls, open doors, gamble on the mystery box, drink perks and revive your friends.

The zombies mode itself is [Horde Hammer](https://github.com/error-error-fruit-user/horde-hammer), a library this map is built on. Many of the map's assets are taken from or based on 'World at War' (see [Credits](#credits)).

![The burning plane in the intro](assets/intro.png)

![Zombies closing in on the Ray Gun](assets/zombies.png)

![The help door](assets/help-door.png)

![A chalk wall buy](assets/wall-buy.png)

## Installation & Configuration

Nacht des Schreckens runs on [UZDoom](https://github.com/UZDoom/UZDoom) 5 or newer, and needs [Horde Hammer](https://github.com/error-error-fruit-user/horde-hammer), loaded before it, and **World at War's weapons, which you make from your own copy of the game** before you play for the first time.

They aren't in this repository, because World at War's assets can't be shared. `install-nacht` rebuilds them while it installs, with [Doomify WaW](https://github.com/error-error-fruit-user/doomify-waw)'s library built into it, from **Call of Duty: World at War** (Steam) while it runs: every weapon of Der Riese (the M1911 to the Wunderwaffe DG-2, their Pack-a-Punched versions, the Stielhandgranate, Bouncing Betty, cymbal monkey and Bowie knife), the perk bottles and their drinking, their wall drawings and sounds, and the zombies' voices, into `nacht-waw.pk3`. The perk machines are nacht's own. It needs [Blender](https://www.blender.org) 4.0 or newer, which renders the weapons, and takes about an hour the first time:

1. Start World at War and, in Zombies, play Der Riese solo. Stay in the map.
2. Run `install-nacht` (or, in this checkout, `python3 publish-install.py`).

Before then, nacht plays as **Nacht des Platzhalters**: Doom's marine and Doom's weapons stand in for World at War's (the box gives them; the perk machines sell Horde Hammer's drinks). `python3 publish.py` sets it up as a profile in a loadout of nacht's own, `published/artifacts/loadout` (joining `setup.toml` to tdl's own in `published/artifacts/` and running `tdl setup` on it; tdl doesn't start opening it), and says how to play it: `tdl --loadout published/artifacts/loadout launch "Nacht des Platzhalters"`. Once `install-nacht` has built the weapons it adds **Nacht des Schreckens** beside it, with nacht-waw bringing World at War's marine (`Nacht_Player`, the M1911 and two Stielhandgranaten) and weapons. `--no-setup` leaves Nacht des Platzhalters out. `install-nacht` and the scripts here tell you what they do in a voice from [Installation Groans](https://github.com/error-error-fruit-user/installation-groans): Toiling Through Hell, or with `--computer-speak` a plain, formal line per step; their logs keep the plain account.

The weapons' settings are in `doomify/`: a TOML per weapon (`doomify/weapons/`), the zombies' sounds (`doomify/sounds/`) and `doomify/doomify.toml`. Their data (not their text or comments) is built into `install-nacht`, which writes them into its artifacts' `doomify/` and builds the weapons from there: rewrite them there and run it again to build your own (they are kept until a newer `install-nacht` brings settings of its own, which replace them). Then load the three, in this order:

```
uzdoom -iwad doom2.wad -file horde-hammer.pk3 nacht.pk3 nacht-waw.pk3
```

The released folder (`published/releases/`) has `install-nacht` (`install-nacht.exe` on Windows, an AppImage on Linux; its source is `installer/`), which says under a red warning exactly what it will do and asks one question, "Are you sure? [y/n]" (in its voice's words: in a terminal on a screen where you tick what it does, or else in plain lines whose answer can carry any of its flags after the y, like `y --user-wide --desktop-shortcut`; `--accept` goes ahead without asking, with no shortcuts unless told), then installs where you say, which it must be told: `--locally` (in place, its tdl loadout keeping settings of its own, so the tdl you use elsewhere keeps yours) or `--user-wide` (for you; without either, nothing is done. It never installs for everyone, so it needs no root or administrator, and won't run as root), runs `install-tdl` (tdl, UZDoom, Freedoom 2 and the `tdl` command on your PATH), puts `horde-hammer.pk3` and `nacht.pk3`, the payload, in `wads/` and everything else in an `artifacts/` folder beside it (nacht's own `published/artifacts/` when it installs in place from `published/releases/`, or `--artifacts DIR`: tdl, UZDoom, Freedoom 2, Blender, the weapons' settings in `doomify/` and what is built from them, the song, the loadout and its log), downloads Blender 4.2 LTS if it isn't installed (`--no-blender` doesn't) and builds the weapons into `wads/nacht-waw.pk3` (`--no-doomify` doesn't), which needs World at War running with Der Riese loaded unless everything is already in doomify's cache. `--desktop-shortcut` and `--menu-entry` make shortcuts that open tdl on the install's loadout, with the system's lock icon. `--command` makes `nacht` a command in your terminal that does the same (`~/.local/bin/nacht`, or `nacht.cmd` on your PATH on Windows). It speaks in Toiling Through Hell (`--computer-speak`: plainly), and keeps one log, `artifacts/install.log`. Run again, it picks up where it left off (`artifacts/install.state`): tdl and the song are done once, so a song you pick in tdl afterwards stays, the weapons are built again when the doomify in it or the weapons' settings changed (only what changed is rendered again), and the profiles are set up again only when the pk3s changed; `--reinstall` does it all again (your rewritten settings replaced), and `--rerender` pulls and renders every weapon again from your game (World at War running), though they are built and in the cache. Then it pulls World at War's songs out of your game (found in your Steam libraries, or `--waw DIR`) into `songs/` in the artifacts: Der Riese's Beauty of Annihilation becomes tdl's song for every loadout (it is heavy metal, so mind your speakers), and Verrückt's Lullaby for a Dead Man and Shi No Numa's The One are songs tdl knows, there to pick in its settings (`J`/`K` on the song). A song whose map pack your game lacks is left out; `--no-song` pulls none and keeps the music you have. At the end it sets up a loadout of the install's own (`artifacts/loadout/`) with Nacht des Platzhalters in it, and Nacht des Schreckens first once `nacht-waw.pk3` is made (its part of tdl's own `setup.toml` in the artifacts, beside install-tdl's, with `tdl setup`), both playing with nacht's keyboard controls (`config.ini`, built into it from this repository and written beside `wads/` once, so the settings UZDoom keeps in it stay; `--reinstall` writes it again), and, once you have pressed Enter on its last line (every run ends on one, so you can read what it did or what went wrong), opens tdl on it (`--no-play` doesn't). `--help` lists its options.

`python3 publish.py` here (and in Horde Hammer) makes the pk3s and `install-nacht` in `published/releases/`, and also puts `horde-hammer.pk3` there; building `install-nacht` needs the checkouts of [Doomify WaW](https://github.com/error-error-fruit-user/doomify-waw) and [Hell Hound](https://github.com/error-error-fruit-user/hell-hound) beside this one. `nacht-waw` is yours alone, never share it. Without Horde Hammer, UZDoom stops at startup with "Unknown class HH_..."; without `nacht-waw`, the console tells you to run `install-nacht`.

For the IWAD, use 'doom2.wad' from a legal copy of [Doom + Doom II](https://store.steampowered.com/app/2280/DOOM__DOOM_II/), or 'freedoom2.wad' from the [Freedoom project](https://freedoom.github.io/download.html).

The easiest way to play is [tdl](https://github.com/error-error-fruit-user/tdl), a launcher for UZDoom: make a profile with `horde-hammer.pk3`, `nacht.pk3` then `nacht-waw.pk3`, and give it this repository's `config.ini` as its ini to get nacht's keyboard controls. The controller layout below is Horde Hammer's: it offers it the first time you press a button on a controller.

The weapons are drawn wide enough for screens up to 21:9.

To play against Doom's own monsters instead of the zombies, set 'Zombies' to 'Rogues gallery' in the full options menu. Horde Hammer's own options (toggled zoom, where each part of the HUD goes) are under 'Horde Hammer Options'.

## Default Controls

|Action|Keyboard|Xbox Controller|
|:---:|:---:|:---:|
|Movement|WASD Keys|Left Stick|
|Fire|Left Click|Right Trigger|
|Use|E Key|A Button|
|Reload|R Key|X Button|
|Zoom|Right Click|Left Trigger|
|Kick (a stab, once you own the Bowie knife)|F Key|Right Stick Click|
|Equipment (monkey, Betty, Bowie knife, grenades)|G Key||
|Swap Weapon|Mouse Wheel|Y Button|
|Quick Swap|1-9 Keys|D-Pad: Up first weapon, Right second, Left third|
|Drop Weapon|C Key x2|Right Bumper x2|
|Repulse/Skip Intro|Q Key|Left Bumper|

## Multiplayer

Host or join with tdl: the host serves the profile's files, and joiners download whatever they're missing.

## Credits

### Crew

- **Alexis Dutcher**: Lead Artist
- **Tyler Wojciechowski**: Lead Developer

### Base games

- **id Software's [Doom + Doom II](https://store.steampowered.com/app/2280/DOOM__DOOM_II/)**: the IWAD the mod runs on. Nacht ships no textures of its own, so every wall, floor and ceiling on the map is a Doom 2 texture (`GRAY5`, `ROCK3`, `RROCK03`, `BROWNHUG`, `FLAT5_4`, `FLAT1`, ...), and so is the sky. The fires on the crashed plane loop the Arch-vile's flame frames (`FIRE`). The Doom marine player class keeps Doom's weapons, and the 'Rogues gallery' option sends Doom's monsters instead of the zombies.
- **[Freedoom](https://freedoom.github.io/)**: the free IWAD the mod also runs on, in place of Doom 2.
- **Treyarch's [Call of Duty: World at War](https://store.steampowered.com/app/10090/Call_of_Duty_World_at_War/)**: the map remade, and the source of most of nacht's art:
    - Der Riese's weapons, perk bottles and drinking, their wall drawings and sounds and the zombies' voices, rebuilt by `install-nacht` from your own copy of the game ([Doomify WaW](https://github.com/error-error-fruit-user/doomify-waw), with [Hell Hound](https://github.com/error-error-fruit-user/hell-hound) reading the game and Blender rendering it). None of it is in this repository.
    - The perk drinking sounds: swallowing and the bottle breaking.

### Other mods and libraries

- **ZDL's [COD Zombies](https://www.moddb.com/mods/call-of-duty-nazi-zombies)** (the ZDL Edition of Call of Duty: Zombies for Doom 2), where nacht started out:
    - The zombie: every frame of its walking, attacking and dying sprites (`NAZO`).
    - The Insta-Kill, Max Ammo and Nuke power-up sprites, and the Ray Gun's bolt and its explosion (`RAYL`, `RAYX`), which the doomify Ray Guns fire.
    - The Insta-Kill and Double Points HUD icons.
    - The rest of the sounds, which were most likely pulled from World at War in the first place:
        - The announcer and jingles: the game start, round change, siren, purchase and mystery box sounds, the Nuke, Double Points, Insta-Kill, Max Ammo and Fire Sale pickups, the power-up grab, and the power-ups fading.
        - The intro music and the game over music.
- **Boondorl's [Weather library](https://github.com/Boondorl/Weather)**: the blood rain, vendored unchanged under its own license (`LICENSE-weather`).
- **[Horde Hammer](https://github.com/error-error-fruit-user/horde-hammer)**: the zombies mode itself (rounds, points, doors, the box, perks, drops, last stand, the kick, the HUD), which nacht's own code became.
- **[NTM's Quick Kick](https://github.com/LocalInsomniac/NTMAi/blob/master/zscript/weapons/kick.txt)** ([forum thread](https://forum.zdoom.org/viewtopic.php?p=1181624#p1181624)): the kick's leg and its animation (the `QKCK` sprites), on Horde Hammer's kick.

### Made for nacht

- The mystery box, the doors and the Juggernog, Quick Revive, Speed Cola and Double Tap machines, drawn by Alexis Dutcher.
- The Fire Sale and perk HUD icons, drawn by Tyler Wojciechowski with ZDL's power-up icons as a template.
- The crashed plane, drawn by `tools/plane.py`.
- The menu theme: the title screen, the console's background, the menu's title, the pause sign and the blood-drop selector, drawn by `tools/theme.py`, in nacht's own colours (`TEXTCOLO.txt`).

### Used in earlier versions

- The perks' bottles and the four drinking animations, cropped frame by frame from World at War. The first weapons' sprites and sounds (the M1911, .357 Magnum, M1 Garand, M1 Carbine, Kar98k, Thompson, PPSh-41, Type 100, double-barreled shotgun and Ray Gun), converted from World at War; the zombie's sounds from ZDL's COD Zombies; the chalk wall buys, drawn by hand or traced by `tools/chalk.py`. Doomify WaW now makes all of these from the player's own game.

- **dodopod's [ZScript Weapons Library](https://forum.zdoom.org/viewtopic.php?t=61172)**: the first weapons, since rewritten.

## License

This is open source to anyone, as long as they follow the licenses of the parts that carry their own:

- `LICENSE-weather` (Boondorl's Weather library)

Please email me if you feel that any other licenses should apply: tylerwojo81@gmail.com
