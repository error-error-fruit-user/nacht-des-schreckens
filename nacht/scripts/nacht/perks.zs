// The perk machines, drawn for nacht by Alexis Dutcher. Their drinks are World at War's bottles,
// rebuilt from the player's own game by doomify.py (the generated <prefix>_...Drink classes); the
// perks themselves are Horde Hammer's, their HUD icons in graphics/hh/ under the library's names.

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

