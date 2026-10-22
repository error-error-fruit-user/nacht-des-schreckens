// The marine. World at War's weapons put themselves in slots (Weapon.SlotNumber, from doomify);
// the player starts with the M1911 and two Stielhandgranaten, which the equipment key brings up.

class Nacht_Player : DoomPlayer {
    Default {
        Player.DisplayName "Marine (Nacht)";
        // a start item gets no ammo of its own (Weapon.AmmoGive is for pickups)
        Player.StartItem "Nacht_Colt";
        Player.StartItem "Nacht_ColtAmmo", 32;
        Player.StartItem "Nacht_Stielhandgranate";
        Player.StartItem "Nacht_StielhandgranateAmmo", 2;
    }
}
