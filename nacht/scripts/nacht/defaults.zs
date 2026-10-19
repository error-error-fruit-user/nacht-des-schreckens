// Nacht's settings on top of Horde Hammer's defaults (any host can still change the CVars)

class Nacht_Defaults : HH_Defaults {
    override void Fill(HH_SettingsHandler settings) {
        super.Fill(settings);
        // The "Zombies" option: nacht's, or Doom's monsters (the rogues gallery)
        settings.Set("hh_zombie_class", nacht_rogues_gallery? "HH_VariedZombie": "Nacht_Zombie");
        settings.Set("hh_player_speed", "0.5");
        // The intro starts round 1, and nothing of the HUD shows before it
        settings.Set("hh_auto_start", "0");
        settings.Set("hh_hud_before_start", "0");
    }
}
