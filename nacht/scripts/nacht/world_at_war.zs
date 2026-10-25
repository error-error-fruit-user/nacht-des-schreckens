// Whether World at War's weapons (nacht-waw, built by install-nacht with doomify) are loaded. Without them the map
// is Nacht des Platzhalters: Doom's weapons stand in, and the console says how to get the real ones.

class Nacht_WorldAtWar : EventHandler {
    override void WorldLoaded(WorldEvent e) {
        Name generated = 'Nacht_DoomifyWeapon';
        if ((class<Actor>)(generated) == null) {
            Console.Printf("\cJNacht des Platzhalters\c-: Doom's weapons stand in for World at War's. Run install-nacht (with Call of Duty: World at War open on Der Riese) and load nacht-waw after nacht for Nacht des Schreckens.");
        }
    }
}
