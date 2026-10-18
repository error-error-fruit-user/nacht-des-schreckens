// The boarded doors and the piles of boxes in the way

// A door drawn front and back: the back is a second wall sprite just behind it
class Nacht_HelpDoor : HH_Door {
    Actor back;

    Default {
        //$Category "Nacht"
        //$Title "Help Door"
        Radius 16;
        Height 150;
    }

    override void PostBeginPlay() {
        super.PostBeginPlay();
        let offset = Actor.AngleToVector(self.angle, 1);
        self.back = Actor.Spawn('Nacht_HelpDoorBack', self.pos - (offset.x, offset.y, 0));
        if (self.back != null) {
            self.back.angle = self.angle;
        }
    }

    override void Open() {
        if (self.back != null) {
            self.back.Destroy();
        }
        super.Open();
    }

    States {
    Spawn:
        DOOR A -1;
        Stop;
    }
}

class Nacht_HelpDoorBack : Actor {
    Default {
        +WALLSPRITE
        +NOBLOCKMAP
        +NOGRAVITY
    }

    States {
    Spawn:
        DOOR B -1;
        Stop;
    }
}

class Nacht_Debris : HH_Debris {
    Default {
        //$Category "Nacht"
        //$Title "Boxes"
        Radius 20;
        Height 150;
        +WALLSPRITE
    }

    States {
    Spawn:
        BOXS A -1;
        Stop;
    }
}
