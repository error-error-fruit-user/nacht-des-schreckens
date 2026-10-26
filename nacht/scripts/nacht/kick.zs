// Nacht's kick: Horde Hammer's (its key, cooldown, hit and push), with nacht's own leg, the
// QKCK frames of NTM's Quick Kick, played as nacht always played them.
class Nacht_Kick : HH_KickItem replaces HH_KickItem {
    States {
    Kick:
        QKCK ABCDE 2;
        QKCK F 2 HH_KickHit;
        QKCK EDCBA 2;
        Stop;
    }
}
