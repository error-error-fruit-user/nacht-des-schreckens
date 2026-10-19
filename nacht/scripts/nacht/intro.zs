// The intro's look: the title flashing over the camera's flight, then "Doomed Zombies" on black.
// The intro itself (the camera, its path, the skip on the repulse key, the start of round 1) is
// ACS, in acs/nacht.acs; this only draws, and stops once the game has started.

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
    const FLASH_DELAY = 35 * 3;
    const BLACK_SCREEN_DELAY = 35 * 18;
    const TEXT_DELAY = 35 * 5;
    const TEXT_COLOR = Font.CR_RED;

    int ticsSinceStart;
    double alpha;
    Vector2 textOffset;

    clearscope static bool IntroRunning() {
        let rounds = HH_Rounds.Get();
        return rounds != null && !rounds.IsStarted();
    }

    void ChangeTextOffset() {
        self.textOffset = (Random[Nacht_Intro](-1, 1), Random[Nacht_Intro](-1, 1));
    }

    override void WorldTick() {
        if (!Nacht_IntroHandler.IntroRunning()) {
            return;
        }
        ++self.ticsSinceStart;
        if (self.ticsSinceStart < Nacht_IntroHandler.BLACK_SCREEN_DELAY) {
            self.alpha = abs((self.ticsSinceStart % (Nacht_IntroHandler.FLASH_DELAY * 2) - Nacht_IntroHandler.FLASH_DELAY) / double(Nacht_IntroHandler.FLASH_DELAY));
        } else if (self.ticsSinceStart == Nacht_IntroHandler.BLACK_SCREEN_DELAY) {
            self.ChangeTextOffset();
            self.alpha = 0.0;
        } else {
            if (self.ticsSinceStart % 3 == 0) {
                self.ChangeTextOffset();
            }
            self.alpha = min(1.0, (self.ticsSinceStart - Nacht_IntroHandler.BLACK_SCREEN_DELAY) / double(Nacht_IntroHandler.TEXT_DELAY));
        }
    }

    override void RenderOverlay(RenderEvent e) {
        if (!Nacht_IntroHandler.IntroRunning()) {
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
