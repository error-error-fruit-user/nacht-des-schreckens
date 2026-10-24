// The perk machines, drawn for nacht by Alexis Dutcher. Their drinks are World at War's bottles,
// rebuilt from the player's own game by doomify.py (the generated Nacht_...Drink classes in
// nacht-waw), found by name when one is bought, so nacht loads without them: then (Nacht des
// Platzhalters) the library's drinks are sold. The perks themselves are Horde Hammer's, their HUD
// icons in graphics/hh/ under the library's names.

// The World at War drink called `name`, if nacht-waw is loaded, or else `otherwise`.
class Nacht_Drinks play {
    static class<HH_Drink> Named(Name name, class<HH_Drink> otherwise) {
        class<HH_Drink> waw = (class<HH_Drink>)(name);
        return waw != null ? waw : otherwise;
    }
}

class Nacht_QuickReviveMachine : HH_QuickReviveMachine {
    override class<HH_Drink> CurrentDrink() {
        return multiplayer
            ? Nacht_Drinks.Named('Nacht_QuickReviveDrink', self.drink)
            : Nacht_Drinks.Named('Nacht_SoloReviveDrink', self.soloDrink);
    }

    States {
    Spawn:
        QKRV A -1;
        Stop;
    }
}

class Nacht_JuggernogMachine : HH_JuggernogMachine {
    override class<HH_Drink> CurrentDrink() {
        return Nacht_Drinks.Named('Nacht_JuggernogDrink', self.drink);
    }

    States {
    Spawn:
        JGNG A -1;
        Stop;
    }
}

class Nacht_SpeedColaMachine : HH_SpeedColaMachine {
    override class<HH_Drink> CurrentDrink() {
        return Nacht_Drinks.Named('Nacht_SpeedColaDrink', self.drink);
    }

    States {
    Spawn:
        SPCA A -1;
        Stop;
    }
}

class Nacht_DoubleTapMachine : HH_DoubleTapMachine {
    override class<HH_Drink> CurrentDrink() {
        return Nacht_Drinks.Named('Nacht_DoubleTapDrink', self.drink);
    }

    States {
    Spawn:
        DBTP A -1;
        Stop;
    }
}

