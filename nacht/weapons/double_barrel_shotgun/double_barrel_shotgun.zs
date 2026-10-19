// Double-Barreled Shotgun: a weapon package for Horde Hammer. Its sprites are in sprites/weapons/double_barrel_shotgun/,
// its sounds and sndinfo.txt are next to this file in weapons/double_barrel_shotgun/; copy both folders, and add
// its #include to ZSCRIPT.zs and its $include to SNDINFO.txt, to use it elsewhere.

class Nacht_DoubleBarrelShotgunAmmo : Ammo {
    Default {
        Inventory.MaxAmount 60;
    }
}

class Nacht_DoubleBarrelShotgun : HH_Weapon {
    Default {
        Tag "Double-Barreled Shotgun";
        HH_Weapon.BoxWeight 1;
        Weapon.AmmoGive 28;
        Weapon.AmmoType "Nacht_DoubleBarrelShotgunAmmo";
        HH_Weapon.ActiveAmmo 2;
        HH_Weapon.ReloadFrameRate 3;
        HH_Weapon.FireFrameRate 2;
        HH_Weapon.KeepPartialReload true;
    }

    States {
    Spawn:
        DBA0 A -1;
        Loop;
    Select:
    Raise:
        DBC0 A 1 A_Raise;
        Loop;
    Ready:
        TNT1 A 0 WhenZoomed("ZoomReady");
    Idle:
        DBC0 A 1 ReadyWeapon;
        Loop;
    Deselect:
        TNT1 A 0 ZoomOut;
    Lower:
        DBC0 A 1 A_Lower;
        Loop;
    Fire:
        TNT1 A 0 WhenNoActiveAmmo("Ready");
        TNT1 A 0 WhenZoomed("ZoomFire");
        TNT1 A 0 A_StartSound("weapons/shotgun_fire");
        DBF0 A 2 FF;
        TNT1 A 0 ShootBullets(5, 30, 4);
        DBF0 BCDEF 2 FF;
        Goto Ready;
    Reload:
        TNT1 A 0 WhenFullAmmo("Ready");
        TNT1 A 0 WhenNoAmmo("Ready");
        TNT1 A 0 ZoomOut;
        TNT1 A 0 WhenAnyActiveAmmo("PartialReload");
        DBD0 ABCDEFGHIJ 3 FR;
        TNT1 A 0 A_StartSound("weapons/shotgun_pull");
        DBD0 KLMNOPQRSTUVWXYZ 3 FR;
        DBD1 ABCDEFGHIJKLMNOPQRSTUV 3 FR;
        TNT1 A 0 A_StartSound("weapons/shotgun_push");
        DBD1 WXYZ 3 FR;
        DBD2 ABCD 3 FR;
        TNT1 A 0 Reload;
        Goto Ready;
    Zoom:
        TNT1 A 0 ToggleZoom;
    ZoomIn:
        TNT1 A 0 ZoomIn;
        DBB0 ABCDEFGH 2;
    ZoomReady:
    ZoomIdle:
        TNT1 A 0 WhenShouldZoomOut("ZoomOut");
        DBG0 A 2 ReadyWeapon;
        Loop;
    ZoomOut:
        TNT1 A 0 ZoomOut;
        DBB0 HGFEDCBA 2;
        Goto Ready;
    ZoomFire:
        TNT1 A 0 A_StartSound("weapons/shotgun_fire");
        DBH0 A 2 FF;
        TNT1 A 0 ShootBullets(3, 30, 4);
        DBH0 BCDEF 2 FF;
        Goto Ready;
    PartialReload:
        DBE0 ABCDEFGH 2 FR;
        TNT1 A 0 A_StartSound("weapons/shotgun_pull");
        DBE0 IJKLMNOPQRSTUVWXYZ 2 FR;
        DBE1 ABCDEFGHIJKLMNO 2 FR;
        TNT1 A 0 A_StartSound("weapons/shotgun_push");
        DBE1 PQRSTUV 2 FR;
        TNT1 A 0 Reload;
        Goto Ready;
    }
}

// The chalk outline to buy it off the wall
class Nacht_DoubleBarrelShotgunDrawing : HH_WallBuy {
    Default {
        //$Title "Double-Barreled Shotgun Wall Buy"
        HH_WallBuy.Weapon "Nacht_DoubleBarrelShotgun";
        HH_WallBuy.Cost 1200;
    }

    States {
    Spawn:
        DBSD A -1 Bright;
        Stop;
    }
}
