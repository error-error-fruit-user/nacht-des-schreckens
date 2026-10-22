// World at War's weapons and sounds aren't in nacht: doomify.py rebuilds them from the player's
// own game into ../nacht-waw, which is loaded after nacht. Without it there is nothing to play
// with, so the game stops and says what to do.

class Nacht_WorldAtWar : EventHandler {
    override void WorldLoaded(WorldEvent e) {
        Name generated = 'Nacht_DoomifyWeapon';
        if ((class<Actor>)(generated) == null) {
            ThrowAbortException("Nacht des Schreckens needs World at War's weapons: run doomify.py (with Call of Duty: World at War open on Der Riese), then load nacht-waw after nacht.");
        }
    }
}
