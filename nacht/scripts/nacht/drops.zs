// World at War's power-up drops; each replaces Horde Hammer's in the drop pool. Their HUD icons are
// nacht's, in graphics/hh/ under the library's names.

class Nacht_Instakill : HH_Instakill {
    Default {
        Scale 0.66;
    }

    States {
    Spawn:
        INST ABCDEFGH 5 Bright;
        Loop;
    }
}

class Nacht_DoublePoints : HH_DoublePoints {
    Default {
        Scale 0.66;
    }

    States {
    Spawn:
        INST A -1 Bright;
        Stop;
    }
}

class Nacht_MaxAmmo : HH_MaxAmmo {
    Default {
        Scale 0.66;
    }

    States {
    Spawn:
        MAXA ABCDEFGH 5 Bright;
        Loop;
    }
}

class Nacht_Kaboom : HH_Kaboom {
    Default {
        Scale 1.0;
    }

    States {
    Spawn:
        NUKE A -1 Bright;
        Stop;
    }
}

class Nacht_FireSale : HH_FireSale {
    Default {
        Scale 0.66;
    }

    States {
    Spawn:
        MAXA A -1 Bright;
        Stop;
    }
}
