//! `nacht-install`: installs Nacht des Schreckens with everything it needs, then tries to rebuild
//! its World at War weapons and sounds with `doomify.py`. Run it from a published release folder
//! (`published/nacht-des-schreckens/`), which has everything it installs beside it:
//!
//! ```text
//! horde-hammer.pk3           the library nacht runs on
//! nacht.pk3                  the map
//! ```
//!
//! `doomify.py` and the `doomify/**/*.toml` settings are inside the installer itself (embedded by
//! `build.rs` with `include_str!` from the repository), so to customize them, edit them and
//! rebuild it.
//!
//! The tools aren't in it. `tdl`, `tdl-install` and `doomify-waw` are taken from beside this
//! program if they are there, else from the workspace's own releases when this program runs from
//! a release folder in one (`../../../tdl/published/releases/`...), and otherwise downloaded from
//! the latest release of their repositories on GitHub (`tdl.AppImage`/`tdl.exe`, ...). Those downloads can't be checked
//! against a pinned hash, since the latest release isn't known when this is built; they come over
//! HTTPS from the project's own releases.
//!
//! It asks (or `--mode` says) where to install: in place, for you or for everyone, like
//! `tdl-install`. The payload goes in that folder: the pk3s, in `wads/` (a pool tdl offers).
//! Everything else is an artifact, in `artifacts/` there (nacht's `published/artifacts/` when this
//! runs in place from its `published/releases/`, or `--artifacts`): tdl with UZDoom and Freedoom 2,
//! the `doomify` machinery in `nacht-des-schreckens/`, Blender (downloaded, checked against its
//! published SHA-256, unless it is installed already) in `blender/`, the song in `songs/`, the
//! install's loadout and its journal. Then, if World at War is running with
//! Der Riese loaded, it runs `doomify.py`, which takes about an hour the first time. Last, it
//! pulls nacht's song, Der Riese's Beauty of Annihilation, out of the player's World at War
//! (found in a Steam library, or `--waw`) into `songs/` (`--no-song` leaves it), and sets up the
//! install's loadout with `tdl setup`, the song as tdl's.

#[macro_use]
mod journal;

use std::{
    ffi::OsString,
    fs,
    io::{self, IsTerminal, Read, Write},
    path::{Path, PathBuf},
    process::{Command, ExitCode},
};

use clap::{Parser, ValueEnum};
use sha2::{Digest, Sha256};

/// The pk3s nacht is played with, in the order they load.
const PK3S: [&str; 2] = ["horde-hammer.pk3", "nacht.pk3"];
/// Where the tools are released: the latest release of each repository has its programs as
/// assets named like the program, `.AppImage` on Linux and `.exe` on Windows.
const RELEASES: &str = "https://github.com";
const TDL_REPOSITORY: &str = "error-error-fruit-user/tdl";
const DOOMIFY_REPOSITORY: &str = "error-error-fruit-user/doomify-waw";
/// What the installed copy of this project is called.
const NAME: &str = "nacht-des-schreckens";

/// A song of World at War's a map brings: pulled from the player's own game into the install's
/// `songs/` (it never comes with the map) and kept as tdl's song. Each map has its own.
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

/// World at War's folder in a Steam library.
const WORLD_AT_WAR: &str = "steamapps/common/Call of Duty World at War";

/// A TOML file of the repository, embedded when this is built.
#[derive(Clone, Copy, Debug)]
pub struct Toml {
    /// Where it is in the repository.
    pub path: &'static str,
    /// What is in it, as the repository had it when this was built.
    pub source: &'static str,
}

impl Toml {
    /// The file parsed, for looking at its settings.
    pub fn table(&self) -> Result<toml::Table, toml::de::Error> {
        self.source.parse()
    }
}

/// Embeds a TOML file of the repository as a [`Toml`], in a const. The path is from the
/// repository's root (this installer is in `installer/`, one level down):
///
/// ```ignore
/// const colt: Toml = const_toml!["doomify/weapons/colt.toml"];
/// ```
///
/// `build.rs` makes one for every TOML under `doomify/`, named after its path in upper case
/// (`DOOMIFY_WEAPONS_COLT_TOML`); to add settings of your own, put the file there (the next build
/// picks it up) or call this by hand. Edit a file, then rebuild.
macro_rules! const_toml {
    ($path:literal) => {
        $crate::Toml {
            path: $path,
            source: include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/../", $path)),
        }
    };
}

/// `doomify.py` and `doomify/**/*.toml`, as consts (`DOOMIFY_PY`, `DOOMIFY_WEAPONS_COLT_TOML`...)
/// and the tables `FILES`, `WEAPONS` and `SOUNDS`, as the repository had them when this was built.
#[allow(dead_code)] // the per-file consts and tables are there to be used when customizing
mod embedded {
    use crate::Toml;

    include!(concat!(env!("OUT_DIR"), "/embedded.rs"));
}

/// A file to download: where from (the first that works), and what it must be.
struct Download {
    name: &'static str,
    urls: &'static [&'static str],
    size: u64,
    sha256: &'static str,
}

/// Blender 4.2.9 LTS for Linux; doomify-waw needs 4.0 or newer. The hash is the one in the
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

/// Installs Nacht des Schreckens, its tools and, if World at War is running, its weapons.
#[derive(Parser)]
#[command(version, about)]
struct Cli {
    /// Where to install: in place (next to this program), for you, or for everyone. Asked if not
    /// given (and in place if there is no terminal to ask on).
    #[arg(long, value_enum)]
    mode: Option<Mode>,
    /// The folder to install into. Defaults to the one this program is in (in place) or the
    /// mode's own folder.
    #[arg(long, value_name = "DIR")]
    dir: Option<PathBuf>,
    /// Answers yes to every question (downloading Blender, running doomify.py).
    #[arg(short, long)]
    yes: bool,
    /// Leaves tdl, UZDoom and Freedoom 2 out (`tdl-install` isn't run).
    #[arg(long)]
    no_tdl: bool,
    /// Passed to tdl-install: leaves UZDoom out.
    #[arg(long)]
    no_uzdoom: bool,
    /// Passed to tdl-install: leaves Freedoom 2 out.
    #[arg(long)]
    no_freedoom: bool,
    /// Doesn't download Blender.
    #[arg(long)]
    no_blender: bool,
    /// Doesn't run doomify.py.
    #[arg(long)]
    no_doomify: bool,
    /// Doesn't open tdl on the install's loadout at the end
    #[arg(long)]
    no_play: bool,
    /// Doesn't pull nacht's song (Beauty of Annihilation) from World at War for tdl to play
    #[arg(long)]
    no_song: bool,
    /// Where everything but the pk3s goes (tdl, UZDoom, Freedoom 2, Blender, doomify.py, the song,
    /// the loadout, the journal). Defaults to `artifacts/` in the install's folder, or nacht's
    /// `published/artifacts/` when this runs in place from its `published/releases/`.
    #[arg(long, value_name = "DIR")]
    artifacts: Option<PathBuf>,
    /// World at War's folder, if it isn't in a Steam library this can find
    #[arg(long, value_name = "DIR")]
    waw: Option<PathBuf>,
    /// The Blender doomify.py renders with, instead of finding or downloading one.
    #[arg(long, value_name = "PATH")]
    blender: Option<PathBuf>,
    /// Says what it does plainly and formally, rather than as a descent through hell (and has
    /// tdl-install and doomify.py do the same)
    #[arg(long)]
    computer_speak: bool,
}

/// One of installation-groans' voices, as this was built with it (see `build.rs`): the same trick
/// as `const_toml!`, from the build's own folder.
macro_rules! const_groan {
    ($voice:literal) => {
        include_str!(concat!(env!("OUT_DIR"), "/groans/", $voice))
    };
}

/// Toiling Through Hell, the voice the install speaks in unless told `--computer-speak`.
const TOILING_THROUGH_HELL: &str = const_groan!["toiling-through-hell.toml"];
/// Computer Speak, for `--computer-speak`.
const COMPUTER_SPEAK: &str = const_groan!["computer-speak.toml"];

/// Where nacht lives.
#[derive(Clone, Copy, PartialEq, Eq, Debug, ValueEnum)]
enum Mode {
    /// Next to this program.
    InPlace,
    /// Copied into your own folder, with the `tdl` command on your PATH.
    User,
    /// Copied into the system's folder, with the `tdl` command on everyone's PATH. Needs root.
    System,
}

impl Mode {
    fn flag(self) -> &'static str {
        match self {
            Mode::InPlace => "in-place",
            Mode::User => "user",
            Mode::System => "system",
        }
    }
}

/// What went wrong, for the user.
type Outcome<T> = Result<T, String>;

/// The folder this program is in. An AppImage runs from a mount that goes away with it, so for
/// one it is the folder of the AppImage file itself (`$APPIMAGE`).
fn program_dir() -> Option<PathBuf> {
    let exe = std::env::var_os("APPIMAGE")
        .map(PathBuf::from)
        .filter(|path| path.is_file())
        .or_else(|| std::env::current_exe().ok())?;
    exe.parent().map(Path::to_path_buf)
}

fn main() -> ExitCode {
    let cli = Cli::parse();
    journal::speak_in(if cli.computer_speak {
        COMPUTER_SPEAK
    } else {
        TOILING_THROUGH_HELL
    });
    match run(&cli) {
        Ok(()) => ExitCode::SUCCESS,
        Err(problem) => {
            warn!("{problem}");
            ExitCode::FAILURE
        }
    }
}

fn run(cli: &Cli) -> Outcome<()> {
    let here = program_dir().ok_or("Couldn't tell where this program is")?;
    let mode = cli.mode.unwrap_or_else(|| {
        if io::stdin().is_terminal() {
            ask_mode(&here)
        } else {
            Mode::InPlace
        }
    });
    let dir = match &cli.dir {
        Some(dir) => std::path::absolute(dir).unwrap_or_else(|_| dir.clone()),
        None => install_dir(mode, &here)?,
    };
    if mode == Mode::System {
        check_privileges()?;
    }
    for pk3 in PK3S {
        if !here.join(pk3).is_file() {
            return Err(format!(
                "{pk3} isn't next to this program, in {}: run it from the published folder",
                here.display()
            ));
        }
    }
    fs::create_dir_all(&dir).map_err(|error| format!("{}: {error}", dir.display()))?;
    let art = artifacts_dir(cli.artifacts.as_deref(), &dir, &here);
    fs::create_dir_all(&art).map_err(|error| format!("{}: {error}", art.display()))?;
    // 📓 from here on the journal is kept with the artifacts
    let journal = journal::open(&art, "nacht-install.log");
    journal::tell(
        "begin",
        &[
            ("what", "Nacht des Schreckens"),
            ("place", &dir.display().to_string()),
        ],
        &format!("Installing Nacht des Schreckens in {}", dir.display()),
    );
    note!("this program is in {}", here.display());
    note!(
        "mode {mode:?}; leaving out: tdl {}, uzdoom {}, freedoom {}, blender {}, doomify {}; yes to everything: {}",
        cli.no_tdl,
        cli.no_uzdoom,
        cli.no_freedoom,
        cli.no_blender,
        cli.no_doomify,
        cli.yes
    );

    let scratch = Scratch::new();
    if !cli.no_tdl {
        install_tdl(&here, &art, mode, cli, &scratch)?;
    }
    let home = art.join(NAME);
    place_files(&here, &dir, &home, &scratch)?;

    let python = find_python();
    if python.is_none() {
        say!(
            "Python 3 wasn't found, and doomify.py needs it: install it (python.org), then run it in {}",
            home.display()
        );
    }
    let blender = match &cli.blender {
        Some(path) => Some(path.clone()),
        None if cli.no_blender => find_blender(&art),
        None => ensure_blender(&art, cli.yes)?,
    };
    note!("blender: {:?}", blender);
    if !cli.no_doomify
        && let Some(python) = python
    {
        doomify(
            &python,
            &home,
            &dir,
            blender.as_deref(),
            cli.yes,
            cli.computer_speak,
        );
    }
    if let Some(journal) = &journal {
        journal::tell(
            "journal",
            &[("place", &journal.display().to_string())],
            &format!("Everything this install did is in {}", journal.display()),
        );
    }
    let song = if cli.no_song {
        None
    } else {
        pull_song(&SONG, &art, cli.waw.as_deref())
    };
    let tdl = set_up_loadout(&dir, &art, &home, song.as_deref());
    journal::tell(
        "done",
        &[("what", "Nacht des Schreckens")],
        "Done: Nacht des Platzhalters (and Nacht des Schreckens, once doomify.py has made its weapons) are profiles in the install's loadout",
    );
    if let Some(tdl) = tdl {
        play(&tdl, &dir, &art, cli.no_play);
    }
    Ok(())
}

/// The install's own loadout (`<art>/loadout`, in the artifacts): `setup.toml` beside doomify.py
/// makes Nacht des Platzhalters in it, and Nacht des Schreckens once `nacht-waw.pk3` is in the wad
/// pool (`<dir>/wads`), and the tdl the install put in `art` (or the one on the PATH) runs
/// `tdl setup` on it. Returns that tdl, or
/// `None` (said) when there is none or the setup failed.
fn set_up_loadout(dir: &Path, art: &Path, home: &Path, song: Option<&Path>) -> Option<PathBuf> {
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
            "There is no tdl to set up the profiles with (tdl-install puts one in {})",
            art.display()
        );
        return None;
    };
    let wads = dir.join("wads");
    let quoted = |path: &Path| format!("{:?}", path.display().to_string());
    let mut text = format!(
        "# The install's own loadout, and its profiles: what nacht-install keeps with `tdl setup`.\n\
         loadout = {}\nremember_loadout = false\n{}\n\
         [[profiles]]\nname = \"Nacht des Platzhalters\"\nwads = [{}, {}]\n",
        quoted(&art.join("loadout")),
        song.map(|song| format!("song = {}\n", quoted(song)))
            .unwrap_or_default(),
        quoted(&wads.join("horde-hammer.pk3")),
        quoted(&wads.join("nacht.pk3")),
    );
    if wads.join("nacht-waw.pk3").is_file() {
        text.push_str(&format!(
            "\n[[profiles]]\nname = \"Nacht des Schreckens\"\nplace = 1\nwads = [{}, {}, {}]\n",
            quoted(&wads.join("horde-hammer.pk3")),
            quoted(&wads.join("nacht.pk3")),
            quoted(&wads.join("nacht-waw.pk3")),
        ));
    }
    let setup = home.join("setup.toml");
    if let Err(problem) = write_text(&setup, &text) {
        warn!("{problem}");
        return None;
    }
    let command = format!("tdl setup {}", setup.display());
    journal::tell(
        "run",
        &[("command", &command)],
        &format!("running {command}"),
    );
    match Command::new(&tdl).arg("setup").arg(&setup).status() {
        Ok(status) if status.success() => {
            journal::tell(
                "ran",
                &[("command", &command)],
                &format!("{command} is done"),
            );
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

/// Pulls `song` out of the player's World at War (`waw`, or the one in a Steam library) into
/// `<dir>/songs/`, after its warning. Returns where it is, or `None` (said) when there is no game
/// or no song in it.
fn pull_song(song: &Song, dir: &Path, waw: Option<&Path>) -> Option<PathBuf> {
    say!("{}", song.warning);
    let Some(main) = world_at_war(waw) else {
        say!(
            "World at War wasn't found, so {} isn't tdl's song (--waw DIR says where it is)",
            song.title
        );
        return None;
    };
    journal::tell(
        "found",
        &[
            ("what", "World at War"),
            ("place", &main.display().to_string()),
        ],
        &format!("World at War: {}", main.display()),
    );
    let to = dir.join("songs").join(song.file);
    match pull(song, &main, &to) {
        Ok(true) => {
            journal::tell(
                "copy",
                &[("what", song.title), ("place", &to.display().to_string())],
                &format!("{}: {}", song.title, to.display()),
            );
            Some(to)
        }
        Ok(false) => {
            say!(
                "{} isn't in World at War's IWDs in {}",
                song.title,
                main.display()
            );
            None
        }
        Err(problem) => {
            warn!("Couldn't pull {}: {problem}", song.title);
            None
        }
    }
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
    if no_play || !io::stdin().is_terminal() || !io::stdout().is_terminal() {
        say!("To play: {command}");
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
    let candidates = [name.to_string(), format!("{name}.exe"), asset(name)];
    let project = repository.rsplit('/').next().unwrap_or(repository);
    if let Some(beside) = candidates
        .iter()
        .map(|n| here.join(n))
        .find(|path| path.is_file())
    {
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
            &[("name", name), ("size", "its size unknown")],
            &format!("{name} isn't next to this program, so it is downloaded: {url}"),
        );
        let file = fetch_unpinned(&url, &asset(name), scratch)?;
        copy_whole(&file, to)?;
    }
    make_executable(to)?;
    note!("{name} is at {}", to.display());
    Ok(())
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

/// Runs the `tdl-install` that puts tdl, UZDoom and Freedoom 2 in `dir`. It and tdl are staged
/// side by side first, since tdl-install copies the tdl it finds beside itself.
fn install_tdl(here: &Path, dir: &Path, mode: Mode, cli: &Cli, scratch: &Scratch) -> Outcome<()> {
    let stage = scratch.dir()?.join("tools");
    let installer = stage.join(asset("tdl-install"));
    let tdl = stage.join(asset("tdl"));
    get_tool(here, "tdl-install", TDL_REPOSITORY, &installer, scratch)?;
    get_tool(here, "tdl", TDL_REPOSITORY, &tdl, scratch)?;
    if mode == Mode::InPlace {
        // 🧱 in place there is no copying: tdl is simply put where it will live
        copy_whole(
            &tdl,
            &dir.join(if cfg!(windows) { "tdl.exe" } else { "tdl" }),
        )?;
        make_executable(&dir.join(if cfg!(windows) { "tdl.exe" } else { "tdl" }))?;
    }
    journal::tell("run", &[("command", "tdl-install")], "Running tdl-install");
    note!(
        "running {} --mode {} --dir {}",
        installer.display(),
        mode.flag(),
        dir.display()
    );
    let mut command = Command::new(&installer);
    // 📦 the installer is its own AppImage, if it is one
    command.env_remove("APPIMAGE");
    // 🗃️ tdl is an artifact here, and so is all tdl-install makes beside it
    command
        .arg("--mode")
        .arg(mode.flag())
        .arg("--dir")
        .arg(dir)
        .arg("--artifacts")
        .arg(dir);
    if cli.computer_speak {
        command.arg("--computer-speak");
    }
    if cli.no_uzdoom {
        command.arg("--no-uzdoom");
    }
    if cli.no_freedoom {
        command.arg("--no-freedoom");
    }
    let status = command
        .status()
        .map_err(|error| format!("couldn't run {}: {error}", installer.display()))?;
    note!("tdl-install ended: {status}");
    if status.success() {
        Ok(())
    } else {
        Err(format!("tdl-install failed ({status})"))
    }
}

/// Puts the pk3s in `<dir>/wads/` and the doomify machinery in `home`: doomify.py, its settings,
/// doomify-waw and the sprites of nacht.pk3, which doomify-waw reads to avoid their names.
fn place_files(here: &Path, dir: &Path, home: &Path, scratch: &Scratch) -> Outcome<()> {
    let wads = dir.join("wads");
    for pk3 in PK3S {
        copy_whole(&here.join(pk3), &wads.join(pk3))?;
        journal::tell(
            "copy",
            &[("what", pk3), ("place", &wads.display().to_string())],
            &format!("{pk3}: {}", wads.join(pk3).display()),
        );
    }
    for (inside, contents) in embedded::FILES {
        write_text(&home.join(inside), contents)?;
    }
    // 🗣️ the voices this was built with, for doomify.py, which has no workspace beside it here
    for (voice, contents) in [
        ("toiling-through-hell.toml", TOILING_THROUGH_HELL),
        ("computer-speak.toml", COMPUTER_SPEAK),
    ] {
        if !contents.is_empty() {
            write_text(&home.join("groans").join(voice), contents)?;
        }
    }
    note!(
        "wrote doomify.py and its {} settings into {}",
        embedded::FILES.len() - 1,
        home.display()
    );
    // 🗃️ doomify.py's artifacts are beside it here, in the install's artifacts
    let to = home.join(if cfg!(windows) {
        "doomify-waw.exe"
    } else {
        "doomify-waw"
    });
    // Not fatal: without it doomify.py builds doomify-waw from its source (git and cargo)
    if let Err(problem) = get_tool(here, "doomify-waw", DOOMIFY_REPOSITORY, &to, scratch) {
        warn!(
            "{problem}\ndoomify-waw wasn't installed, so doomify.py will try to build it from source (it needs git and cargo)"
        );
    }
    unpack_sprites(&here.join("nacht.pk3"), &home.join("nacht"))?;
    journal::tell(
        "copy",
        &[
            ("what", "doomify.py"),
            ("place", &home.display().to_string()),
        ],
        &format!("doomify.py: {}", home.display()),
    );
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

/// The Python 3 that runs doomify.py, if one is installed.
fn find_python() -> Option<OsString> {
    let found = find_python_quietly();
    note!("python: {:?}", found);
    found
}

fn find_python_quietly() -> Option<OsString> {
    let candidates: &[&str] = if cfg!(windows) {
        &["python", "py"]
    } else {
        &["python3", "python"]
    };
    candidates.iter().find_map(|name| {
        let output = Command::new(name).arg("--version").output().ok()?;
        let text = String::from_utf8_lossy(&output.stdout).to_string()
            + &String::from_utf8_lossy(&output.stderr);
        (output.status.success() && text.trim_start().starts_with("Python 3"))
            .then(|| OsString::from(name))
    })
}

/// A Blender that is installed already: the one we put in `<dir>/blender/`, `$BLENDER`, or one on
/// the PATH. doomify-waw looks in a few more places itself when given none.
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

/// Finds Blender or, if the user agrees, downloads it into `<dir>/blender/`.
fn ensure_blender(dir: &Path, yes: bool) -> Outcome<Option<PathBuf>> {
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
        say!("Blender has no pinned release here: install it (blender.org) for doomify.py");
        return Ok(None);
    };
    let question = format!(
        "Blender (4.0 or newer) renders the weapons and isn't installed. Download Blender 4.2 LTS ({} MB) into {}?",
        download.size / 1_000_000,
        dir.join("blender").display()
    );
    if !(yes || ask_yes(&question)) {
        say!("Skipped Blender; doomify.py needs it (blender.org, or --blender PATH).");
        return Ok(None);
    }
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
    say!("Blender: {}", found.display());
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

/// Runs doomify.py in `home` (after asking whether the game is running), then puts the packed
/// `nacht-waw.pk3` in the wad pool. Nothing here is an error: the rest is installed, and the
/// command to run later is printed.
fn doomify(
    python: &OsString,
    home: &Path,
    dir: &Path,
    blender: Option<&Path>,
    yes: bool,
    computer_speak: bool,
) {
    let mut args: Vec<OsString> = vec!["doomify.py".into(), "--pack".into()];
    if computer_speak {
        args.push("--computer-speak".into());
    }
    if let Some(blender) = blender {
        args.extend(["--".into(), "--blender".into(), blender.into()]);
    }
    let later = || {
        let shown: Vec<_> = args.iter().map(|arg| arg.to_string_lossy()).collect();
        say!(
            "To make the weapons later, start World at War, load Der Riese in solo Zombies, and run in {}:\n  {} {}",
            home.display(),
            python.to_string_lossy(),
            shown.join(" ")
        );
    };
    if !(yes
        || ask_yes(
            "Is World at War running with Der Riese loaded (solo Zombies)? doomify.py rebuilds the weapons from it and takes about an hour",
        ))
    {
        later();
        return;
    }
    note!(
        "running {} {} in {}",
        python.to_string_lossy(),
        args.iter()
            .map(|arg| arg.to_string_lossy())
            .collect::<Vec<_>>()
            .join(" "),
        home.display()
    );
    match Command::new(python).args(&args).current_dir(home).status() {
        Ok(status) if status.success() => {
            let pk3 = home.join("nacht-waw.pk3");
            match copy_whole(&pk3, &dir.join("wads").join("nacht-waw.pk3")) {
                Ok(()) => say!("nacht-waw.pk3: {}", dir.join("wads").display()),
                Err(problem) => warn!("{problem}"),
            }
        }
        Ok(status) => {
            warn!("doomify.py failed ({status}).");
            later();
        }
        Err(error) => {
            warn!("Couldn't run doomify.py: {error}");
            later();
        }
    }
}

/// Asks a yes-or-no question, no by default; without a terminal the answer is no.
fn ask_yes(question: &str) -> bool {
    if !io::stdin().is_terminal() {
        return false;
    }
    print!("{question} [y/n] ");
    let _ = io::stdout().flush();
    let mut line = String::new();
    io::stdin().read_line(&mut line).is_ok()
        && matches!(line.trim().to_lowercase().as_str(), "y" | "yes")
}

/// Asks where nacht should live. Enter takes in place; input that ends takes it too.
fn ask_mode(here: &Path) -> Mode {
    say!("Where should Nacht des Schreckens be installed?");
    say!(
        "  1) In place: in {}, nothing else changes (default)",
        here.display()
    );
    for (number, mode, who) in [
        (2, Mode::User, "For you"),
        (3, Mode::System, "For everyone"),
    ] {
        let folder = install_dir(mode, here)
            .map(|dir| dir.display().to_string())
            .unwrap_or_else(|_| "?".into());
        let note = if mode == Mode::System {
            "; needs root"
        } else {
            ""
        };
        say!("  {number}) {who}: in {folder}, with the tdl command on your PATH{note}");
    }
    loop {
        print!("Choice [1]: ");
        let _ = io::stdout().flush();
        let mut line = String::new();
        if io::stdin().read_line(&mut line).unwrap_or(0) == 0 {
            println!();
            return Mode::InPlace;
        }
        match parse_choice(&line) {
            Some(mode) => return mode,
            None => say!("Type 1, 2 or 3."),
        }
    }
}

/// What the user typed at the question, if it is an answer. Nothing at all is in place.
fn parse_choice(line: &str) -> Option<Mode> {
    match line.trim().to_lowercase().as_str() {
        "" | "1" | "in place" | "in-place" | "i" => Some(Mode::InPlace),
        "2" | "user" | "u" | "you" | "for you" => Some(Mode::User),
        "3" | "system" | "s" | "everyone" | "for everyone" => Some(Mode::System),
        _ => None,
    }
}

/// Where everything but the pk3s goes: `given`, or, when this runs in place from a project's
/// `published/releases/`, that project's `published/artifacts/`, or else `<dir>/artifacts/`.
fn artifacts_dir(given: Option<&Path>, dir: &Path, here: &Path) -> PathBuf {
    if let Some(given) = given {
        return std::path::absolute(given).unwrap_or_else(|_| given.to_path_buf());
    }
    match here.parent() {
        Some(published)
            if dir == here
                && here.file_name().is_some_and(|name| name == "releases")
                && published
                    .file_name()
                    .is_some_and(|name| name == "published") =>
        {
            published.join("artifacts")
        }
        _ => dir.join("artifacts"),
    }
}

/// The folder nacht is installed to in `mode`; `here` is where this program is.
fn install_dir(mode: Mode, here: &Path) -> Outcome<PathBuf> {
    let var = |name: &str| {
        std::env::var_os(name)
            .map(PathBuf::from)
            .filter(|path| !path.as_os_str().is_empty())
            .ok_or_else(|| format!("${name} isn't set; pass --dir"))
    };
    Ok(match (mode, cfg!(windows)) {
        (Mode::InPlace, _) => here.to_path_buf(),
        (Mode::User, true) => var("LOCALAPPDATA")?.join("Programs").join(NAME),
        (Mode::User, false) => var("HOME")?.join(".local").join("opt").join(NAME),
        (Mode::System, true) => var("ProgramFiles")?.join(NAME),
        (Mode::System, false) => PathBuf::from("/opt").join(NAME),
    })
}

/// A system install writes where only root can: says so before anything is done.
fn check_privileges() -> Outcome<()> {
    #[cfg(windows)]
    let elevated = Command::new("net")
        .args(["session"])
        .output()
        .map(|output| output.status.success())
        .unwrap_or(false);
    #[cfg(not(windows))]
    let elevated = Command::new("id")
        .arg("-u")
        .output()
        .map(|output| output.stdout.trim_ascii() == b"0")
        .unwrap_or(false);
    if elevated {
        Ok(())
    } else if cfg!(windows) {
        Err("Installing for everyone needs an administrator: run this from an elevated terminal, or choose \"for you\"".into())
    } else {
        Err("Installing for everyone needs root: run this with sudo, or choose \"for you\"".into())
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
        Self(std::env::temp_dir().join(format!("nacht-install-{}", std::process::id())))
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
            std::env::temp_dir().join(format!("nacht-install-test-{name}-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn the_question_takes_numbers_and_words() {
        assert_eq!(parse_choice("\n"), Some(Mode::InPlace));
        assert_eq!(parse_choice(" 2 "), Some(Mode::User));
        assert_eq!(parse_choice("For Everyone"), Some(Mode::System));
        assert_eq!(parse_choice("4"), None);
    }

    #[test]
    fn the_pinned_downloads_are_whole_descriptions() {
        for download in [&BLENDER_LINUX, &BLENDER_WINDOWS] {
            assert_eq!(download.sha256.len(), 64, "{}", download.name);
            assert!(download.urls.iter().all(|url| url.ends_with(download.name)));
        }
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
    fn the_settings_are_embedded() {
        let names: Vec<_> = embedded::FILES.iter().map(|(name, _)| *name).collect();
        assert!(names.contains(&"doomify.py"));
        assert_eq!(embedded::DOOMIFY_PY, embedded::FILES[0].1);
        assert!(embedded::DOOMIFY_DOOMIFY_TOML.source.contains("prefix"));
        assert_eq!(embedded::DOOMIFY_DOOMIFY_TOML.path, "doomify/doomify.toml");
        assert!(
            embedded::WEAPONS
                .iter()
                .any(|(name, _)| *name == "doomify/weapons/colt.toml")
        );
        assert!(embedded::WEAPONS.contains(&(
            "doomify/weapons/colt.toml",
            embedded::DOOMIFY_WEAPONS_COLT_TOML.source
        )));
        assert!(
            embedded::SOUNDS
                .iter()
                .all(|(name, _)| name.starts_with("doomify/sounds/"))
        );
        assert!(names.contains(&"doomify/doomify.toml"));
        assert!(
            names
                .iter()
                .any(|name| name.starts_with("doomify/weapons/"))
        );
        assert!(
            embedded::FILES
                .iter()
                .all(|(_, contents)| !contents.is_empty())
        );
    }

    #[test]
    fn every_embedded_toml_parses() {
        for (name, source) in embedded::FILES
            .iter()
            .filter(|(name, _)| name.ends_with(".toml"))
        {
            assert!(source.parse::<toml::Table>().is_ok(), "{name} isn't TOML");
        }
        let colt = embedded::DOOMIFY_WEAPONS_COLT_TOML.table().unwrap();
        assert!(!colt.is_empty());
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
