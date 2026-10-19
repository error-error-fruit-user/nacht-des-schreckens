license:

    this is open source to any person, as long as they follow any license associated with any sub-license files listed:

        license_weather

        please email me if you feel that any other licenses should apply: tylerwojo81@gmail.com

# Nacht des Schreckens

> **AI notice:** this project is developed with the help of AI. The history up to July 2025 was written by hand; since October 2026, much of the code and documentation is written with [Claude](https://claude.ai) (Anthropic), working under my direction and review. Commits that Claude helped write carry a `Co-Authored-By: Claude` trailer, so you can see which ones in the history.

![demo of the map](demo.png)

Consider this a custom zombies map for 'Call of Duty: World at War' but in the vein of a Doom 2 mod using the GZDoom source port. This map pulls or modifies many assets from 'World at War'. Most likely, after the final release of the demo, further updates will have to be retrieved elsewhere and a valid copy of 'Call of Duty: World at War' will also be required to use this mod.

This mod is meant to bring the features and spirit of classic 'Call of Duty Zombies' maps into Doom 2 through a reimagining of their very first map. While this has been done before, I hope to bring this type of mod into a category of its own.

## Credit

### Base Games

- **id Software's Doom 2**: https://store.steampowered.com/app/10090/Call_of_Duty_World_at_War/

- **Freedoom**: https://freedoom.github.io/index.html

- **Treyarch's Call of Duty: World at War**: https://store.steampowered.com/app/10090/Call_of_Duty_World_at_War/
</br></br>
### Other Mods/Libraries Used

- **ZDL's COD Zombies**: https://www.moddb.com/mods/call-of-duty-nazi-zombies

- **dodopod's ZScript Weapons Library** (removed):  https://forum.zdoom.org/viewtopic.php?t=61172

- **Boondorl's Weather Library** https://github.com/Boondorl/Weather

- **Horde Hammer** https://github.com/error-error-fruit-user/horde-hammer: the zombies mode itself (rounds, points, doors, the box, perks, drops, last stand, the HUD), which nacht's code became

- **[unknown]'s NTM Quick Kick** (removed: the kick is Horde Hammer's own now):

    - https://github.com/LocalInsomniac/NTMAi/blob/master/zscript/weapons/kick.txt

    - https://forum.zdoom.org/viewtopic.php?p=1181624#p1181624

### Crew

- **Alexis Dutcher**: Lead Artist

- **Tyler Wojciechowski**: Lead Developer

## Installation & Configuration

Nacht des Schreckens runs on [UZDoom](https://github.com/UZDoom/UZDoom) 5 or newer (GZDoom can't run it any more), and needs [Horde Hammer](https://github.com/error-error-fruit-user/horde-hammer), loaded before it:

```
uzdoom -iwad doom2.wad -file horde-hammer.pk3 nacht.pk3
```

`python3 publish.py` here (and in Horde Hammer) makes the pk3s in `published/`. Without Horde Hammer, UZDoom stops at startup with "Unknown class HH_...".

Extract the 'doom2.wad' file from a legal copy of Doom 2 OR extract the 'freedoom2.wad' file from the Freedoom project: https://freedoom.github.io/download.html

The easiest way to play is [tdl](https://github.com/error-error-fruit-user/tdl), a launcher for UZDoom: make a profile with `horde-hammer.pk3` then `nacht.pk3`, and give it this repository's `config.ini` as its ini to get nacht's keyboard controls. The controller layout below is Horde Hammer's: it offers it the first time you press a button on a controller.

To avoid weapon sprite cropping, make sure the aspect ratio is set to 4:3 in-game (weapon sprites will be widened later to support wider ratios).

To play against the original rogues gallery of enemies, set 'Zombies' to 'Rogues gallery' in the full options menu. Horde Hammer's own options (toggled zoom, where each part of the HUD goes) are under 'Horde Hammer Options'.

## Default Controls

|Action|Keyboard|Xbox Controller|
|:---:|:---:|:---:|
|Movement|WASD Keys|Left Stick|
|Fire|Left Click|Right Trigger|
|Use|E Key|A Button|
|Reload|R Key|X Button|
|Zoom|Right Click|Left Trigger|
|Kick|F Key|Right Stick Click|
|Swap Weapon|Mouse Wheel|Y Button|
|Quick Swap|1-9 Keys|D-Pad (Clockwise starting from left)|
|Drop Weapon|C Key x2|Right Bumper x2|
|Repulse/Skip Intro|Q Key|Left Bumper|

## Multiplayer

Host or join with tdl: the host serves the profile's files, and joiners download whatever they're missing.

## Cross Mod Support

While there is initial support for use with other mods, there is still a long ways to go.

## Next Milestone

This mod is still early in development, so the map is very basic, the weapon roster is limited, and there are many placeholder textures. Currently, I am working towards a demo filling in these issues by creating a memorable starting area, porting more weapons from World at War, creating and pulling more assets, stabilizing the multiplayer experience, and adding an easter egg or two :)