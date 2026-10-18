// The intro: a camera sways over the map with the title flashing, then round 1 starts. Any player
// can skip it with the repulse key (Q). Horde Hammer's hh_auto_start is off for nacht, so the game
// waits for this.

// Views the intro camera while the intro runs
class Nacht_Intro : Inventory {
    Default {
        Inventory.MaxAmount 1;
        +INVENTORY.UNDROPPABLE
        +INVENTORY.UNTOSSABLE
        +INVENTORY.UNCLEARABLE
    }

    override void AttachToOwner(Actor other) {
        super.AttachToOwner(other);
        let camera = Level.CreateActorIterator(Nacht_IntroHandler.CAMERA_TID).Next();
        if (other.player != null && camera != null) {
            other.player.camera = camera;
        }
    }

    override void DetachFromOwner() {
        if (self.owner != null && self.owner.player != null) {
            self.owner.player.camera = self.owner;
        }
        super.DetachFromOwner();
    }
}

// What the intro camera looks at, drifting about
class Nacht_SwayTarget : Actor {
    const MAX_WIDTH = 10;
    const MAX_HEIGHT = 10;
    const TICS_TILL_CHANGE = 120;

    Vector3 originalPosition;
    Vector3 lastPosition;
    Vector3 targetPosition;
    int ticsSinceChange;

    Default {
        //$Category "Nacht"
        //$Title "Intro Sway Target"
        +NOGRAVITY
        +NOBLOCKMAP
        RenderStyle "None";
    }

    static Vector3 Lerp(Vector3 start, Vector3 end, double percent) {
        return start + percent * (end - start);
    }

    static Vector3 SmoothStep(Vector3 start, Vector3 end, double tics) {
        let percent = tics / Nacht_SwayTarget.TICS_TILL_CHANGE;
        return Nacht_SwayTarget.Lerp(start, end, percent * percent * percent * (percent * (6 * percent - 15) + 10));
    }

    override void BeginPlay() {
        super.BeginPlay();
        self.originalPosition = self.pos;
        self.ChangeTargetPosition();
    }

    override void Tick() {
        if (self.ticsSinceChange == Nacht_SwayTarget.TICS_TILL_CHANGE) {
            self.ticsSinceChange = 0;
            self.ChangeTargetPosition();
        } else {
            ++self.ticsSinceChange;
            self.SetXYZ(Nacht_SwayTarget.SmoothStep(self.lastPosition, self.targetPosition, self.ticsSinceChange));
        }
    }

    void ChangeTargetPosition() {
        self.lastPosition = self.pos;
        self.targetPosition = self.originalPosition + (Random[Nacht_Intro](-Nacht_SwayTarget.MAX_WIDTH, Nacht_SwayTarget.MAX_WIDTH), 0, Random[Nacht_Intro](0, Nacht_SwayTarget.MAX_HEIGHT));
    }

    States {
    Spawn:
        TNT1 A -1;
        Stop;
    }
}

class Nacht_IntroHandler : EventHandler {
    // TIDs in map01
    const CAMERA_TID = 13;
    const MOVER_TID = 20;
    const SWAY_TARGET_TID = 25;
    const ZOMBIE_TID = 116;

    const FLASH_DELAY = 35 * 3;
    const BLACK_SCREEN_DELAY = 35 * 18;
    const TEXT_DELAY = 35 * 5;
    const START_DELAY = 1015;
    const TEXT_COLOR = Font.CR_RED;

    bool done;
    int ticsSinceStart;
    double alpha;
    Vector2 textOffset;

    override void WorldLoaded(WorldEvent e) {
        if (e.IsSaveGame) {
            return;
        }
        let camera = Level.CreateActorIterator(Nacht_IntroHandler.CAMERA_TID).Next();
        if (camera != null) {
            camera.A_StartSound("game/intro_cinematic", CHAN_5, attenuation: ATTN_NONE);
        }
    }

    // (players enter before WorldLoaded runs, so this can't wait for it)
    override void PlayerEntered(PlayerEvent e) {
        if (!self.done && HH_Util.InGame(e.PlayerNumber)) {
            players[e.PlayerNumber].mo.GiveInventory('Nacht_Intro', 1);
        }
    }

    // The repulse key skips the intro
    override void NetworkProcess(ConsoleEvent e) {
        if (e.Name == 'hh_repulse' && !self.done && HH_Util.InGame(e.Player)) {
            self.StartMap();
        }
    }

    static void DestroyAll(int tid) {
        if (tid == 0) {
            return;
        }
        let iterator = Level.CreateActorIterator(tid);
        Actor thing;
        while (thing = iterator.Next()) {
            thing.Destroy();
        }
    }

    // Rain, everyone to their places, round 1; only ever once
    void StartMap() {
        if (self.done) {
            return;
        }
        self.done = true;

        Actor.Spawn('Weather');
        Weather.SetPrecipitationType('BloodRain');

        let camera = Level.CreateActorIterator(Nacht_IntroHandler.CAMERA_TID).Next();
        if (camera != null) {
            camera.A_StopSound(CHAN_5);
        }
        Nacht_IntroHandler.DestroyAll(Nacht_IntroHandler.ZOMBIE_TID);
        Nacht_IntroHandler.DestroyAll(Nacht_IntroHandler.SWAY_TARGET_TID);

        for (let i = 0; i < MAXPLAYERS; ++i) {
            if (HH_Util.InGame(i)) {
                let pawn = players[i].mo;
                pawn.TakeInventory('Nacht_Intro', 1);
                HH_Players.MoveToSpawn(pawn);
            }
        }
        let rounds = HH_Rounds.Get();
        if (rounds != null) {
            rounds.StartGame();
        }
    }

    void ChangeTextOffset() {
        self.textOffset = (Random[Nacht_Intro](-1, 1), Random[Nacht_Intro](-1, 1));
    }

    override void WorldTick() {
        if (self.done) {
            return;
        }
        ++self.ticsSinceStart;
        if (self.ticsSinceStart == 4) {
            let mover = Level.CreateActorIterator(Nacht_IntroHandler.MOVER_TID).Next();
            if (mover != null) {
                mover.Activate(null);
            }
        }
        if (self.ticsSinceStart < Nacht_IntroHandler.BLACK_SCREEN_DELAY) {
            self.alpha = abs((self.ticsSinceStart % (Nacht_IntroHandler.FLASH_DELAY * 2) - Nacht_IntroHandler.FLASH_DELAY) / double(Nacht_IntroHandler.FLASH_DELAY));
        } else if (self.ticsSinceStart == Nacht_IntroHandler.BLACK_SCREEN_DELAY) {
            self.ChangeTextOffset();
            self.alpha = 0.0;
        } else if (self.ticsSinceStart >= Nacht_IntroHandler.START_DELAY) {
            self.StartMap();
        } else {
            if (self.ticsSinceStart % 3 == 0) {
                self.ChangeTextOffset();
            }
            self.alpha = (self.ticsSinceStart - Nacht_IntroHandler.BLACK_SCREEN_DELAY) / double(Nacht_IntroHandler.TEXT_DELAY);
        }
    }

    override void RenderOverlay(RenderEvent e) {
        if (self.done) {
            return;
        }
        if (self.ticsSinceStart < Nacht_IntroHandler.BLACK_SCREEN_DELAY) {
            Screen.Dim("Black", self.alpha, 0, 0, Screen.GetWidth(), Screen.GetHeight());
            return;
        }
        Screen.Dim("Black", 1.0, 0, 0, Screen.GetWidth(), Screen.GetHeight());
        let scale = (3.0, 5.0);
        self.DrawTitle(StringTable.Localize("$NACHT_INTRO_TOP"), 5, 20, scale);
        self.DrawTitle(StringTable.Localize("$NACHT_INTRO_BOTTOM"), 6, 110, scale);
    }

    ui void DrawTitle(String text, int padding, double y, Vector2 scale) {
        let x = 160 - (bigFont.StringWidth(text) + padding) * scale.x / 2 + self.textOffset.x;
        Screen.DrawText(bigFont, Nacht_IntroHandler.TEXT_COLOR, x, y + self.textOffset.y, text,
            DTA_ScaleX, scale.x, DTA_ScaleY, scale.y, DTA_Alpha, self.alpha, DTA_Spacing, 1, DTA_320x200, true);
    }
}
