// A barrel that comes back a while after it blows up

class Nacht_Barrel : ExplosiveBarrel {
    Default {
        //$Category "Nacht"
        //$Title "Barrel"
    }

    States {
    Death:
        BEXP A 5 Bright;
        BEXP B 5 Bright A_Scream;
        BEXP C 5 Bright;
        BEXP D 5 Bright A_Explode(200);
        BEXP E 10 Bright;
        TNT1 A 1050 Bright A_BarrelDestroy;
        Stop;
    }
}
