// World at War's perk machines and drinks. The perks themselves are Horde Hammer's; their HUD icons
// are nacht's, in graphics/hh/ under the library's names.

class Nacht_QuickReviveMachine : HH_QuickReviveMachine {
    Default {
        HH_PerkMachine.Drink "Nacht_QuickReviveDrink";
        HH_QuickReviveMachine.SoloDrink "Nacht_SoloReviveDrink";
    }

    States {
    Spawn:
        QKRV A -1;
        Stop;
    }
}

class Nacht_QuickReviveDrink : HH_QuickReviveDrink {
    States {
    Sprites:
        DQ0R A 0;
        DQ1R A 0;
        DQ2R A 0;
    Spawn:
        QRA0 A -1;
        Stop;
    }
}

class Nacht_SoloReviveDrink : HH_SoloReviveDrink {
    States {
    Sprites:
        DQ0R A 0;
        DQ1R A 0;
        DQ2R A 0;
    Spawn:
        QRA0 A -1;
        Stop;
    }
}

class Nacht_JuggernogMachine : HH_JuggernogMachine {
    Default {
        HH_PerkMachine.Drink "Nacht_JuggernogDrink";
    }

    States {
    Spawn:
        JGNG A -1;
        Stop;
    }
}

class Nacht_JuggernogDrink : HH_JuggernogDrink {
    States {
    Sprites:
        DJ0N A 0;
        DJ1N A 0;
        DJ2N A 0;
    Spawn:
        JGA0 A -1;
        Stop;
    }
}

class Nacht_SpeedColaMachine : HH_SpeedColaMachine {
    Default {
        HH_PerkMachine.Drink "Nacht_SpeedColaDrink";
    }

    States {
    Spawn:
        SPCA A -1;
        Stop;
    }
}

class Nacht_SpeedColaDrink : HH_SpeedColaDrink {
    States {
    Sprites:
        DS0C A 0;
        DS1C A 0;
        DS2C A 0;
    Spawn:
        SCA0 A -1;
        Stop;
    }
}

class Nacht_DoubleTapMachine : HH_DoubleTapMachine {
    Default {
        HH_PerkMachine.Drink "Nacht_DoubleTapDrink";
    }

    States {
    Spawn:
        DBTP A -1;
        Stop;
    }
}

class Nacht_DoubleTapDrink : HH_DoubleTapDrink {
    States {
    Sprites:
        DD0T A 0;
        DD1T A 0;
        DD2T A 0;
    Spawn:
        DTA0 A -1;
        Stop;
    }
}
