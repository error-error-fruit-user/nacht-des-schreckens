// The crashed plane outside (drawn by tools/plane.py), burning: it lights its own fires on the
// wreck, and more can be placed by hand (DoomEdNum 1017)

class Nacht_Plane : Actor {
    // Where its fires burn on the picture: across it (pixels right of its middle) and up it (above
    // the ground). The plane always faces the viewer, so its fires stand where it stands, shifted
    // on screen with SpriteOffset: placed along the wreck in the world, they would end up mirrored
    // from behind it and hidden behind its picture.
    static const double FIRE_X[] = { -106, -44, 18, 94 };
    static const double FIRE_HEIGHT[] = { 20, 46, 12, 60 };

    Default {
        //$Category "Nacht"
        //$Title "Plane"
        +SOLID
    }

    override void PostBeginPlay() {
        super.PostBeginPlay();
        for (let i = 0; i < Nacht_Plane.FIRE_X.Size(); ++i) {
            let fire = Nacht_PlaneFire(Actor.Spawn('Nacht_PlaneFire', self.pos + (0, 0, Nacht_Plane.FIRE_HEIGHT[i])));
            if (fire != null) {
                fire.SpriteOffset = (Nacht_Plane.FIRE_X[i], 0);
                fire.smokeSpread = abs(Nacht_Plane.FIRE_X[i]);
                // Out of step with each other, so the flames don't flicker together
                fire.tics = 1 + i * 2;
            }
        }
    }

    States {
    Spawn:
        PLNE A -1;
        Stop;
    }
}

// A burning patch: the Arch-vile's flames (every Doom 2 IWAD has them), a flickering light
// (GLDEFS.txt) and smoke rising from it
class Nacht_PlaneFire : Actor {
    // How far from it the smoke may rise, for the plane's fires, which stand in its middle
    double smokeSpread;

    Default {
        //$Category "Nacht"
        //$Title "Plane Fire"
        RenderStyle "Add";
        Alpha 0.9;
        Scale 0.8;
        +NOINTERACTION
        +NOGRAVITY
        +FORCEXYBILLBOARD
    }

    // A puff of smoke drifting up out of the flames; cosmetic, so nothing depends on it
    void Smoke() {
        let away = Actor.AngleToVector(FRandom[Nacht_Fire](0, 360), FRandom[Nacht_Fire](0, self.smokeSpread));
        self.A_SpawnParticle("2A2622", SPF_RELATIVE, 105, FRandom[Nacht_Fire](10, 18), 0,
            away.x + FRandom[Nacht_Fire](-6, 6), away.y + FRandom[Nacht_Fire](-6, 6), FRandom[Nacht_Fire](40, 60),
            FRandom[Nacht_Fire](-0.2, 0.2), FRandom[Nacht_Fire](-0.2, 0.2), FRandom[Nacht_Fire](0.6, 1.1),
            startalphaf: 0.45, sizestep: 0.15);
    }

    States {
    // Only the frames standing on the ground: from E on, the Arch-vile's flame dies away and lifts
    // off (in Doom 2 and Freedoom alike), which floats above the wreck
    Spawn:
        FIRE BC 3 Bright;
        FIRE D 4 Bright Smoke;
        FIRE C 3 Bright;
        Loop;
    }
}
