// M1 Garand: a weapon package for Horde Hammer. Its sprites are in sprites/weapons/m1garand/,
// its sounds and sndinfo.txt are next to this file in weapons/m1garand/; copy both folders, and add
// its #include to ZSCRIPT.zs and its $include to SNDINFO.txt, to use it elsewhere.

class Nacht_M1GarandAmmo : Ammo {
    Default {
        Inventory.MaxAmount 128;
    }
}

class Nacht_M1Garand : HH_Weapon {
    Default {
        Tag "M1 Garand";
        HH_Weapon.BoxWeight 1;
        Weapon.AmmoGive 56;
        Weapon.AmmoType "Nacht_M1GarandAmmo";
        HH_Weapon.ActiveAmmo 8;
        HH_Weapon.ReloadFrameRate 3;
        HH_Weapon.FireFrameRate 2;
        HH_Weapon.KeepPartialReload true;
    }

    States {
    Spawn:
        M2A0 A -1;
        Loop;
    Select:
        TNT1 A 0 WhenNoActiveAmmo("EmptyRaise");
    Raise:
        M2C0 A 1 A_Raise;
        Loop;
    Ready:
        TNT1 A 0 WhenZoomed("ZoomReady");
        TNT1 A 0 WhenNoActiveAmmo("EmptyIdle");
    Idle:
        M2C0 A 1 ReadyWeapon;
        Loop;
    Deselect:
        TNT1 A 0 ZoomOut;
        TNT1 A 0 WhenNoActiveAmmo("EmptyLower");
    Lower:
        M2C0 A 1 A_Lower;
        Loop;
    Fire:
        TNT1 A 0 WhenNoActiveAmmo("Ready");
        TNT1 A 0 WhenZoomed("ZoomFire");
        TNT1 A 0 WhenLastActiveAmmo("LastFire");
        M2F0 A 2 FF;
        TNT1 A 0 A_StartSound("weapons/m1g_fire");
        TNT1 A 0 ShootBullets(3, 25, 1);
        M2F0 BCDEF 2 FF;
        Goto Ready;
    Reload:
        TNT1 A 0 WhenFullAmmo("Ready");
        TNT1 A 0 WhenNoAmmo("Ready");
        TNT1 A 0 ZoomOut;
        TNT1 A 0 WhenAnyActiveAmmo("PartialReload");
        M2D0 ABCDEFGHIJK 3 FR;
        TNT1 A 0 A_StartSound("weapons/m1g_clipin");
        M2D0 LMNOP 3 FR;
        TNT1 A 0 A_StartSound("weapons/m1g_close");
        M2D0 QRSTUVWX 3 FR;
        TNT1 A 0 Reload;
        Goto Ready;
    Zoom:
        TNT1 A 0 ToggleZoom;
    ZoomIn:
        TNT1 A 0 ZoomIn;
        TNT1 A 0 WhenNoActiveAmmo("EmptyZoomIn");
        M2B0 ABCDEF 2;
    ZoomReady:
        TNT1 A 0 WhenNoActiveAmmo("EmptyZoomIdle");
    ZoomIdle:
        TNT1 A 0 WhenShouldZoomOut("ZoomOut");
        M2H0 A 2 ReadyWeapon;
        Loop;
    ZoomOut:
        TNT1 A 0 ZoomOut;
        TNT1 A 0 WhenNoActiveAmmo("EmptyZoomOut");
        M2B0 FEDCBA 2;
        Goto Ready;
    ZoomFire:
        TNT1 A 0 WhenLastActiveAmmo("LastZoomFire");
        M2I0 A 2 FF;
        TNT1 A 0 A_StartSound("weapons/m1g_fire");
        TNT1 A 0 ShootBullets(0.5, 25, 1);
        M2I0 BCDEF 2 FF;
        Goto Ready;
    LastFire:
        M2G0 A 2 FF;
        TNT1 A 0 A_StartSound("weapons/m1g_fire");
        TNT1 A 0 ShootBullets(3, 25, 1);
        M2G0 BCD 2 FF;
        TNT1 A 0 A_StartSound("weapons/m1g_ping");
        M2G0 E 2 FF;
        Goto Ready;
    LastZoomFire:
        M2J0 A 2 FF;
        TNT1 A 0 A_StartSound("weapons/m1g_fire");
        TNT1 A 0 ShootBullets(0.5, 25, 1);
        M2J0 BCD 2 FF;
        TNT1 A 0 A_StartSound("weapons/m1g_ping");
        M2J0 EF 2 FF;
        Goto Ready;
    PartialReload:
        M2E0 ABCDEFGHI 2 FR;
        TNT1 A 0 A_StartSound("weapons/m1g_open");
        M2E0 JK 2 FR;
        TNT1 A 0 A_StartSound("weapons/m1g_clipout");
        M2E0 LMNOPQRSTUVWXYZ 2 FR;
        M2E1 ABCDEFG 2 FR;
        TNT1 A 0 A_StartSound("weapons/m1g_clipin");
        M2E1 HIJKL 2 FR;
        TNT1 A 0 A_StartSound("weapons/m1g_close");
        M2E1 MNOPQRSTUVWXYZ 2 FR;
        M2E2 A 2 FR;
        TNT1 A 0 Reload;
        Goto Ready;
    EmptyRaise:
        M2L0 A 1 A_Raise;
        Loop;
    EmptyIdle:
        M2L0 A 1 ReadyWeapon;
        Loop;
    EmptyLower:
        M2L0 A 1 A_Lower;
        Loop;
    EmptyZoomIn:
        M2K0 ABCDEF 2;
    EmptyZoomIdle:
        TNT1 A 0 WhenShouldZoomOut("ZoomOut");
        M2M0 A 1 ReadyWeapon;
        Loop;
    EmptyZoomOut:
        M2K0 FEDCBA 2;
        Goto Ready;
    }
}

// The chalk outline to buy it off the wall
class Nacht_M1GarandDrawing : HH_WallBuy {
    Default {
        //$Title "M1 Garand Wall Buy"
        HH_WallBuy.Weapon "Nacht_M1Garand";
        HH_WallBuy.Cost 1200;
    }

    States {
    Spawn:
        GRND A -1 Bright;
        Stop;
    }
}
