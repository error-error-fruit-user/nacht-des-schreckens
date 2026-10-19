// Kar98k: a weapon package for Horde Hammer. Its sprites are in sprites/weapons/kar98/,
// its sounds and sndinfo.txt are next to this file in weapons/kar98/; copy both folders, and add
// its #include to ZSCRIPT.zs and its $include to SNDINFO.txt, to use it elsewhere.

class Nacht_Kar98Ammo : Ammo {
    Default {
        Inventory.MaxAmount 60;
    }
}

class Nacht_Kar98 : HH_Weapon {
    Default {
        Tag "Kar98k";
        HH_Weapon.BoxWeight 1;
        Weapon.AmmoGive 30;
        Weapon.AmmoType "Nacht_Kar98Ammo";
        HH_Weapon.ActiveAmmo 5;
        HH_Weapon.ReloadFrameRate 3;
        HH_Weapon.FireFrameRate 2;
        HH_Weapon.KeepPartialReload true;
    }

    States {
    Spawn:
        KRA0 A -1;
        Loop;
    Select:
    Raise:
        KRC0 A 1 A_Raise;
        Loop;
    Ready:
        TNT1 A 0 WhenZoomed("ZoomReady");
    Idle:
        KRC0 A 1 ReadyWeapon;
        Loop;
    Deselect:
        TNT1 A 0 ZoomOut;
    Lower:
        KRC0 A 1 A_Lower;
        Loop;
    Fire:
        TNT1 A 0 WhenNoActiveAmmo("Ready");
        TNT1 A 0 WhenZoomed("ZoomFire");
        TNT1 A 0 WhenLastActiveAmmo("LastFire");
        TNT1 A 0 A_StartSound("weapons/kar98_fire1");
        KRE0 A 2 FF;
        TNT1 A 0 ShootBullets(1, 20, 1);
        KRE0 BCDEFGH 2 FF;
        TNT1 A 0 A_StartSound("weapons/kar98_bolt_up");
        KRE0 IJ 2 FF;
        TNT1 A 0 A_StartSound("weapons/kar98_bolt_back");
        KRE0 KL 2 FF;
        TNT1 A 0 A_StartSound("weapons/kar98_bolt_forward");
        KRE0 MNOPQRSTUV 2 FF;
        Goto Ready;
    Reload:
        TNT1 A 0 WhenFullAmmo("Ready");
        TNT1 A 0 WhenNoAmmo("Ready");
        TNT1 A 0 ZoomOut;
        KRD0 ABC 3 FR;
        TNT1 A 0 A_StartSound("weapons/kar98_bolt_back");
        KRD0 DEFGHIJKLMNOPQRSTUVWXYZ 3 FR;
        KRD1 ABCD 3 FR;
        TNT1 A 0 A_StartSound("weapons/kar98_bolt_forward");
        KRD1 EFGHIJKLMN 3 FR;
        TNT1 A 0 Reload;
        Goto Ready;
    Zoom:
        TNT1 A 0 ToggleZoom;
    ZoomIn:
        TNT1 A 0 ZoomIn;
        KRB0 ABCDE 2;
    ZoomReady:
    ZoomIdle:
        TNT1 A 0 WhenShouldZoomOut("ZoomOut");
        KRH0 A 2 ReadyWeapon;
        Loop;
    ZoomOut:
        TNT1 A 0 ZoomOut;
        KRB0 EDCBA 2;
        Goto Ready;
    ZoomFire:
        TNT1 A 0 WhenLastActiveAmmo("LastZoomFire");
        TNT1 A 0 A_StartSound("weapons/kar98_fire1");
        KRI0 A 2 FF;
        TNT1 A 0 ShootBullets(0.25, 20, 1);
        KRI0 BCDEFGH 2 FF;
        TNT1 A 0 A_StartSound("weapons/kar98_bolt_up");
        KRI0 IJ 2 FF;
        TNT1 A 0 A_StartSound("weapons/kar98_bolt_back");
        KRI0 KL 2 FF;
        TNT1 A 0 A_StartSound("weapons/kar98_bolt_forward");
        KRI0 MNOPQRSTUV 2 FF;
        Goto Ready;
    LastFire:
        TNT1 A 0 A_StartSound("weapons/kar98_fire1");
        KRG0 A 2 FF;
        TNT1 A 0 ShootBullets(1, 20, 1);
        KRG0 BCDEF 2 FF;
        Goto Ready;
    LastZoomFire:
        TNT1 A 0 A_StartSound("weapons/kar98_fire1");
        KRK0 A 2 FF;
        TNT1 A 0 ShootBullets(0.25, 20, 1);
        KRK0 BCDEF 2 FF;
        Goto Ready;
    }
}

// The chalk outline to buy it off the wall
class Nacht_Kar98Drawing : HH_WallBuy {
    Default {
        //$Title "Kar98k Wall Buy"
        HH_WallBuy.Weapon "Nacht_Kar98";
        HH_WallBuy.Cost 500;
    }

    States {
    Spawn:
        K98D A -1 Bright;
        Stop;
    }
}
