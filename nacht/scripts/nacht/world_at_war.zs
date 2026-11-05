// Whether World at War's weapons (nacht-waw, built by install-nacht with doomify) are loaded. Without them the map
// is Nacht des Platzhalters: Doom's weapons stand in, and the console says how to get the real ones.
// With them, the "Wall weapons" option (nacht_doom_walls) can put Doom's drawings on the walls
// (walls.zs) in place of World at War's, from the next map start.

class Nacht_WorldAtWar : EventHandler {
    override void CheckReplacement(ReplaceEvent e) {
        if (nacht_doom_walls && e.Replacee is 'HH_WallBuy' && !(e.Replacee is 'Nacht_DoomDrawing')) {
            let drawing = (class<HH_WallBuy>)(e.Replacee);
            Name generated = 'Nacht_DoomifyWeapon';
            let weapon = GetDefaultByType(drawing).weaponType;
            if (weapon != null && (class<Actor>)(generated) != null && weapon is generated) {
                e.Replacement = Nacht_DoomWalls.InPlaceOf(e.Replacee);
            }
        }
    }

    override void WorldLoaded(WorldEvent e) {
        Name generated = 'Nacht_DoomifyWeapon';
        if ((class<Actor>)(generated) == null) {
            Console.Printf("\cJNacht des Platzhalters\c-: Doom's weapons stand in for World at War's. Run install-nacht (with Call of Duty: World at War open on Der Riese) and load nacht-waw after nacht for Nacht des Schreckens.");
        }
    }
}
