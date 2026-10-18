// The marine, with World at War's weapons in the slots

class Nacht_Player : DoomPlayer {
    Default {
        Player.DisplayName "Marine (Nacht)";
        Player.StartItem "Nacht_Colt";
        Player.StartItem "Nacht_ColtAmmo", 32;
        Player.WeaponSlot 1, "Nacht_Colt", "Nacht_Magnum";
        Player.WeaponSlot 2, "Nacht_Kar98", "Nacht_Carbine";
        Player.WeaponSlot 3, "Nacht_M1Garand";
        Player.WeaponSlot 4, "Nacht_DoubleBarrelShotgun";
        Player.WeaponSlot 5, "Nacht_Type100", "Nacht_Thompson";
        Player.WeaponSlot 6, "Nacht_Ppsh";
        Player.WeaponSlot 7, "Nacht_Raygun";
    }
}
