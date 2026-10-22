// The marine. World at War's weapons put themselves in slots (Weapon.SlotNumber, from doomify);
// the player starts with the M1911 and two Stielhandgranaten, which the equipment key brings up.

class Nacht_Player : DoomPlayer {
    Default {
        Player.DisplayName "Marine (Nacht)";
        Player.StartItem "Nacht_Colt";
        Player.StartItem "Nacht_Stielhandgranate";
    }
}
