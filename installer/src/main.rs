//! `install-nacht`: installs Nacht des Schreckens with everything it needs, then rebuilds its
//! World at War weapons and sounds with doomify, which it is built with. Run it from a published
//! release folder (`published/releases/`), which has everything it installs beside it:
//!
//! ```text
//! horde-hammer.pk3           the library nacht runs on
//! nacht.pk3                  the map
//! ```
//!
//! The `doomify/**/*.toml` settings are built into it as consts of doomify's types (`const_toml!`,
//! made by `build.rs` from the repository): their data, not their text. It writes them from that
//! data into its artifacts' `doomify/`, which
//! the weapons are built from: a player can rewrite them there, and they are kept until a newer
//! install-nacht brings settings of its own, which replace them.
//!
//! The tools aren't in it. `tdl` and `install-tdl` are taken from beside this program if they are
//! there, else from the workspace's own releases when this program runs from a release folder in
//! one (`../../../tdl/published/releases/`), and otherwise downloaded from the latest release of
//! tdl on GitHub (`tdl.AppImage`/`tdl.exe`, ...). Those downloads can't be checked against a
//! pinned hash, since the latest release isn't known when this is built; they come over HTTPS from
//! the project's own releases.
//!
//! `--locally` (in place) or `--user-wide` (for you, as install-tdl's) says where to
//! install, and one of them is needed: without either, nothing is done. Nothing is
//! installed for everyone, so it never needs root or an administrator, and it won't run as root. The payload goes in that folder: the pk3s, in `wads/` (a pool tdl offers).
//! Everything else is an artifact, in `artifacts/` there (nacht's `published/artifacts/` when this
//! runs in place from its `published/releases/`, or `--artifacts`): tdl with UZDoom and Freedoom 2,
//! doomify's settings in `doomify/`, nacht's sprites in `nacht/` and the built weapons in
//! `nacht-waw/`, Blender (downloaded, checked against its published SHA-256, unless it is installed
//! already) in `blender/`, the song in `songs/`, the install's loadout and its journal. Then it
//! builds the weapons, which needs World at War running with Der Riese loaded unless everything is
//! in doomify's cache (about an hour the first time), and packs them into `wads/nacht-waw.pk3`.
//! Blender's script pulls from the game by running this program again with
//! `--script TOML --out DIR`. Last, it pulls World at War's songs out of the player's game (found
//! in a Steam library, or `--waw`) into `songs/` (`--no-song` leaves them): Lullaby for a Dead
//! Man, The One and nacht's own, Der Riese's Beauty of Annihilation; and sets up the install's
//! loadout with `tdl setup`, tdl knowing them all and nacht's as its song.
//!
//! It is built with installation-groans, the installers' library (the `installation-groans/`
//! submodule): its command line is the `Cli` struct, the question and the journal are the
//! library's, and every run ends with a press of Enter, so what was done can be read first.

use std::{
    ffi::OsString,
    fs,
    io::{self, IsTerminal, Read, Write},
    path::{Path, PathBuf},
    process::{Command, ExitCode},
};

use installation_groans::{Mode, Places, journal, note, say, warn};
use sha2::{Digest, Sha256};

/// The pk3s nacht is played with, in the order they load.
const PK3S: [&str; 2] = ["horde-hammer.pk3", "nacht.pk3"];
/// nacht's keyboard controls, the ini its profiles are given: built in from the repository's
/// `config.ini`, and written into the install's folder once (UZDoom rewrites it on every exit, so
/// the player's settings stay).
const INI: &str = "config.ini";
const CONFIG_INI: &str = include_str!("../../config.ini");
/// Where the tools are released: the latest release of each repository has its programs as
/// assets named like the program, `.AppImage` on Linux and `.exe` on Windows.
const RELEASES: &str = "https://github.com";
const TDL_REPOSITORY: &str = "error-error-fruit-user/tdl";
/// What the installed copy of this project is called.
const NAME: &str = "nacht-des-schreckens";
/// Where in the artifacts doomify's settings go (the repository's `doomify/`).
const DOOMIFY: &str = "doomify";

/// A song of World at War's: pulled from the player's own game into the install's `songs/` (it
/// never comes with the map), for tdl to know; the map's own (`SONG`) is kept as tdl's song.
struct Song {
    title: &'static str,
    /// What it is called in `songs/`.
    file: &'static str,
    /// Where it is in World at War's IWDs, in lowercase (the last IWD with it wins, as in the game).
    inside: &'static str,
    /// What the warning says about it before it is put in, its own for every song.
    warning: &'static str,
}

/// Nacht's song: Der Riese's Beauty of Annihilation.
const SONG: Song = Song {
    title: "Beauty of Annihilation",
    file: "beauty_of_annihilation.wav",
    inside: "sound/stream/music/mission/zombie/mx_beauty.wav",
    warning: "Beauty of Annihilation, Der Riese's song, is heavy metal: it becomes tdl's song, so \
              the splash opens on down-tuned riffs and screaming. Turn your speakers down, or pass \
              --no-song to keep the music you have.",
};

/// World at War's songs, each a map's easter egg: every one is pulled for tdl to know (`J`/`K` on
/// the song in its settings), nacht's (`SONG`) among them. A song a player's game lacks (the
/// map packs bring The One and Beauty of Annihilation) is left out.
const SONGS: [Song; 3] = [
    Song {
        title: "Lullaby for a Dead Man",
        file: "lullaby_for_a_dead_man.wav",
        inside: "sound/stream/music/mission/zombie/mx_lullaby.wav",
        warning: "Lullaby for a Dead Man, Verrückt's song, is pulled too, for tdl to know: it plays \
                  only if you pick it (J/K on the song in tdl's settings).",
    },
    Song {
        title: "The One",
        file: "the_one.wav",
        inside: "sound/stream/music/mission/zombie/mx_the_one.wav",
        warning: "The One, Shi No Numa's song, is pulled too, for tdl to know: it plays only if you \
                  pick it.",
    },
    SONG,
];

/// World at War's folder in a Steam library.
const WORLD_AT_WAR: &str = "steamapps/common/Call of Duty World at War";

/// `doomify/**/*.toml`, as consts of doomify's types, each made by doomify's `const_toml!` from
/// the file `build.rs` read with serde (`DOOMIFY_WEAPONS_COLT_TOML` is a `Weapon`), and the tables
/// `FILES` (each file's text), `WEAPONS`, `SOUNDS` and `CONFIG`, as the repository had them when
/// this was built. To build a TOML of your own in: put it in `doomify/` (the next build picks it
/// up), or by hand, `const MINE: Weapon = const_toml!["doomify/weapons/mine.toml"];` once
/// `build.rs` writes it.
#[allow(dead_code)] // the per-file consts are there to be used when customizing
mod embedded {
    use doomify::{const_toml, types::*};

    include!(concat!(env!("OUT_DIR"), "/embedded.rs"));
}

/// A file to download: where from (the first that works), and what it must be.
struct Download {
    name: &'static str,
    urls: &'static [&'static str],
    size: u64,
    sha256: &'static str,
}

/// Blender 4.2.9 LTS for Linux; doomify needs 4.0 or newer. The hash is the one in the
/// release's `blender-4.2.9.sha256`.
const BLENDER_LINUX: Download = Download {
    name: "blender-4.2.9-linux-x64.tar.xz",
    urls: &[
        "https://download.blender.org/release/Blender4.2/blender-4.2.9-linux-x64.tar.xz",
        "https://mirrors.dotsrc.org/blender/blender-release/Blender4.2/blender-4.2.9-linux-x64.tar.xz",
    ],
    size: 355_259_956,
    sha256: "dfbc127a7d28f9c2175b23bf9d6701b2855f31eedfb391f9a6e60adb24572846",
};
/// Blender 4.2.9 LTS for Windows.
const BLENDER_WINDOWS: Download = Download {
    name: "blender-4.2.9-windows-x64.zip",
    urls: &[
        "https://download.blender.org/release/Blender4.2/blender-4.2.9-windows-x64.zip",
        "https://mirrors.dotsrc.org/blender/blender-release/Blender4.2/blender-4.2.9-windows-x64.zip",
    ],
    size: 386_972_284,
    sha256: "223cd22afc5cab3f8cb43006574f1c962ff9bb9e07418c3f4f2542b7c34899cb",
};

/// World at War's Nacht der Untoten on Doom 2, in tdl
#[installation_groans::cli(
    title = "Nacht des Schreckens",
    folder = "nacht-des-schreckens",
    plan = plan
)]
struct Cli {
    /// Runs install-tdl, which puts tdl in the artifacts
    #[installation_groans::On]
    tdl: bool,
    /// Has install-tdl download UZDoom
    #[installation_groans::On]
    uzdoom: bool,
    /// Has install-tdl download Freedoom 2
    #[installation_groans::On]
    freedoom: bool,
    /// Downloads Blender 4.2.9 LTS into the artifacts, if no Blender 4.0 or newer is installed
    #[installation_groans::On]
    blender: bool,
    /// Rebuilds the weapons from your game with doomify
    #[installation_groans::On]
    doomify: bool,
    /// Pulls World at War's songs for tdl: nacht's (Beauty of Annihilation), which becomes tdl's
    /// song, Lullaby for a Dead Man and The One
    #[installation_groans::On]
    song: bool,
    /// Opens tdl on the install's loadout at the end
    #[installation_groans::On]
    play: bool,
    /// Pulls and renders every weapon again (doomify's force), though they were built and are in
    /// the cache; needs World at War running
    rerender: bool,
    /// Makes nacht a command anywhere in the terminal, opening tdl on the install's loadout
    command: bool,
    /// World at War's folder, if it isn't in a Steam library this can find
    waw: Option<PathBuf>,
    /// The Blender doomify renders with, instead of finding or downloading one
    #[installation_groans::Flag("blender")]
    blender_path: Option<PathBuf>,
}

#[installation_groans::location(Cli)]
struct Location;

/// What went wrong, for the user.
type Outcome<T> = Result<T, String>;

fn main() -> ExitCode {
    // 🎣 Blender's script pulls what a TOML names from the game through this program
    let args: Vec<OsString> = std::env::args_os().collect();
    if args.get(1).is_some_and(|arg| arg == "--script") {
        return pull_for_blender(&args[1..]);
    }
    installation_groans::run(|terminal| {
        let mut cli = Cli::new();
        let Some(location) = installation_groans::prompt_user(terminal, &mut cli) else {
            return;
        };
        if let Some(pk3) = PK3S.iter().find(|pk3| !location.here.join(pk3).is_file()) {
            installation_groans::fail(&format!(
                "{pk3} isn't next to this program, in {}: run it from the published folder",
                location.here.display()
            ));
            return;
        }
        location.install(terminal, &cli);
        if let Err(problem) = install(&location, &cli) {
            installation_groans::fail(&problem);
        }
    });
}

/// `--script TOML --out DIR [--pid N]`, run by doomify's Blender script: pulls what the TOML names
/// from the running game into DIR.
fn pull_for_blender(args: &[OsString]) -> ExitCode {
    let (mut script, mut out, mut pid) = (None, None, None);
    let mut args = args.iter();
    while let Some(arg) = args.next() {
        match arg.to_str() {
            Some("--script") => script = args.next().map(PathBuf::from),
            Some("--out") => out = args.next().map(PathBuf::from),
            Some("--pid") => pid = args.next().and_then(|n| n.to_str()?.parse().ok()),
            _ => {}
        }
    }
    let (Some(script), Some(out)) = (script, out) else {
        eprintln!("--script needs a TOML and --out DIR");
        return ExitCode::FAILURE;
    };
    match doomify::script::run(&script, &out, pid) {
        Ok(()) => ExitCode::SUCCESS,
        Err(problem) => {
            eprintln!("{problem:#}");
            ExitCode::FAILURE
        }
    }
}

/// The plan's lines for nacht's parts, under the warning before the one question.
fn plan(cli: &Cli, places: &Places) -> Vec<String> {
    let mut lines = vec![
        format!(
            "  - puts horde-hammer.pk3 and nacht.pk3, the payload, in {}, and {INI} (nacht's controls, the profiles' ini) in {}",
            places.dir.join("wads").display(),
            places.dir.display()
        ),
        "  - puts doomify's settings in the artifacts (the weapons' TOMLs, yours to rewrite; a newer install-nacht's replace them), with the built weapons and the loadout".into(),
    ];
    if cli.tdl {
        let downloads: Vec<&str> = [("UZDoom", cli.uzdoom), ("Freedoom 2", cli.freedoom)]
            .into_iter()
            .filter_map(|(name, wanted)| wanted.then_some(name))
            .collect();
        lines.push(format!(
            "  - runs install-tdl, which puts tdl in the artifacts{}{}",
            match places.mode {
                Mode::InPlace => "",
                Mode::User => " with the tdl command on the PATH",
            },
            if downloads.is_empty() {
                String::new()
            } else {
                format!(" and downloads {}", downloads.join(" and "))
            }
        ));
    }
    match &cli.blender_path {
        Some(blender) => lines.push(format!("  - renders with the Blender at {}", blender.display())),
        None if cli.blender => lines.push(
            "  - downloads Blender 4.2.9 LTS into the artifacts, checked against its hash, if no Blender 4.0 or newer is installed"
                .into(),
        ),
        None => {}
    }
    let steps = journal::Steps::open(&places.artifacts, cli.reinstall);
    if cli.song && !steps.done("song") {
        lines.push(format!("  - {}", SONG.warning));
    }
    if cli.song && !steps.done("songs") {
        for song in SONGS.iter().filter(|song| song.title != SONG.title) {
            lines.push(format!("  - {}", song.warning));
        }
    }
    if cli.doomify && cli.rerender {
        lines.push(
            "  - pulls and renders every weapon again from World at War (--rerender), though they are built and in the cache: an hour or more"
                .into(),
        );
    }
    if cli.doomify {
        lines.push(
            "  - rebuilds the weapons from your game with doomify, if World at War is running or everything is in doomify's cache (about an hour the first time), into wads/nacht-waw.pk3"
                .into(),
        );
    }
    if let Some(waw) = &cli.waw {
        lines.push(format!("  - looks for World at War in {}", waw.display()));
    }
    if cli.command {
        lines.push(format!(
            "  - makes nacht a command in your terminal, which opens tdl on the install's loadout ({})",
            command_place()
        ));
    }
    lines.push(format!(
        "  - sets up the install's loadout{}",
        if cli.play { " and opens tdl on it" } else { "" }
    ));
    lines
}

/// Everything after what the library did (the question, the folders, the journal and its
/// beginning): tdl, the pk3s, doomify's settings, Blender, the weapons, the songs and the loadout.
fn install(location: &Location, cli: &Cli) -> Outcome<()> {
    let (here, dir, art) = (&location.here, &location.dir, &location.places.artifacts);
    let mode = location.mode;
    note!(
        "leaving out: tdl {}, uzdoom {}, freedoom {}, blender {}, doomify {}",
        !cli.tdl,
        !cli.uzdoom,
        !cli.freedoom,
        !cli.blender,
        !cli.doomify,
    );

    let mut steps = journal::Steps::open(art, cli.reinstall);
    let scratch = Scratch::new();
    let tdl_name = if cfg!(windows) { "tdl.exe" } else { "tdl" };
    // 🔁 done again when the tdl it would take (beside this, or the workspace's release) is
    // another than the one it took, so a newer tdl reaches an install
    let local: Vec<PathBuf> = ["tdl", "install-tdl"]
        .iter()
        .filter_map(|name| beside(here, name).or_else(|| from_workspace(here, "tdl", name)))
        .collect();
    let tdl_step = if local.is_empty() {
        "tdl".to_string()
    } else {
        format!("tdl {}", fingerprint(&local))
    };
    if !!cli.tdl {
        if steps.done(&tdl_step) && art.join(tdl_name).is_file() {
            steps.skip("tdl", &art.display().to_string());
        } else {
            // the install's loadout first, so tdl's own setup (its Freedoom profile) goes in it too
            merge_setup(art, |table| {
                set_loadout(table, art, mode == Mode::InPlace)
            })?;
            install_tdl(here, art, mode, cli, &scratch)?;
            steps.finish(&tdl_step);
        }
    }
    journal::section("install");
    place_files(here, dir)?;
    place_ini(dir, cli.reinstall)?;
    let settings = art.join(DOOMIFY);
    place_settings(&settings, &mut steps)?;
    let blender = match &cli.blender_path {
        Some(path) => Some(path.clone()),
        None if !cli.blender => find_blender(art),
        None => ensure_blender(art)?,
    };
    note!("blender: {:?}", blender);
    let built = dir.join("wads").join("nacht-waw.pk3");
    // 🔫 built again when doomify's source or the installed settings changed (doomify's cache
    // keeps what they didn't touch: only what a changed part of its render script draws, or a
    // rewritten TOML, is rendered again)
    let weapons = format!("weapons {}", weapons_mark(&settings));
    if !!cli.doomify && !cli.rerender && steps.done(&weapons) && built.is_file() {
        journal::section("weapons");
        steps.skip("nacht-waw.pk3", &built.display().to_string());
    } else if !!cli.doomify
        && build_weapons(
            here,
            art,
            &settings,
            &built,
            blender.as_deref(),
            cli.rerender,
        )
    {
        steps.finish(&weapons);
    }
    // 🎵 World at War's songs are pulled once for tdl to know, and nacht's is made tdl's song once:
    // a song picked since then is left alone
    let (song, songs) = if !cli.song {
        (None, Vec::new())
    } else {
        journal::section("song");
        let make_song = !steps.done("song");
        let know = !steps.done("songs");
        if !make_song {
            steps.skip(SONG.title, "tdl's song, picked once");
        }
        if know {
            note!("World at War's songs are to be pulled for tdl to know");
        } else {
            steps.skip("World at War's songs", "the songs tdl knows");
        }
        let wanted: Vec<&Song> = SONGS
            .iter()
            .filter(|song| know || (make_song && song.title == SONG.title))
            .collect();
        let pulled = pull_songs(&wanted, art, cli.waw.as_deref());
        let song = pulled
            .iter()
            .find(|(song, _)| make_song && song.title == SONG.title)
            .map(|(_, path)| path.clone());
        let songs = if know {
            pulled.into_iter().map(|(_, path)| path).collect()
        } else {
            Vec::new()
        };
        (song, songs)
    };
    let tdl = set_up_loadout(
        dir,
        art,
        song.as_deref(),
        &songs,
        mode == Mode::InPlace,
        &mut steps,
    );
    if let Some(tdl) = &tdl {
        let mut command = vec![tdl.display().to_string(), "--session".into()];
        command.extend([
            "--loadout".into(),
            art.join("loadout").display().to_string(),
        ]);
        command.extend(["--wads".into(), dir.join("wads").display().to_string()]);
        journal::shortcut(
            "Nacht des Schreckens",
            NAME,
            &command,
            "World at War's Nacht der Untoten on Doom 2, in tdl",
            cli.desktop_shortcut,
            cli.menu_entry,
        );
        if cli.command {
            match make_command(art, &command) {
                Ok(told) => journal::tell(
                    "copy",
                    &[("what", "The nacht command"), ("place", &command_place())],
                    &told,
                ),
                Err(problem) => warn!("The nacht command wasn't made: {problem}"),
            }
        }
    }
    if let Some(tdl) = tdl {
        let (dir, art, play) = (dir.clone(), art.clone(), cli.play);
        installation_groans::then(move || self::play(&tdl, &dir, &art, !play));
    }
    Ok(())
}

/// The install's own loadout (`<art>/loadout`, in the artifacts): nacht's part of tdl's own
/// `setup.toml` there (beside install-tdl's) makes Nacht des Platzhalters in it, and Nacht des
/// Schreckens once `nacht-waw.pk3` is in the wad pool (`<dir>/wads`), and the tdl the install put
/// in `art` (or the one on the PATH) runs `tdl setup` on it. Returns that tdl, or
/// `None` (said) when there is none or the setup failed. Both profiles get `<dir>/config.ini`.
fn set_up_loadout(
    dir: &Path,
    art: &Path,
    song: Option<&Path>,
    songs: &[PathBuf],
    own: bool,
    steps: &mut journal::Steps,
) -> Option<PathBuf> {
    let name = if cfg!(windows) { "tdl.exe" } else { "tdl" };
    let tdl = Some(art.join(name))
        .filter(|tdl| tdl.is_file())
        .or_else(|| {
            std::env::var_os("PATH").and_then(|path| {
                std::env::split_paths(&path)
                    .map(|folder| folder.join(name))
                    .find(|tdl| tdl.is_file())
            })
        });
    let Some(tdl) = tdl else {
        warn!(
            "There is no tdl to set up the profiles with (install-tdl puts one in {})",
            art.display()
        );
        return None;
    };
    let wads = dir.join("wads");
    // 🧾 a profile is set up again only when its pk3s changed (so tdl takes their new hashes), the
    // song only when it was just pulled
    let platzhalters = [wads.join("horde-hammer.pk3"), wads.join("nacht.pk3")];
    let schreckens = [
        wads.join("horde-hammer.pk3"),
        wads.join("nacht.pk3"),
        wads.join("nacht-waw.pk3"),
    ];
    // the built-in ini, not the copy UZDoom rewrites, so a new one sets the profiles up again
    let marked = |wads: &[PathBuf]| format!("{} {}", fingerprint(wads), fnv(CONFIG_INI.as_bytes()));
    let platzhalters_step = format!("profile Nacht des Platzhalters {}", marked(&platzhalters));
    let schreckens_step = format!("profile Nacht des Schreckens {}", marked(&schreckens));
    let ini = dir.join(INI).display().to_string();
    let mut setting_up = Vec::new();
    let mut profiles = vec![("Nacht des Platzhalters", &platzhalters[..], None)];
    if !steps.done(&platzhalters_step) {
        setting_up.push(platzhalters_step.clone());
    }
    if schreckens[2].is_file() {
        profiles.push(("Nacht des Schreckens", &schreckens[..], Some(1)));
        if !steps.done(&schreckens_step) {
            setting_up.push(schreckens_step.clone());
        }
    }
    if song.is_some() {
        setting_up.push("song".to_string());
    }
    if !songs.is_empty() {
        setting_up.push("songs".to_string());
    }
    // an install --locally switched to settings of its own once, an earlier one's too
    if own && !steps.done("own settings") {
        setting_up.push("own settings".to_string());
    }
    journal::section("setup");
    // 🧹 nacht's own setup TOML of before, now a part of tdl's
    let _ = fs::remove_file(art.join("setup-nacht.toml"));
    // 🧾 nacht's part of tdl's own setup.toml (install-tdl's part kept): the loadout, its profiles
    // (replaced by name) and the songs tdl knows; the song only for this run, so a pick in tdl stays
    let set_profiles = |table: &mut toml::Table| {
        let list = table
            .entry("profiles")
            .or_insert_with(|| toml::Value::Array(Vec::new()));
        if let Some(list) = list.as_array_mut() {
            for (name, wads, place) in &profiles {
                let mut profile = toml::Table::new();
                profile.insert("name".into(), (*name).into());
                if let Some(place) = place {
                    profile.insert("place".into(), toml::Value::Integer(*place));
                }
                profile.insert(
                    "wads".into(),
                    toml::Value::Array(
                        wads.iter()
                            .map(|wad| wad.display().to_string().into())
                            .collect(),
                    ),
                );
                profile.insert("ini".into(), ini.clone().into());
                let profile = toml::Value::Table(profile);
                match list
                    .iter_mut()
                    .find(|kept| kept.get("name").and_then(toml::Value::as_str) == Some(*name))
                {
                    Some(kept) => *kept = profile,
                    None => list.push(profile),
                }
            }
        }
    };
    let written = merge_setup(art, |table| {
        set_loadout(table, art, own);
        // the World at War songs the install has, kept listed so the file is whole
        let have: Vec<PathBuf> = SONGS
            .iter()
            .map(|song| art.join("songs").join(song.file))
            .filter(|path| path.is_file())
            .chain(songs.iter().cloned())
            .collect();
        if !have.is_empty() {
            let known = table
                .entry("songs")
                .or_insert_with(|| toml::Value::Array(Vec::new()));
            if let Some(known) = known.as_array_mut() {
                for song in &have {
                    let song = toml::Value::String(song.display().to_string());
                    if !known.contains(&song) {
                        known.push(song);
                    }
                }
            }
        }
        if let Some(song) = song {
            table.insert("song".into(), song.display().to_string().into());
        }
        set_profiles(table);
    });
    let setup = match written {
        Ok(setup) => setup,
        Err(problem) => {
            warn!("{problem}");
            return None;
        }
    };
    // written every run, so tdl's setup.toml always holds nacht's part; run only when it changed
    if setting_up.is_empty() {
        steps.skip(
            "The install's loadout",
            &art.join("loadout").display().to_string(),
        );
        return Some(tdl);
    }
    let command = format!("tdl setup {}", setup.display());
    let ran = journal::run(Command::new(&tdl).arg("setup").arg(&setup), &command);
    if song.is_some()
        && let Err(problem) = merge_setup(art, |table| {
            table.remove("song");
        })
    {
        warn!("{problem}");
    }
    match ran {
        Ok(status) if status.success() => {
            for step in setting_up {
                steps.finish(&step);
            }
            Some(tdl)
        }
        Ok(status) => {
            warn!("{command} failed ({status})");
            None
        }
        Err(error) => {
            warn!("Couldn't run {}: {error}", tdl.display());
            None
        }
    }
}

/// The install's own loadout in a setup TOML, which tdl doesn't open every time; with `own` (an
/// install `--locally`), with settings of its own (its settings.rite), so nothing the install keeps
/// (UZDoom, the base wad, the songs) touches tdl's global settings.
fn set_loadout(table: &mut toml::Table, art: &Path, own: bool) {
    table.insert(
        "loadout".into(),
        art.join("loadout").display().to_string().into(),
    );
    table.insert("remember_loadout".into(), false.into());
    if own {
        table.insert("own_settings".into(), true.into());
    } else {
        table.remove("own_settings");
    }
}

/// Changes tdl's own `setup.toml` in `art` (the one install-tdl writes, its part kept) with
/// `change`, writing it back under tdl's header. `Err` if it is there and isn't TOML, which is
/// never written over.
fn merge_setup(art: &Path, change: impl FnOnce(&mut toml::Table)) -> Outcome<PathBuf> {
    let path = art.join("setup.toml");
    let mut table = match fs::read_to_string(&path) {
        Ok(text) => text.parse::<toml::Table>().map_err(|error| {
            format!(
                "{} is there and isn't TOML, so it is left alone: {error}",
                path.display()
            )
        })?,
        Err(_) => toml::Table::new(),
    };
    change(&mut table);
    let text = format!(
        "# What tdl keeps, with no windows: `tdl setup` reads this (see tdl setup --help).\n\
         # Paths are relative to this folder. install-tdl and install-nacht keep their parts in it.\n{}",
        toml::to_string(&table).map_err(|error| error.to_string())?
    );
    write_text(&path, &text)?;
    Ok(path)
}

/// A short mark of what `files` hold (an FNV-1a hash of their bytes), so a step done with them is
/// done again when they change.
fn fingerprint(files: &[PathBuf]) -> String {
    let mut hash: u64 = 0xcbf2_9ce4_8422_2325;
    for file in files {
        for byte in fs::read(file).unwrap_or_default() {
            hash = (hash ^ byte as u64).wrapping_mul(0x100_0000_01b3);
        }
        hash = (hash ^ 0xff).wrapping_mul(0x100_0000_01b3);
    }
    format!("{hash:016x}")
}

/// The mark of what builds nacht-waw: doomify's own source (`FINGERPRINT`) and the settings in
/// `settings` the weapons are built from (a player's rewritten ones among them).
fn weapons_mark(settings: &Path) -> String {
    let mut files = Vec::new();
    files_under(settings, &mut files);
    files.sort();
    format!("{} {}", doomify::FINGERPRINT, fingerprint(&files))
}

/// Every file under `folder`.
fn files_under(folder: &Path, found: &mut Vec<PathBuf>) {
    for entry in fs::read_dir(folder).into_iter().flatten().flatten() {
        let path = entry.path();
        if path.is_dir() {
            files_under(&path, found);
        } else {
            found.push(path);
        }
    }
}

/// What starts every TOML the install writes.
const WRITTEN: &str = "# Written by install-nacht from the settings built into it: rewrite it to build your own\n\
                       # weapons (kept until a newer install-nacht brings other settings, which replace it).\n";

/// doomify's settings built in, as the install writes them (from their data, which is all that is
/// built in): where each goes in the settings folder, and its text.
fn built_settings() -> Vec<(String, String)> {
    let written =
        |data: Result<String, toml::ser::Error>| format!("{WRITTEN}{}", data.unwrap_or_default());
    let mut settings = vec![(
        "doomify.toml".to_string(),
        written(toml::to_string(&embedded::CONFIG)),
    )];
    for (id, weapon) in embedded::WEAPONS {
        settings.push((
            format!("weapons/{id}.toml"),
            written(toml::to_string(weapon)),
        ));
    }
    for (id, set) in embedded::SOUNDS {
        settings.push((format!("sounds/{id}.toml"), written(toml::to_string(set))));
    }
    settings
}

/// Puts doomify's settings, built into this from the repository's `doomify/`, in `settings`,
/// which the weapons are built from. A player may rewrite them there, and they are kept (said
/// so) until this is an install-nacht whose settings differ from the ones put there last, a newer
/// release's, which replace them (`--reinstall` too).
fn place_settings(settings: &Path, steps: &mut journal::Steps) -> Outcome<()> {
    let built = built_settings();
    let texts: Vec<u8> = built
        .iter()
        .flat_map(|(place, text)| [place.as_bytes(), text.as_bytes()])
        .flatten()
        .copied()
        .collect();
    let step = format!("settings {}", fnv(&texts));
    let rewritten: Vec<&str> = built
        .iter()
        .map(|(place, _)| place.as_str())
        .filter(|place| !same_as_built(settings, place))
        .collect();
    if steps.done(&step) {
        if rewritten.is_empty() {
            steps.skip("doomify's settings", &settings.display().to_string());
        } else {
            say!(
                "Your settings in {} are kept, and the weapons are built from them: {}",
                settings.display(),
                rewritten.join(", ")
            );
        }
        return Ok(());
    }
    let replaced = !rewritten.is_empty() && settings.join("doomify.toml").is_file();
    for (place, text) in &built {
        write_text(&settings.join(place), text)?;
    }
    if replaced {
        say!(
            "This install-nacht's settings replace the ones in {} that differ: {}",
            settings.display(),
            rewritten.join(", ")
        );
    }
    journal::tell(
        "copy",
        &[
            ("what", "doomify's settings"),
            ("place", &settings.display().to_string()),
        ],
        &format!("doomify's settings: {}", settings.display()),
    );
    steps.finish(&step);
    Ok(())
}

/// Whether the installed `place` (`weapons/colt.toml`) in `settings` reads as the built-in
/// settings, as doomify reads it (comments and layout aside).
fn same_as_built(settings: &Path, place: &str) -> bool {
    let Ok(text) = fs::read_to_string(settings.join(place)) else {
        return false;
    };
    let id = Path::new(place)
        .file_stem()
        .and_then(|stem| stem.to_str())
        .unwrap_or_default();
    if place.starts_with("weapons/") {
        embedded::WEAPONS.iter().any(|(built_id, built)| {
            *built_id == id
                && toml::from_str::<doomify::types::Weapon>(&text)
                    .ok()
                    .as_ref()
                    == Some(built)
        })
    } else if place.starts_with("sounds/") {
        embedded::SOUNDS.iter().any(|(built_id, built)| {
            *built_id == id
                && toml::from_str::<doomify::types::SoundSet>(&text)
                    .ok()
                    .as_ref()
                    == Some(built)
        })
    } else {
        toml::from_str::<doomify::types::Config>(&text).ok() == Some(embedded::CONFIG)
    }
}

/// The same mark of `bytes` alone.
fn fnv(bytes: &[u8]) -> String {
    let hash = bytes.iter().fold(0xcbf2_9ce4_8422_2325_u64, |hash, byte| {
        (hash ^ *byte as u64).wrapping_mul(0x100_0000_01b3)
    });
    format!("{hash:016x}")
}

/// Pulls `songs` out of the player's World at War (`waw`, or the one in a Steam library) into
/// `<dir>/songs/` (their warnings were in the plan). Returns those it pulled and where each is;
/// a missing game, or a song the game lacks, is said.
fn pull_songs<'a>(songs: &[&'a Song], dir: &Path, waw: Option<&Path>) -> Vec<(&'a Song, PathBuf)> {
    if songs.is_empty() {
        return Vec::new();
    }
    for song in songs {
        note!("{}", song.warning);
    }
    let Some(main) = world_at_war(waw) else {
        say!(
            "World at War wasn't found, so its songs aren't pulled for tdl (--waw DIR says where it is)"
        );
        return Vec::new();
    };
    journal::tell(
        "found",
        &[
            ("what", "World at War"),
            ("place", &main.display().to_string()),
        ],
        &format!("World at War: {}", main.display()),
    );
    let mut pulled = Vec::new();
    for song in songs {
        let to = dir.join("songs").join(song.file);
        match pull(song, &main, &to) {
            Ok(true) => {
                journal::tell(
                    "copy",
                    &[("what", song.title), ("place", &to.display().to_string())],
                    &format!("{}: {}", song.title, to.display()),
                );
                pulled.push((*song, to));
            }
            Ok(false) => say!(
                "{} isn't in World at War's IWDs in {} (its map pack isn't installed?)",
                song.title,
                main.display()
            ),
            Err(problem) => warn!("Couldn't pull {}: {problem}", song.title),
        }
    }
    pulled
}

/// Copies `song` from the last of `main`'s IWDs that has it to `to`. `false` if none has it.
fn pull(song: &Song, main: &Path, to: &Path) -> Outcome<bool> {
    let problem =
        |path: &Path, error: &dyn std::fmt::Display| format!("{}: {error}", path.display());
    let mut iwds: Vec<PathBuf> = fs::read_dir(main)
        .map_err(|error| problem(main, &error))?
        .flatten()
        .map(|entry| entry.path())
        .filter(|path| iwd_number(path).is_some())
        .collect();
    // 🔢 the game reads them in order, and a later one overrides an earlier one
    iwds.sort_by_key(|path| iwd_number(path));
    for iwd in iwds.iter().rev() {
        let file = fs::File::open(iwd).map_err(|error| problem(iwd, &error))?;
        let mut archive = zip::ZipArchive::new(file).map_err(|error| problem(iwd, &error))?;
        let Some(name) = archive
            .file_names()
            .find(|name| name.eq_ignore_ascii_case(song.inside))
            .map(str::to_string)
        else {
            continue;
        };
        let mut entry = archive
            .by_name(&name)
            .map_err(|error| problem(iwd, &error))?;
        if fs::metadata(to).is_ok_and(|kept| kept.len() == entry.size()) {
            note!("{} is in {} already", song.title, to.display());
            return Ok(true);
        }
        let mut bytes = Vec::with_capacity(entry.size() as usize);
        entry
            .read_to_end(&mut bytes)
            .map_err(|error| problem(iwd, &error))?;
        let folder = to.parent().unwrap_or(Path::new("."));
        fs::create_dir_all(folder).map_err(|error| problem(folder, &error))?;
        let part = to.with_extension("part");
        fs::write(&part, &bytes).map_err(|error| problem(&part, &error))?;
        fs::rename(&part, to).map_err(|error| problem(to, &error))?;
        note!("pulled {name} from {} into {}", iwd.display(), to.display());
        return Ok(true);
    }
    Ok(false)
}

/// `12` for `iw_12.iwd`; `None` for anything else.
fn iwd_number(path: &Path) -> Option<u32> {
    let name = path.file_name()?.to_str()?.to_ascii_lowercase();
    name.strip_prefix("iw_")?.strip_suffix(".iwd")?.parse().ok()
}

/// World at War's `main` folder: in `given` (the game's folder or its `main`), or else in one of
/// the Steam libraries on this machine.
fn world_at_war(given: Option<&Path>) -> Option<PathBuf> {
    let main_of = |folder: &Path| {
        [folder.join("main"), folder.to_path_buf()]
            .into_iter()
            .find(|main| main.join("iw_00.iwd").is_file())
    };
    if let Some(given) = given {
        return main_of(given);
    }
    let var = |name: &str| std::env::var_os(name).map(PathBuf::from);
    let roots: Vec<PathBuf> = if cfg!(windows) {
        ["ProgramFiles(x86)", "ProgramFiles"]
            .iter()
            .filter_map(|name| var(name))
            .map(|folder| folder.join("Steam"))
            .collect()
    } else {
        let home = var("HOME").unwrap_or_default();
        [
            ".steam/steam",
            ".steam/debian-installation",
            ".local/share/Steam",
            ".var/app/com.valvesoftware.Steam/.local/share/Steam",
        ]
        .iter()
        .map(|root| home.join(root))
        .collect()
    };
    // 📚 every library a Steam knows is in its libraryfolders.vdf, as "path" lines
    let mut libraries = Vec::new();
    for root in roots.iter().filter(|root| root.is_dir()) {
        libraries.push(root.clone());
        let vdf = fs::read_to_string(root.join("steamapps/libraryfolders.vdf")).unwrap_or_default();
        for line in vdf.lines() {
            let mut parts = line.split('"').filter(|part| !part.trim().is_empty());
            if parts.next() == Some("path")
                && let Some(path) = parts.next()
            {
                libraries.push(PathBuf::from(path.replace("\\\\", "\\")));
            }
        }
    }
    libraries
        .iter()
        .find_map(|library| main_of(&library.join(WORLD_AT_WAR)))
}

/// Opens `tdl` on the install's loadout, with no question: for this run only (`--session`, so the
/// loadout tdl opens otherwise stays as it was) and with the install's wads as the wad pool. Only
/// when there is a terminal for it and `--no-play` wasn't given; otherwise says how to.
fn play(tdl: &Path, dir: &Path, art: &Path, no_play: bool) {
    let loadout = art.join("loadout");
    // 🗝️ --session asks nothing about what is passed; --wads gives the wad pool, so the wads beside
    // tdl aren't asked about either
    let wads = dir.join("wads");
    let command = format!(
        "{} --session --loadout {} --wads {}",
        tdl.display(),
        loadout.display(),
        wads.display()
    );
    journal::section("play");
    if no_play || !io::stdin().is_terminal() || !io::stdout().is_terminal() {
        journal::tell(
            "ready",
            &[("what", "Nacht des Schreckens"), ("command", &command)],
            &format!("To play: {command}"),
        );
        return;
    }
    journal::tell(
        "run",
        &[("command", &command)],
        &format!("Opening tdl: {command}"),
    );
    let opened = Command::new(tdl)
        .arg("--session")
        .arg("--loadout")
        .arg(&loadout)
        .arg("--wads")
        .arg(&wads)
        .status();
    if let Err(error) = opened {
        warn!("Couldn't run {}: {error}", tdl.display());
        say!("To play: {command}");
    }
}

/// What a release calls the program `name` on this system.
fn asset(name: &str) -> String {
    format!("{name}{}", if cfg!(windows) { ".exe" } else { ".AppImage" })
}

/// Gets the program `name` into `to`: copied from beside this program (as `name`, `name.exe` or
/// `name.AppImage`), or from the workspace's own release of `repository` (see [`from_workspace`]),
/// or else downloaded from its latest release on GitHub.
fn get_tool(
    here: &Path,
    name: &str,
    repository: &str,
    to: &Path,
    scratch: &Scratch,
) -> Outcome<()> {
    let project = repository.rsplit('/').next().unwrap_or(repository);
    if let Some(beside) = beside(here, name) {
        note!("{name}: the one beside this program, {}", beside.display());
        copy_whole(&beside, to)?;
    } else if let Some(built) = from_workspace(here, project, name) {
        journal::tell(
            "found",
            &[("what", name), ("place", &built.display().to_string())],
            &format!("{name}: {}", built.display()),
        );
        note!("{name}: the workspace's release, {}", built.display());
        copy_whole(&built, to)?;
    } else {
        let url = format!(
            "{RELEASES}/{repository}/releases/latest/download/{}",
            asset(name)
        );
        journal::tell(
            "download",
            &[("name", name), ("size", "some unknown amount")],
            &format!("{name} isn't next to this program, so it is downloaded: {url}"),
        );
        let file = fetch_unpinned(&url, &asset(name), scratch)?;
        copy_whole(&file, to)?;
    }
    make_executable(to)?;
    note!("{name} is at {}", to.display());
    Ok(())
}

/// The program `name` beside this one.
fn beside(here: &Path, name: &str) -> Option<PathBuf> {
    [name.to_string(), format!("{name}.exe"), asset(name)]
        .iter()
        .map(|n| here.join(n))
        .find(|path| path.is_file())
}

/// The workspace's own release of the program `name`, when this program runs from a project's
/// release folder in a workspace that has `project` too: from
/// `<workspace>/<this project>/published/releases/`, that is
/// `<workspace>/<project>/published/releases/<name>.AppImage` (`.exe` on Windows), so what the
/// workspace built is used before anything is downloaded.
fn from_workspace(here: &Path, project: &str, name: &str) -> Option<PathBuf> {
    let published = here.parent()?;
    if here.file_name()? != "releases" || published.file_name()? != "published" {
        return None;
    }
    let workspace = published.parent()?.parent()?;
    let path = workspace
        .join(project)
        .join("published")
        .join("releases")
        .join(asset(name));
    path.is_file().then_some(path)
}

/// Runs the `install-tdl` that puts tdl, UZDoom and Freedoom 2 in `dir` (the artifacts, which
/// all install-tdl makes goes in too). It and tdl are staged side by side first, and install-tdl
/// installs the tdl beside it (`--from`).
fn install_tdl(here: &Path, dir: &Path, mode: Mode, cli: &Cli, scratch: &Scratch) -> Outcome<()> {
    let stage = scratch.dir()?.join("tools");
    let installer = stage.join(asset("install-tdl"));
    let tdl = stage.join(asset("tdl"));
    get_tool(here, "install-tdl", TDL_REPOSITORY, &installer, scratch)?;
    get_tool(here, "tdl", TDL_REPOSITORY, &tdl, scratch)?;
    journal::section("download");
    let mut command = Command::new(&installer);
    // 📦 the installer is its own AppImage, if it is one
    command.env_remove("APPIMAGE");
    // 🗃️ tdl is an artifact here, and so is all install-tdl makes beside it; it speaks for itself,
    // in this one's voice and journal, and opens nothing (the loadout is nacht's to open)
    journal::child(&mut command, true);
    command
        .arg("--accept")
        .arg(mode.flag())
        .arg("--from")
        .arg(&stage)
        .arg("--dir")
        .arg(dir)
        .arg("--artifacts")
        .arg(dir)
        .arg("--no-play");
    for (flag, on) in [
        ("--computer-speak", cli.computer_speak),
        ("--no-uzdoom", !cli.uzdoom),
        ("--no-freedoom", !cli.freedoom),
        ("--reinstall", cli.reinstall),
    ] {
        if on {
            command.arg(flag);
        }
    }
    note!("running {command:?}");
    let status = command
        .status()
        .map_err(|error| format!("couldn't run {}: {error}", installer.display()))?;
    note!("install-tdl ended: {status}");
    if status.success() {
        Ok(())
    } else {
        Err(format!("install-tdl failed ({status})"))
    }
}

/// Writes the built-in `config.ini` into `dir`, unless it is there already (UZDoom keeps the
/// player's settings in it) and this isn't a reinstall.
fn place_ini(dir: &Path, reinstall: bool) -> Outcome<()> {
    let to = dir.join(INI);
    if to.is_file() && !reinstall {
        journal::tell(
            "skip",
            &[("what", INI), ("place", &to.display().to_string())],
            &format!(
                "{INI}: {} is there already, with your settings",
                to.display()
            ),
        );
        return Ok(());
    }
    write_text(&to, CONFIG_INI)?;
    journal::tell(
        "copy",
        &[("what", INI), ("place", &dir.display().to_string())],
        &format!("{INI}: {}", to.display()),
    );
    Ok(())
}

/// Puts the pk3s in `<dir>/wads/`.
fn place_files(here: &Path, dir: &Path) -> Outcome<()> {
    let wads = dir.join("wads");
    for pk3 in PK3S {
        copy_whole(&here.join(pk3), &wads.join(pk3))?;
        journal::tell(
            "copy",
            &[("what", pk3), ("place", &wads.display().to_string())],
            &format!("{pk3}: {}", wads.join(pk3).display()),
        );
    }
    Ok(())
}

/// Takes the `sprites/` folder out of the pk3 into `folder`, replacing what was there.
fn unpack_sprites(pk3: &Path, folder: &Path) -> Outcome<()> {
    let problem = |error: &dyn std::fmt::Display| format!("{}: {error}", pk3.display());
    let mut archive = zip::ZipArchive::new(fs::File::open(pk3).map_err(|e| problem(&e))?)
        .map_err(|e| problem(&e))?;
    let _ = fs::remove_dir_all(folder);
    let mut count = 0;
    for index in 0..archive.len() {
        let mut entry = archive.by_index(index).map_err(|e| problem(&e))?;
        let Some(name) = entry.enclosed_name() else {
            continue;
        };
        if entry.is_dir() || !name.starts_with("sprites") {
            continue;
        }
        let to = folder.join(&name);
        if let Some(parent) = to.parent() {
            fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
        }
        let mut file = fs::File::create(&to).map_err(|e| format!("{}: {e}", to.display()))?;
        io::copy(&mut entry, &mut file).map_err(|e| format!("{}: {e}", to.display()))?;
        count += 1;
    }
    note!(
        "took {count} sprites out of {} into {}",
        pk3.display(),
        folder.display()
    );
    Ok(())
}

/// Copies a file to `to` by way of `<to>.part`, unless it already is that file.
fn copy_whole(from: &Path, to: &Path) -> Outcome<()> {
    if from == to {
        return Ok(());
    }
    let problem = |error: io::Error| format!("{}: {error}", to.display());
    if let Some(parent) = to.parent() {
        fs::create_dir_all(parent).map_err(problem)?;
    }
    let mut part = to.as_os_str().to_os_string();
    part.push(".part");
    let part = PathBuf::from(part);
    let bytes = fs::copy(from, &part).map_err(problem)?;
    fs::rename(&part, to).map_err(problem)?;
    note!(
        "copied {} to {} ({bytes} bytes)",
        from.display(),
        to.display()
    );
    Ok(())
}

/// Writes `contents` to `to`, by way of `<to>.part`.
fn write_text(to: &Path, contents: &str) -> Outcome<()> {
    let problem = |error: io::Error| format!("{}: {error}", to.display());
    if let Some(parent) = to.parent() {
        fs::create_dir_all(parent).map_err(problem)?;
    }
    let mut part = to.as_os_str().to_os_string();
    part.push(".part");
    let part = PathBuf::from(part);
    fs::write(&part, contents).map_err(problem)?;
    fs::rename(&part, to).map_err(problem)
}

/// Copies every file under `from` into `to`.
#[cfg(test)]
fn copy_tree(from: &Path, to: &Path) -> Outcome<()> {
    let problem = |error: io::Error| format!("{}: {error}", from.display());
    for entry in fs::read_dir(from).map_err(problem)? {
        let path = entry.map_err(problem)?.path();
        let target = to.join(path.file_name().unwrap_or_default());
        if path.is_dir() {
            copy_tree(&path, &target)?;
        } else {
            copy_whole(&path, &target)?;
        }
    }
    Ok(())
}

fn make_executable(path: &Path) -> Outcome<()> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(path, fs::Permissions::from_mode(0o755))
            .map_err(|error| format!("{}: {error}", path.display()))?;
    }
    let _ = path;
    Ok(())
}

/// A Blender that is installed already: the one we put in `<dir>/blender/`, `$BLENDER`, or one on
/// the PATH. doomify looks in a few more places itself when given none.
fn find_blender(dir: &Path) -> Option<PathBuf> {
    if let Some(ours) = blender_in(&dir.join("blender")) {
        return Some(ours);
    }
    if let Some(path) = std::env::var_os("BLENDER")
        .map(PathBuf::from)
        .filter(|p| p.is_file())
    {
        return Some(path);
    }
    let works = Command::new("blender")
        .arg("--version")
        .output()
        .map(|output| output.status.success())
        .unwrap_or(false);
    works.then(|| PathBuf::from("blender"))
}

/// The Blender executable under `folder` (one level down, where the release unpacks), if any.
fn blender_in(folder: &Path) -> Option<PathBuf> {
    let name = if cfg!(windows) {
        "blender.exe"
    } else {
        "blender"
    };
    fs::read_dir(folder)
        .ok()?
        .filter_map(|entry| entry.ok())
        .map(|entry| entry.path().join(name))
        .find(|path| path.is_file())
}

/// Finds Blender or downloads it into `<dir>/blender/` (the install's question covered it).
fn ensure_blender(dir: &Path) -> Outcome<Option<PathBuf>> {
    if let Some(found) = find_blender(dir) {
        journal::tell(
            "found",
            &[("what", "Blender"), ("place", &found.display().to_string())],
            &format!("Blender: {}", found.display()),
        );
        return Ok(Some(found));
    }
    let download = if cfg!(all(windows, target_arch = "x86_64")) {
        &BLENDER_WINDOWS
    } else if cfg!(all(target_os = "linux", target_arch = "x86_64")) {
        &BLENDER_LINUX
    } else {
        say!("Blender has no pinned release here: install it (blender.org) for doomify");
        return Ok(None);
    };
    journal::section("download");
    let scratch = Scratch::new();
    let file = fetch(download, &scratch)?;
    let folder = dir.join("blender");
    journal::tell(
        "unpack",
        &[
            ("name", download.name),
            ("place", &folder.display().to_string()),
        ],
        &format!("unpacking {} into {}", download.name, folder.display()),
    );
    let part = dir.join("blender.part");
    let _ = fs::remove_dir_all(&part);
    fs::create_dir_all(&part).map_err(|error| format!("{}: {error}", part.display()))?;
    let unpacked = if download.name.ends_with(".zip") {
        unpack_zip(&file, &part)
    } else {
        let status = Command::new("tar")
            .arg("-xJf")
            .arg(&file)
            .arg("-C")
            .arg(&part)
            .status();
        match status {
            Ok(status) if status.success() => Ok(()),
            Ok(status) => Err(format!("tar failed ({status})")),
            Err(error) => Err(format!(
                "couldn't run tar (needed to unpack Blender): {error}"
            )),
        }
    };
    if let Err(problem) = unpacked {
        let _ = fs::remove_dir_all(&part);
        return Err(problem);
    }
    let _ = fs::remove_dir_all(&folder);
    fs::rename(&part, &folder).map_err(|error| format!("{}: {error}", folder.display()))?;
    let found = blender_in(&folder).ok_or("Blender unpacked, but its executable isn't there")?;
    note!("Blender: {}", found.display());
    Ok(Some(found))
}

/// Unpacks every file in the zip into `folder`; a name that would land outside it is refused.
fn unpack_zip(file: &Path, folder: &Path) -> Outcome<()> {
    let problem = |error: &dyn std::fmt::Display| format!("{}: {error}", file.display());
    let mut archive = zip::ZipArchive::new(fs::File::open(file).map_err(|e| problem(&e))?)
        .map_err(|e| problem(&e))?;
    for index in 0..archive.len() {
        let mut entry = archive.by_index(index).map_err(|e| problem(&e))?;
        let name = entry
            .enclosed_name()
            .ok_or_else(|| format!("{} has a file named {:?}", file.display(), entry.name()))?;
        let to = folder.join(name);
        if entry.is_dir() {
            fs::create_dir_all(&to).map_err(|e| format!("{}: {e}", to.display()))?;
        } else {
            if let Some(parent) = to.parent() {
                fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
            }
            let mut out = fs::File::create(&to).map_err(|e| format!("{}: {e}", to.display()))?;
            io::copy(&mut entry, &mut out).map_err(|e| format!("{}: {e}", to.display()))?;
        }
    }
    Ok(())
}

/// Builds the weapons with doomify from the settings in `settings` into `<art>/nacht-waw/`, and
/// packs them into `packed` (the wad pool's `nacht-waw.pk3`). It needs World at War running with
/// Der Riese loaded unless everything is in doomify's cache. Whether it built them.
fn build_weapons(
    here: &Path,
    art: &Path,
    settings: &Path,
    packed: &Path,
    blender: Option<&Path>,
    rerender: bool,
) -> bool {
    journal::section("weapons");
    let later = "To build them later, start World at War, load Der Riese in solo Zombies, and run this again";
    // 🎨 nacht's own sprites, whose names the weapons' never take (sprites_of in doomify.toml)
    if let Err(problem) = unpack_sprites(&here.join("nacht.pk3"), &art.join("nacht")) {
        warn!("{problem}");
        return false;
    }
    let mut project = match doomify::project::Project::load(settings) {
        Ok(project) => project,
        Err(problem) => {
            warn!(
                "doomify's settings in {} don't read: {problem:#}",
                settings.display()
            );
            return false;
        }
    };
    project.config.pack = Some(packed.display().to_string().into());
    // 🗝️ the caches keyed on the built-in files' text, before doomify keyed them on the data
    for (name, keys) in embedded::LEGACY_KEYS {
        let known = project.legacy_keys.entry(name.to_string()).or_default();
        known.extend(keys.iter().map(|key| key.to_string()));
    }
    let running = world_at_war_running();
    if running {
        journal::tell(
            "detected",
            &[
                ("what", "World at War"),
                ("doing", "building nacht-waw from it with doomify"),
            ],
            "World at War is running: building nacht-waw from it with doomify",
        );
    } else {
        journal::tell(
            "undetected",
            &[
                ("what", "World at War"),
                (
                    "instead",
                    "nacht-waw is built from doomify's cache, if everything is in it",
                ),
            ],
            "World at War isn't running, so nacht-waw is built from doomify's cache, if everything is in it",
        );
    }
    let options = doomify::pipeline::Options {
        blender: blender.map(Path::to_path_buf),
        force: rerender,
        say: journal::other,
        run: journal::run,
        ..Default::default()
    };
    match doomify::pipeline::build(&project, &options) {
        Ok(()) => packed.is_file(),
        Err(problem) => {
            warn!("The weapons weren't built: {problem:#}");
            if !running {
                say!("{later}");
            }
            false
        }
    }
}

/// Whether World at War runs now (its CoDWaW.exe, under Windows or Wine and Proton), which
/// doomify takes the weapons from.
fn world_at_war_running() -> bool {
    if cfg!(windows) {
        return Command::new("tasklist")
            .args(["/FI", "IMAGENAME eq CoDWaW.exe", "/NH"])
            .output()
            .is_ok_and(|output| String::from_utf8_lossy(&output.stdout).contains("CoDWaW"));
    }
    fs::read_dir("/proc")
        .into_iter()
        .flatten()
        .flatten()
        .any(|entry| {
            fs::read(entry.path().join("cmdline")).is_ok_and(|cmdline| {
                String::from_utf8_lossy(&cmdline)
                    .to_lowercase()
                    .contains("codwaw")
            })
        })
}

/// Where the `nacht` command is put: `~/.local/bin`, or on Windows a `bin` folder of its own in
/// the artifacts, put on the user's PATH.
fn command_place() -> String {
    if cfg!(windows) {
        "nacht.cmd, on your PATH".into()
    } else {
        "~/.local/bin/nacht".into()
    }
}

/// Makes `nacht` a command anywhere in the terminal: a script in `<art>/bin` that runs `command` (what the
/// shortcuts run: tdl on the install's loadout) with whatever it is given, linked from
/// `~/.local/bin` (on Windows `nacht.cmd` in `<art>/bin`, which goes on the user's PATH). Returns
/// what to tell the user.
fn make_command(art: &Path, command: &[String]) -> Outcome<String> {
    #[cfg(windows)]
    {
        let bin = art.join("bin");
        let quoted: Vec<String> = command.iter().map(|arg| format!("\"{arg}\"")).collect();
        write_text(
            &bin.join("nacht.cmd"),
            &format!(
                "@echo off\r\nrem Nacht des Schreckens in tdl, made by install-nacht\r\n{} %*\r\n",
                quoted.join(" ")
            ),
        )?;
        let script = "$d = $env:NACHT_BIN; $p = [Environment]::GetEnvironmentVariable('Path', 'User'); \
             if (($p -split ';') -notcontains $d) { \
               [Environment]::SetEnvironmentVariable('Path', ($p.TrimEnd(';') + ';' + $d), 'User') }";
        let status = Command::new("powershell")
            .args(["-NoProfile", "-NonInteractive", "-Command", script])
            .env("NACHT_BIN", &bin)
            .status()
            .map_err(|error| format!("couldn't run powershell: {error}"))?;
        if !status.success() {
            return Err(format!("powershell failed ({status})"));
        }
        Ok(format!(
            "The nacht command: {} is on your PATH now. Open a new terminal to use it.",
            bin.join("nacht.cmd").display()
        ))
    }
    #[cfg(not(windows))]
    {
        let quoted: Vec<String> = command
            .iter()
            .map(|arg| format!("'{}'", arg.replace('\'', "'\\''")))
            .collect();
        // in a bin/ of its own: the artifacts' nacht/ is nacht's sprites, for doomify
        let script = art.join("bin").join("nacht");
        write_text(
            &script,
            &format!(
                "#!/bin/sh\n# Nacht des Schreckens in tdl, made by install-nacht\nexec {} \"$@\"\n",
                quoted.join(" ")
            ),
        )?;
        make_executable(&script)?;
        let home = std::env::var_os("HOME")
            .map(PathBuf::from)
            .ok_or("$HOME isn't set")?;
        let bin = home.join(".local").join("bin");
        let link = bin.join("nacht");
        let problem = |error: io::Error| format!("{}: {error}", link.display());
        fs::create_dir_all(&bin).map_err(problem)?;
        // an old link is replaced, a real file never
        match fs::symlink_metadata(&link) {
            Ok(meta) if meta.file_type().is_symlink() => fs::remove_file(&link).map_err(problem)?,
            Ok(_) => {
                return Err(format!(
                    "{} is a file that isn't a link, so it is left alone",
                    link.display()
                ));
            }
            Err(_) => {}
        }
        std::os::unix::fs::symlink(&script, &link).map_err(problem)?;
        let mut told = format!("The nacht command: {}", link.display());
        let on_path = std::env::var_os("PATH")
            .is_some_and(|path| std::env::split_paths(&path).any(|entry| entry == bin));
        if !on_path {
            // ~/.local/bin on the PATH from the next terminal, once (install-tdl may have done it)
            const MARK: &str = "# added by install-nacht";
            let profile = home.join(".profile");
            let old = fs::read_to_string(&profile).unwrap_or_default();
            if !old.contains(MARK) && !old.contains("# added by install-tdl") {
                let separator = if old.is_empty() || old.ends_with('\n') {
                    ""
                } else {
                    "\n"
                };
                let line = format!(
                    "{separator}{MARK}\nexport PATH=\"{}:$PATH\"\n",
                    bin.display()
                );
                fs::OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open(&profile)
                    .and_then(|mut file| file.write_all(line.as_bytes()))
                    .map_err(|error| format!("{}: {error}", profile.display()))?;
            }
            told.push_str(&format!(
                "\n{} isn't on this terminal's PATH yet; {} adds it, so open a new terminal (or run `. ~/.profile`).",
                bin.display(),
                profile.display()
            ));
        }
        Ok(told)
    }
}

/// Downloads `download` into the scratch folder from the first of its URLs that works, checking
/// its size and SHA-256. Returns where it is.
fn fetch(download: &Download, scratch: &Scratch) -> Outcome<PathBuf> {
    let mut last = String::new();
    for url in download.urls {
        match fetch_from(download, url, scratch) {
            Ok(path) => return Ok(path),
            Err(problem) => {
                warn!("{problem}");
                last = problem;
            }
        }
    }
    Err(last)
}

/// Downloads `url` into the scratch folder as `name`, without a hash to check it against. It
/// must not be empty.
fn fetch_unpinned(url: &str, name: &str, scratch: &Scratch) -> Outcome<PathBuf> {
    let path = scratch.dir()?.join("download").join(name);
    note!(
        "downloading {url} (no hash to check it against) to {}",
        path.display()
    );
    let failed = |error: &dyn std::fmt::Display| format!("downloading {url}: {error}");
    fs::create_dir_all(path.parent().unwrap_or(Path::new("."))).map_err(|e| failed(&e))?;
    let mut reader = ureq::get(url)
        .call()
        .map_err(|e| failed(&e))?
        .into_body()
        .into_reader();
    let mut file = fs::File::create(&path).map_err(|e| failed(&e))?;
    let total = io::copy(&mut reader, &mut file).map_err(|e| failed(&e))?;
    file.sync_all().map_err(|e| failed(&e))?;
    if total == 0 {
        return Err(failed(&"it is empty"));
    }
    say!("{name}: {} MB", total / 1_000_000);
    Ok(path)
}

fn fetch_from(download: &Download, url: &str, scratch: &Scratch) -> Outcome<PathBuf> {
    let path = scratch.dir()?.join(download.name);
    journal::tell(
        "download",
        &[
            ("name", download.name),
            ("size", &journal::size(download.size)),
        ],
        &format!(
            "Downloading {} ({})",
            download.name,
            journal::size(download.size)
        ),
    );
    note!(
        "downloading {url} ({} bytes, SHA-256 {}) to {}",
        download.size,
        download.sha256,
        path.display()
    );
    let failed = |error: &dyn std::fmt::Display| format!("downloading {url}: {error}");
    let mut reader = ureq::get(url)
        .call()
        .map_err(|error| failed(&error))?
        .into_body()
        .into_reader();
    let mut file = fs::File::create(&path).map_err(|error| failed(&error))?;
    let mut hasher = Sha256::new();
    let mut buf = vec![0; 256 * 1024];
    let mut total = 0;
    let mut shown = u64::MAX;
    loop {
        let read = reader.read(&mut buf).map_err(|error| failed(&error))?;
        if read == 0 {
            break;
        }
        total += read as u64;
        if total > download.size {
            return Err(failed(&"it is bigger than it should be"));
        }
        hasher.update(&buf[..read]);
        file.write_all(&buf[..read])
            .map_err(|error| failed(&error))?;
        let percent = total * 100 / download.size;
        if percent != shown {
            shown = percent;
            eprint!("\r{}: {percent:>3}%", download.name);
        }
    }
    eprintln!();
    file.sync_all().map_err(|error| failed(&error))?;
    if total != download.size {
        return Err(failed(&"it ended early"));
    }
    let hash = hex(&hasher.finalize());
    if hash != download.sha256 {
        note!("{} came with SHA-256 {hash}", download.name);
        journal::tell(
            "corrupted",
            &[("name", download.name)],
            &format!("{} isn't the file it should be", download.name),
        );
        return Err(failed(&"it isn't the file it should be (its hash differs)"));
    }
    note!(
        "{}: {total} bytes, and its hash is the one it should be",
        download.name
    );
    journal::tell(
        "verified",
        &[("name", download.name)],
        &format!("{}: checked", download.name),
    );
    Ok(path)
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

/// A folder for the downloads, in the system's temporary folder, made the first time it is needed
/// and deleted with everything in it at the end.
struct Scratch(PathBuf);

impl Scratch {
    fn new() -> Self {
        Self(std::env::temp_dir().join(format!("install-nacht-{}", std::process::id())))
    }

    fn dir(&self) -> Outcome<&Path> {
        fs::create_dir_all(&self.0)
            .map_err(|error| format!("couldn't make {}: {error}", self.0.display()))?;
        Ok(&self.0)
    }
}

impl Drop for Scratch {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn altar(name: &str) -> PathBuf {
        let dir =
            std::env::temp_dir().join(format!("install-nacht-test-{name}-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn the_pinned_downloads_are_whole_descriptions() {
        for download in [&BLENDER_LINUX, &BLENDER_WINDOWS] {
            assert_eq!(download.sha256.len(), 64, "{}", download.name);
            assert!(download.urls.iter().all(|url| url.ends_with(download.name)));
        }
    }

    #[test]
    fn nachts_setup_is_a_part_of_tdls() {
        let art = altar("setup");
        // install-tdl's setup.toml, as it writes it
        fs::write(
            art.join("setup.toml"),
            "uzdoom = \"uzdoom/uzdoom.AppImage\"\n\n[[profiles]]\nname = \"Freedoom\"\nwads = []\n",
        )
        .unwrap();
        let profile = |name: &'static str| {
            move |table: &mut toml::Table| {
                set_loadout(table, Path::new("/install/artifacts"), true);
                let list = table
                    .entry("profiles")
                    .or_insert(toml::Value::Array(vec![]));
                let list = list.as_array_mut().unwrap();
                let mut made = toml::Table::new();
                made.insert("name".into(), name.into());
                match list
                    .iter_mut()
                    .find(|kept| kept.get("name").and_then(toml::Value::as_str) == Some(name))
                {
                    Some(kept) => *kept = toml::Value::Table(made),
                    None => list.push(toml::Value::Table(made)),
                }
                table.insert("song".into(), "songs/beauty.wav".into());
            }
        };
        merge_setup(&art, profile("Nacht des Platzhalters")).unwrap();
        merge_setup(&art, profile("Nacht des Platzhalters")).unwrap();
        merge_setup(&art, |table| {
            table.remove("song");
        })
        .unwrap();
        let text = fs::read_to_string(art.join("setup.toml")).unwrap();
        let table: toml::Table = text.parse().unwrap();
        // install-tdl's part kept, nacht's profile once, the loadout set, no song left behind
        assert_eq!(table["uzdoom"].as_str(), Some("uzdoom/uzdoom.AppImage"));
        let names: Vec<_> = table["profiles"]
            .as_array()
            .unwrap()
            .iter()
            .map(|profile| profile["name"].as_str().unwrap())
            .collect();
        assert_eq!(names, ["Freedoom", "Nacht des Platzhalters"]);
        assert_eq!(
            table["loadout"].as_str(),
            Some("/install/artifacts/loadout")
        );
        assert_eq!(table["own_settings"].as_bool(), Some(true));
        assert!(!table.contains_key("song"));
        assert!(text.starts_with("# What tdl keeps"));
        // one that isn't TOML is never written over
        fs::write(art.join("setup.toml"), "not = [toml").unwrap();
        assert!(merge_setup(&art, |_| {}).is_err());
        let _ = fs::remove_dir_all(&art);
    }

    #[test]
    fn world_at_wars_songs_are_pulled_the_last_iwd_winning() {
        let dir = altar("songs");
        let main = dir.join("game/main");
        fs::create_dir_all(&main).unwrap();
        let iwd = |name: &str, files: &[(&str, &[u8])]| {
            let mut writer = zip::ZipWriter::new(fs::File::create(main.join(name)).unwrap());
            for (inside, contents) in files {
                writer
                    .start_file(*inside, zip::write::SimpleFileOptions::default())
                    .unwrap();
                writer.write_all(contents).unwrap();
            }
            writer.finish().unwrap();
        };
        // the game's own capitals, and an older Lullaby that a later IWD overrides
        iwd("iw_00.iwd", &[]);
        iwd(
            "iw_23.iwd",
            &[("sound/Stream/music/Mission/zombie/mx_lullaby.wav", b"old")],
        );
        iwd(
            "iw_27.iwd",
            &[
                ("sound/Stream/music/Mission/zombie/mx_lullaby.wav", b"new"),
                ("sound/Stream/music/Mission/zombie/mx_beauty.wav", b"metal"),
            ],
        );
        let wanted: Vec<&Song> = SONGS.iter().collect();
        let pulled = pull_songs(&wanted, &dir.join("art"), Some(&dir.join("game")));
        let titles: Vec<_> = pulled.iter().map(|(song, _)| song.title).collect();
        // The One's map pack isn't there: it is left out
        assert_eq!(titles, ["Lullaby for a Dead Man", "Beauty of Annihilation"]);
        assert_eq!(fs::read(&pulled[0].1).unwrap(), b"new");
        assert_eq!(
            pulled[1].1,
            dir.join("art/songs/beauty_of_annihilation.wav")
        );
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn only_the_sprites_of_the_pk3_are_unpacked() {
        let dir = altar("sprites");
        let pk3 = dir.join("nacht.pk3");
        let mut writer = zip::ZipWriter::new(fs::File::create(&pk3).unwrap());
        for (name, contents) in [("sprites/a/ABCDA0.png", &b"png"[..]), ("MAPINFO.txt", b"x")] {
            writer
                .start_file(name, zip::write::SimpleFileOptions::default())
                .unwrap();
            writer.write_all(contents).unwrap();
        }
        writer.finish().unwrap();
        unpack_sprites(&pk3, &dir.join("out")).unwrap();
        assert_eq!(
            fs::read(dir.join("out/sprites/a/ABCDA0.png")).unwrap(),
            b"png"
        );
        assert!(!dir.join("out/MAPINFO.txt").exists());
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn blender_is_found_one_folder_down() {
        let dir = altar("blender");
        assert_eq!(blender_in(&dir), None);
        let name = if cfg!(windows) {
            "blender.exe"
        } else {
            "blender"
        };
        fs::create_dir_all(dir.join("blender-4.2.9-linux-x64")).unwrap();
        fs::write(dir.join("blender-4.2.9-linux-x64").join(name), b"").unwrap();
        assert_eq!(
            blender_in(&dir),
            Some(dir.join("blender-4.2.9-linux-x64").join(name))
        );
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn the_settings_are_built_in_as_doomifys_types() {
        // a const, read with serde when this was built
        const COLT: doomify::types::Weapon = embedded::DOOMIFY_WEAPONS_COLT_TOML;
        assert_eq!(COLT.sprite, "CL");
        assert_eq!(embedded::CONFIG.prefix, "Nacht");
        assert!(
            embedded::WEAPONS
                .iter()
                .any(|(id, weapon)| *id == "colt" && *weapon == COLT)
        );
        assert!(!embedded::SOUNDS.is_empty());
        assert!(
            embedded::LEGACY_KEYS
                .iter()
                .any(|(name, keys)| *name == "colt" && !keys.is_empty())
        );
        // only the data is built in: the TOMLs written from it read as the same data
        let built = built_settings();
        assert_eq!(
            built.len(),
            1 + embedded::WEAPONS.len() + embedded::SOUNDS.len()
        );
        for (id, weapon) in embedded::WEAPONS {
            let (_, text) = built
                .iter()
                .find(|(place, _)| *place == format!("weapons/{id}.toml"))
                .unwrap();
            assert!(text.starts_with(WRITTEN));
            assert_eq!(
                &toml::from_str::<doomify::types::Weapon>(text).unwrap(),
                weapon
            );
        }
    }

    #[test]
    fn rewritten_settings_are_kept_until_new_ones_come() {
        let dir = altar("settings");
        let settings = dir.join("doomify");
        let art = dir.join("art");
        let mut steps = journal::Steps::open(&art, false);
        place_settings(&settings, &mut steps).unwrap();
        assert!(
            built_settings()
                .iter()
                .all(|(place, _)| same_as_built(&settings, place))
        );
        // a player's rewrite, and a comment alone, which reads the same
        let colt = settings.join("weapons/colt.toml");
        let text = fs::read_to_string(&colt).unwrap();
        fs::write(&colt, format!("# mine\n{text}")).unwrap();
        assert!(same_as_built(&settings, "weapons/colt.toml"));
        fs::write(&colt, text.replace("name = \"", "name = \"My ")).unwrap();
        assert!(!same_as_built(&settings, "weapons/colt.toml"));
        let mut steps = journal::Steps::open(&art, false);
        place_settings(&settings, &mut steps).unwrap();
        assert!(fs::read_to_string(&colt).unwrap().contains("My "));
        // with --reinstall (as with a newer install-nacht's settings) they are replaced
        let mut steps = journal::Steps::open(&art, true);
        place_settings(&settings, &mut steps).unwrap();
        assert!(!fs::read_to_string(&colt).unwrap().contains("My "));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn tools_come_from_the_workspaces_releases() {
        let workspace = altar("workspace");
        let here = workspace.join("nacht-des-schreckens/published/releases");
        let releases = workspace.join("tdl/published/releases");
        fs::create_dir_all(&here).unwrap();
        fs::create_dir_all(&releases).unwrap();
        assert_eq!(from_workspace(&here, "tdl", "tdl"), None);
        fs::write(releases.join(asset("tdl")), b"").unwrap();
        assert_eq!(
            from_workspace(&here, "tdl", "tdl"),
            Some(releases.join(asset("tdl")))
        );
        // 🏠 a folder that isn't a project's release folder has no workspace around it
        assert_eq!(from_workspace(&workspace.join("tdl"), "tdl", "tdl"), None);
        let _ = fs::remove_dir_all(&workspace);
    }

    #[test]
    fn files_are_copied_whole_and_trees_whole() {
        let dir = altar("copy");
        fs::create_dir_all(dir.join("from/sub")).unwrap();
        fs::write(dir.join("from/a.toml"), b"a").unwrap();
        fs::write(dir.join("from/sub/b.toml"), b"b").unwrap();
        copy_tree(&dir.join("from"), &dir.join("to")).unwrap();
        assert_eq!(fs::read(dir.join("to/sub/b.toml")).unwrap(), b"b");
        assert!(!dir.join("to/a.toml.part").exists());
        let _ = fs::remove_dir_all(&dir);
    }
}
