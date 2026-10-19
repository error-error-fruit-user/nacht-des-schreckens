// The crashed plane outside (drawn by tools/plane.py), burning: it lights its own fires along the
// wreck, and more can be placed by hand (DoomEdNum 1017)

class Nacht_Plane : Actor {
    // Where its fires burn: across the wreck (side) and up it (height), from its middle
    static const double FIRE_SIDE[] = { -110, -45, 20, 95 };
    static const double FIRE_HEIGHT[] = { 10, 40, 20, 55 };

    Default {
        //$Category "Nacht"
        //$Title "Plane"
        +SOLID
    }

    override void PostBeginPlay() {
        super.PostBeginPlay();
        let side = Actor.AngleToVector(self.angle + 90);
        for (let i = 0; i < Nacht_Plane.FIRE_SIDE.Size(); ++i) {
            let offset = side * Nacht_Plane.FIRE_SIDE[i];
            let fire = Actor.Spawn('Nacht_PlaneFire', self.pos + (offset.x, offset.y, Nacht_Plane.FIRE_HEIGHT[i]));
            if (fire != null) {
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
// (GLDEFS.txt) and smoke rising from it. Replace the FIRE frames here with the plane's own flames.
class Nacht_PlaneFire : Actor {
    Default {
        //$Category "Nacht"
        //$Title "Plane Fire"
        RenderStyle "Add";
        Alpha 0.9;
        Scale 1.1;
        +NOINTERACTION
        +NOGRAVITY
        +FORCEXYBILLBOARD
    }

    // A puff of smoke drifting up out of the flames; cosmetic, so nothing depends on it
    void Smoke() {
        self.A_SpawnParticle("2A2622", SPF_RELATIVE, 105, FRandom[Nacht_Fire](10, 18), 0,
            FRandom[Nacht_Fire](-6, 6), FRandom[Nacht_Fire](-6, 6), FRandom[Nacht_Fire](40, 60),
            FRandom[Nacht_Fire](-0.2, 0.2), FRandom[Nacht_Fire](-0.2, 0.2), FRandom[Nacht_Fire](0.6, 1.1),
            startalphaf: 0.45, sizestep: 0.15);
    }

    States {
    Spawn:
        FIRE ABCD 3 Bright;
        FIRE E 3 Bright Smoke;
        FIRE FGH 3 Bright;
        FIRE G 3 Bright Smoke;
        FIRE FED 3 Bright;
        Loop;
    }
}
