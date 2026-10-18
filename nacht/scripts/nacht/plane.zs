// The crashed plane outside (a placeholder red rectangle until it has art and its fire)

class Nacht_Plane : Actor {
    Default {
        //$Category "Nacht"
        //$Title "Plane"
        +SOLID
    }

    States {
    Spawn:
        PLNE A -1;
        Stop;
    }
}
