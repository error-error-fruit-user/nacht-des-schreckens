// M1 Carbine: a weapon package for Horde Hammer. Its sprites are in sprites/weapons/carbine/,
// its sounds and sndinfo.txt are next to this file in weapons/carbine/; copy both folders, and add
// its #include to ZSCRIPT.zs and its $include to SNDINFO.txt, to use it elsewhere.

class Nacht_CarbineAmmo : Ammo {
    Default {
        Inventory.MaxAmount 120;
    }
}

class Nacht_Carbine : HH_Weapon {
    Default {
        Tag "M1 Carbine";
        HH_Weapon.BoxWeight 1;
        Weapon.AmmoGive 60;
        Weapon.AmmoType "Nacht_CarbineAmmo";
        HH_Weapon.ActiveAmmo 15;
        HH_Weapon.ReloadFrameRate 3;
        HH_Weapon.FireFrameRate 2;
        HH_Weapon.KeepPartialReload true;
    }

    States {
    Spawn:
        MCA0 A -1;
        Loop;
    Select:
        TNT1 A 0 WhenNoActiveAmmo("EmptyRaise");
    Raise:
        MCC0 A 1 A_Raise;
        Loop;
    Ready:
        TNT1 A 0 WhenZoomed("ZoomReady");
        TNT1 A 0 WhenNoActiveAmmo("EmptyIdle");
    Idle:
        MCC0 A 1 ReadyWeapon;
        Loop;
    Deselect:
        TNT1 A 0 ZoomOut;
        TNT1 A 0 WhenNoActiveAmmo("EmptyLower");
    Lower:
        MCC0 A 1 A_Lower;
        Loop;
    Fire:
        TNT1 A 0 WhenNoActiveAmmo("Ready");
        TNT1 A 0 WhenZoomed("ZoomFire");
        TNT1 A 0 WhenLastActiveAmmo("LastFire");
        MCF0 A 2 FF;
        TNT1 A 0 A_StartSound("weapons/carbine_fire");
        TNT1 A 0 ShootBullets(3, 15, 1);
        MCF0 BCD 2 FF;
        Goto Ready;
    Reload:
        TNT1 A 0 WhenFullAmmo("Ready");
        TNT1 A 0 WhenNoAmmo("Ready");
        TNT1 A 0 ZoomOut;
        TNT1 A 0 WhenAnyActiveAmmo("PartialReload");
        MCD0 ABCDEFGHI 3 FR;
        TNT1 A 0 A_StartSound("weapons/carbine_mag_out");
        MCD0 JKLMNOPQRSTUVWXY 3 FR;
        TNT1 A 0 A_StartSound("weapons/carbine_futz");
        MCD0 Z 3 FR;
        MCD1 ABCDEF 3 FR;
        TNT1 A 0 A_StartSound("weapons/carbine_mag_in");
        MCD1 GHIJKLMNOPQ 3 FR;
        TNT1 A 0 A_StartSound("weapons/carbine_charge");
        MCD1 RSTUVWXYZ 3 FR;
        MCD2 ABCD 3 FR;
        TNT1 A 0 Reload;
        Goto Ready;
    Zoom:
        TNT1 A 0 ToggleZoom;
    ZoomIn:
        TNT1 A 0 ZoomIn;
        TNT1 A 0 WhenNoActiveAmmo("EmptyZoomIn");
        MCB0 ABCDEFGH 2;
    ZoomReady:
        TNT1 A 0 WhenNoActiveAmmo("EmptyZoomIdle");
    ZoomIdle:
        TNT1 A 0 WhenShouldZoomOut("ZoomOut");
        MCH0 A 2 ReadyWeapon;
        Loop;
    ZoomOut:
        TNT1 A 0 ZoomOut;
        TNT1 A 0 WhenNoActiveAmmo("EmptyZoomOut");
        MCB0 HGFEDCBA 2;
        Goto Ready;
    ZoomFire:
        TNT1 A 0 WhenLastActiveAmmo("LastZoomFire");
        MCI0 A 2 FF;
        TNT1 A 0 A_StartSound("weapons/carbine_fire");
        TNT1 A 0 ShootBullets(0.5, 15, 1);
        MCI0 BCD 2 FF;
        Goto Ready;
    LastFire:
        MCG0 A 2 FF;
        TNT1 A 0 A_StartSound("weapons/carbine_fire");
        TNT1 A 0 ShootBullets(3, 15, 1);
        MCG0 BCD 2 FF;
        Goto Ready;
    LastZoomFire:
        MCJ0 A 2 FF;
        TNT1 A 0 A_StartSound("weapons/carbine_fire");
        TNT1 A 0 ShootBullets(0.5, 15, 1);
        MCJ0 BCD 2 FF;
        Goto Ready;
    PartialReload:
        MCE0 ABCDEFGHI 2 FR;
        TNT1 A 0 A_StartSound("weapons/carbine_mag_out");
        MCE0 JKLMNOPQRSTUVWXY 2 FR;
        TNT1 A 0 A_StartSound("weapons/carbine_futz");
        MCE0 Z 2 FR;
        MCE1 ABCDEF 2 FR;
        TNT1 A 0 A_StartSound("weapons/carbine_mag_in");
        MCE1 GHIJKLMNOPQRSTUV 2 FR;
        TNT1 A 0 Reload;
        Goto Ready;
    EmptyRaise:
        MCL0 A 1 A_Raise;
        Loop;
    EmptyIdle:
        MCL0 A 1 ReadyWeapon;
        Loop;
    EmptyLower:
        MCL0 A 1 A_Lower;
        Loop;
    EmptyZoomIn:
        MCK0 ABCDEFGH 2;
    EmptyZoomIdle:
        TNT1 A 0 WhenShouldZoomOut("ZoomOut");
        MCM0 A 1 ReadyWeapon;
        Loop;
    EmptyZoomOut:
        MCK0 HGFEDCBA 2;
        Goto Ready;
    }
}

// The chalk outline to buy it off the wall
class Nacht_CarbineDrawing : HH_WallBuy {
    Default {
        //$Title "M1 Carbine Wall Buy"
        HH_WallBuy.Weapon "Nacht_Carbine";
        HH_WallBuy.Cost 500;
    }

    States {
    Spawn:
        M1CD A -1 Bright;
        Stop;
    }
}
