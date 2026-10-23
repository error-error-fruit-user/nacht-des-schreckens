// The marine. World at War's weapons put themselves in slots (Weapon.SlotNumber, from doomify);
// the player starts with the M1911 and two Stielhandgranaten, which the equipment key brings up.

class Nacht_Player : DoomPlayer {
    Default {
        Player.DisplayName "Marine (Nacht)";
        // DoomPlayer's slots hold Doom's weapons, which the box would give: empty, so only
        // World at War's weapons (which put themselves in slots) are in them
        Player.WeaponSlot 1, "";
        Player.WeaponSlot 2, "";
        Player.WeaponSlot 3, "";
        Player.WeaponSlot 4, "";
        Player.WeaponSlot 5, "";
        Player.WeaponSlot 6, "";
        Player.WeaponSlot 7, "";
        // a start item gets no ammo of its own (Weapon.AmmoGive is for pickups)
        Player.StartItem "Nacht_Colt";
        Player.StartItem "Nacht_ColtAmmo", 32;
        Player.StartItem "Nacht_Stielhandgranate";
        Player.StartItem "Nacht_StielhandgranateAmmo", 2;
    }
}
