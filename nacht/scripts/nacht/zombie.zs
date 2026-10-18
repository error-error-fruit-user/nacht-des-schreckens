// World at War's zombie, on Horde Hammer's (which counts headshots)

class Nacht_Zombie : HH_Zombie {
    Default {
        //$Category "Nacht"
        //$Title "Zombie"
        Obituary "%o died.";
        Speed 3;
        DamageType "Melee";
        ActiveSound "zombie/normal";
        SeeSound "";
        PainSound "zombie/inj";
        DeathSound "";
        +NOBLOOD
        +NOEXTREMEDEATH
    }

    States {
    Spawn:
        NAZO A 1 NoDelay A_Look;
        NAZO AAAABBBBCCCCDDDD 1 A_Wander;
        Goto See;
    See:
        NAZO AAAA 1 A_Chase;
        NAZO BBBB 1 A_Chase;
        NAZO CCCC 1 A_Chase;
        NAZO DDDD 1 A_Chase;
        Loop;
    Pain:
        NAZI H 0 A_StartSound("zombie/shot", CHAN_BODY, volume: 0.3);
        NAZI H 0 A_Pain;
        Goto See;
    Melee:
        TNT1 A 0 A_StartSound("zombie/attack", CHAN_BODY);
        NAZO E 0 A_FaceTarget;
        NAZO E 0 A_Recoil(-2);
        NAZO EF 6 A_FaceTarget;
        NAZO F 3 A_CustomMeleeAttack(50, "none", "none", "Melee");
        NAZO A 15;
        Goto See;
    Death:
    XDeath:
        NAZO I 0 A_StartSound("zombie/crack", CHAN_AUTO);
        NAZO I 1 A_Scream;
        NAZO IJKLMN 2;
        TNT1 A 0 A_StartSound("zombie/fall", CHAN_AUTO, volume: 0.4);
        NAZO N 1 A_NoBlocking;
        NAZO N 512;
        Stop;
    }
}
