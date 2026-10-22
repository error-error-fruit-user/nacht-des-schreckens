// World at War's zombie, on Horde Hammer's (which counts headshots). Its sounds are Der Riese's,
// rebuilt by doomify.py (zombie/...): it groans, hisses, dies, comes apart under explosions, burns
// and is electrocuted by the Wunderwaffe.

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
        DeathSound "zombie/death";
        +NOBLOOD
        +NOEXTREMEDEATH
    }

    // A jolt of the Wunderwaffe's lightning: a twitch and sparks
    void Shock() {
        self.SpriteOffset = (FRandom[Nacht](-3, 3), FRandom[Nacht](-2, 2));
        for (let i = 0; i < 4; ++i) {
            self.A_SpawnParticle(Color(127, 216, 255), SPF_FULLBRIGHT, 10, 4, 0,
                FRandom[Nacht](-12, 12), FRandom[Nacht](-12, 12), FRandom[Nacht](8, self.height),
                FRandom[Nacht](-2, 2), FRandom[Nacht](-2, 2), FRandom[Nacht](0, 2), startalphaf: 1, fadestepf: 0.08);
        }
    }

    void Unshock() {
        self.SpriteOffset = (0, 0);
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
        TNT1 A 0 A_StartSound("zombie/whoosh", CHAN_WEAPON);
        NAZO E 0 A_FaceTarget;
        NAZO E 0 A_Recoil(-2);
        NAZO EF 6 A_FaceTarget;
        NAZO F 3 A_CustomMeleeAttack(50, "none", "none", "Melee");
        NAZO A 15;
        Goto See;
    // The Wunderwaffe: it shakes and sparks, then drops
    Death.Tesla:
        NAZI H 0 A_StartSound("zombie/elec", CHAN_VOICE);
        NAZI HHHHHHHHHHHH 2 Bright Shock;
        NAZI H 0 Unshock;
        Goto Dying;
    Death.Fire:
        NAZI H 0 A_StartSound("zombie/burn", CHAN_BODY);
        Goto Death;
    XDeath:
    Death.Explosive:
        NAZO I 0 A_StartSound("zombie/gib", CHAN_BODY);
        Goto Death;
    Death:
        NAZO I 0 A_StartSound("zombie/crack", CHAN_AUTO);
    Dying:
        NAZO I 1 A_Scream;
        NAZO IJKLMN 2;
        TNT1 A 0 A_StartSound("zombie/fall", CHAN_AUTO, volume: 0.4);
        NAZO N 1 A_NoBlocking;
        NAZO N 512;
        Stop;
    }
}
