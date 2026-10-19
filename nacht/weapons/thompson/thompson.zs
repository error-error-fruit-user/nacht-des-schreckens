// Thompson: a weapon package for Horde Hammer. Its sprites are in sprites/weapons/thompson/,
// its sounds and sndinfo.txt are next to this file in weapons/thompson/; copy both folders, and add
// its #include to ZSCRIPT.zs and its $include to SNDINFO.txt, to use it elsewhere.

class Nacht_ThompsonAmmo : Ammo {
    Default {
        Inventory.MaxAmount 200;
    }
}

class Nacht_Thompson : HH_Weapon {
    Default {
        Tag "Thompson";
        HH_Weapon.BoxWeight 1;
        Weapon.AmmoGive 80;
        Weapon.AmmoType "Nacht_ThompsonAmmo";
        HH_Weapon.ActiveAmmo 20;
        HH_Weapon.ReloadFrameRate 3;
        HH_Weapon.FireFrameRate 2;
        HH_Weapon.KeepPartialReload true;
    }

    States {
    Spawn:
        TPA0 A -1;
        Loop;
    Select:
    Raise:
        TPC0 A 1 A_Raise;
        Loop;
    Ready:
        TNT1 A 0 WhenZoomed("ZoomReady");
    Idle:
        TPC0 A 1 ReadyWeapon;
        Loop;
    Deselect:
        TNT1 A 0 ZoomOut;
    Lower:
        TPC0 A 1 A_Lower;
        Loop;
    Fire:
        TNT1 A 0 WhenNoActiveAmmo("Ready");
        TNT1 A 0 WhenZoomed("ZoomFire");
        TNT1 A 0 WhenLastActiveAmmo("LastFire");
        TPF0 A 2 FF;
        TNT1 A 0 A_StartSound("weapons/thompson_fire");
        TNT1 A 0 ShootBullets(3, 12, 1);
        TPF0 BC 2 FF;
        TNT1 A 0 A_ReFire;
        TPF0 DE 2 FF;
        Goto Ready;
    Reload:
        TNT1 A 0 WhenFullAmmo("Ready");
        TNT1 A 0 WhenNoAmmo("Ready");
        TNT1 A 0 ZoomOut;
        TNT1 A 0 WhenAnyActiveAmmo("PartialReload");
        TPD0 ABCD 3 FR;
        TNT1 A 0 A_StartSound("weapons/thompson_magout");
        TPD0 EFGHIJKLM 3 FR;
        TNT1 A 0 A_StartSound("weapons/thompson_magin");
        TPD0 NOPQRSTUVW 3 FR;
        TNT1 A 0 A_StartSound("weapons/thompson_charge");
        TPD0 XYZ 3 FR;
        TPD1 ABCDEFGHIJKLM 3 FR;
        TNT1 A 0 Reload;
        Goto Ready;
    Zoom:
        TNT1 A 0 ToggleZoom;
    ZoomIn:
        TNT1 A 0 ZoomIn;
        TPB0 ABCD 2;
    ZoomReady:
    ZoomIdle:
        TNT1 A 0 WhenShouldZoomOut("ZoomOut");
        TPH0 A 2 ReadyWeapon;
        Loop;
    ZoomOut:
        TNT1 A 0 ZoomOut;
        TPB0 DCBA 2;
        Goto Ready;
    ZoomFire:
        TNT1 A 0 WhenLastActiveAmmo("LastZoomFire");
        TPI0 A 2 FF;
        TNT1 A 0 A_StartSound("weapons/thompson_fire");
        TNT1 A 0 ShootBullets(1, 12, 1);
        TPI0 BC 2 FF;
        TNT1 A 0 A_ReFire;
        TPI0 DE 2 FF;
        Goto Ready;
    LastFire:
        TPG0 A 2 FF;
        TNT1 A 0 A_StartSound("weapons/thompson_fire");
        TNT1 A 0 ShootBullets(3, 12, 1);
        TPG0 BCDE 2 FF;
        Goto Ready;
    LastZoomFire:
        TPJ0 A 2 FF;
        TNT1 A 0 A_StartSound("weapons/thompson_fire");
        TNT1 A 0 ShootBullets(1, 12, 1);
        TPJ0 BCDE 2 FF;
        Goto Ready;
    PartialReload:
        TPE0 ABCDE 2 FR;
        TNT1 A 0 A_StartSound("weapons/thompson_magout");
        TPE0 FGHIJKLMNOPQRSTU 2 FR;
        TNT1 A 0 A_StartSound("weapons/thompson_magin");
        TPE0 VWXYZ 2 FR;
        TPE1 ABCD 2 FR;
        TNT1 A 0 Reload;
        Goto Ready;
    }
}

// The chalk outline to buy it off the wall
class Nacht_ThompsonDrawing : HH_WallBuy {
    Default {
        //$Title "Thompson Wall Buy"
        HH_WallBuy.Weapon "Nacht_Thompson";
        HH_WallBuy.Cost 1000;
    }

    States {
    Spawn:
        TMPD A -1 Bright;
        Stop;
    }
}
