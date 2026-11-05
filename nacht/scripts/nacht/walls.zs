// Doom's weapons on nacht's walls, in chalk: the Shotgun, the Super Shotgun and the Chaingun, at the
// spots of the Kar98k, the M1 Carbine and MP40, and the Thompson. They are the walls of Nacht des
// Platzhalters (nacht's MAPINFO gives them the wall drawings' editor numbers, 1050-1070), and of
// Nacht des Schreckens too with the "Wall weapons" option on Doom's (nacht_doom_walls), when
// Nacht_WorldAtWar puts them in place of World at War's. The other spots stay bare. The chalk is
// traced by tools/chalk.py from the pickup sprites of Freedoom: Phase 2 (NCWF) and Doom II (NCWD),
// and each drawing shows the set of the IWAD being played.

class Nacht_DoomDrawing : HH_WallBuy {
    meta int chalkFrame;    // its frame of the chalk sprites: A the shotgun, B the super shotgun, C the chaingun

    property ChalkFrame: chalkFrame;

    Default {
        //$Category "Nacht"
        Scale 0.5;
    }

    // Freedoom's IWADs have a FREEDOOM lump
    static bool OnFreedoom() {
        return Wads.CheckNumForName("FREEDOOM", Wads.ns_global) >= 0;
    }

    override void PostBeginPlay() {
        super.PostBeginPlay();
        self.sprite = Nacht_DoomDrawing.OnFreedoom()? Actor.GetSpriteIndex('NCWF'): Actor.GetSpriteIndex('NCWD');
        self.frame = self.chalkFrame;
    }

    States {
    Spawn:
        NCWD A -1 Bright;
        Stop;
    // never entered: they make both sets sprites the drawings can show
    Freedoom:
        NCWF ABC -1 Bright;
        Stop;
    Doom:
        NCWD ABC -1 Bright;
        Stop;
    }
}

class Nacht_ShotgunDrawing : Nacht_DoomDrawing {
    Default {
        //$Title "Shotgun Wall Buy"
        //$Sprite NCWDA0
        HH_WallBuy.Weapon "Shotgun";
        HH_WallBuy.Cost 500;
        Nacht_DoomDrawing.ChalkFrame 0;
    }
}

class Nacht_SuperShotgunDrawing : Nacht_DoomDrawing {
    Default {
        //$Title "Super Shotgun Wall Buy"
        //$Sprite NCWDB0
        HH_WallBuy.Weapon "SuperShotgun";
        HH_WallBuy.Cost 1000;
        Nacht_DoomDrawing.ChalkFrame 1;
    }
}

class Nacht_ChaingunDrawing : Nacht_DoomDrawing {
    Default {
        //$Title "Chaingun Wall Buy"
        //$Sprite NCWDC0
        HH_WallBuy.Weapon "Chaingun";
        HH_WallBuy.Cost 1200;
        Nacht_DoomDrawing.ChalkFrame 2;
    }
}

// A wall spot with no Doom weapon: nothing
class Nacht_BareWall : Actor {
    Default {
        //$Category "Nacht"
        //$Title "Bare Wall"
        +NOINTERACTION
        +NOBLOCKMAP
    }

    States {
    Spawn:
        TNT1 A 0;
        Stop;
    }
}

// Which Doom drawing stands in for each of World at War's (the generated Nacht_<weapon>Drawing),
// as nacht's MAPINFO places them by editor number; any other wall drawing is bare
class Nacht_DoomWalls play {
    static class<Actor> InPlaceOf(class<Actor> drawing) {
        Name drawn = drawing.GetClassName();
        if (drawn == 'Nacht_Kar98kDrawing') {
            return 'Nacht_ShotgunDrawing';
        } else if (drawn == 'Nacht_M1CarbineDrawing' || drawn == 'Nacht_Mp40Drawing') {
            return 'Nacht_SuperShotgunDrawing';
        } else if (drawn == 'Nacht_ThompsonDrawing') {
            return 'Nacht_ChaingunDrawing';
        }
        return 'Nacht_BareWall';
    }
}
