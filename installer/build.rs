//! Builds every `../doomify/**/*.toml` into the installer as a const of the doomify type it is
//! read into (`doomify.toml` a `Config`, `weapons/*.toml` a `Weapon`, `sounds/*.toml` a
//! `SoundSet`): each is read with serde here, a TOML that doesn't read or check failing the build,
//! and written into `OUT_DIR/const_toml/` as the Rust that builds it, which `const_toml!` puts in a
//! named const (`DOOMIFY_WEAPONS_COLT_TOML`). Then the tables over them: `WEAPONS`, `SOUNDS` and
//! `CONFIG`, and `LEGACY_KEYS`, the keys doomify's caches had when they were keyed on the files'
//! text. Only the data is built in, not the text: the install writes its TOMLs from the data. So
//! the settings it installs are the repository's when it is built: edit them, then rebuild.
//!
//! It also brings installation-groans' files (`groans.rs`, the journal it is built with, and the
//! voices) into `OUT_DIR/groans/`: from nacht's installation-groans submodule, else the
//! workspace's checkout beside nacht, else GitHub.

use std::{
    env, fs, io,
    path::{Path, PathBuf},
};

const GROANS: [&str; 3] = [
    "groans.rs",
    "toiling-through-hell.toml",
    "computer-speak.toml",
];

fn tomls(folder: &Path, found: &mut Vec<PathBuf>) -> io::Result<()> {
    for entry in fs::read_dir(folder)? {
        let path = entry?.path();
        if path.is_dir() {
            tomls(&path, found)?;
        } else if path
            .extension()
            .is_some_and(|extension| extension == "toml")
        {
            found.push(path);
        }
    }
    Ok(())
}

/// installation-groans' files into `OUT_DIR/groans/`, for the installer to build in (`groans.rs`, its
/// journal, and the voices for `const_groan!`): from the project's installation-groans submodule,
/// else the workspace's checkout beside the project, else GitHub. groans.rs is needed to build;
/// a voice found nowhere is left empty, and the installer speaks plainly.
fn groans(project: &Path) -> io::Result<()> {
    const GITHUB: &str =
        "https://raw.githubusercontent.com/error-error-fruit-user/installation-groans/main";
    let out = PathBuf::from(env::var("OUT_DIR").unwrap()).join("groans");
    fs::create_dir_all(&out)?;
    let places = [
        project.join("installation-groans"),
        project.join("..").join("installation-groans"),
    ];
    for name in GROANS {
        for place in &places {
            println!("cargo:rerun-if-changed={}", place.join(name).display());
        }
        let text = places
            .iter()
            .find_map(|place| fs::read_to_string(place.join(name)).ok())
            .or_else(|| {
                let fetched = std::process::Command::new("curl")
                    .args(["-fsSL", &format!("{GITHUB}/{name}")])
                    .output()
                    .ok()?;
                fetched
                    .status
                    .success()
                    .then(|| String::from_utf8_lossy(&fetched.stdout).into_owned())
            });
        let text = match text {
            Some(text) => text,
            None if name.ends_with(".toml") => {
                println!(
                    "cargo:warning=installation-groans' {name} is nowhere to be found: the installer speaks plainly"
                );
                String::new()
            }
            None => {
                return Err(io::Error::other(format!(
                    "installation-groans' {name} is nowhere to be found: run git submodule update --init"
                )));
            }
        };
        // 📜 the journal is built in with include!, where a file's inner doc comments can't be
        let text = if name.ends_with(".rs") {
            text.replace("\n//! ", "\n// ")
                .replace("\n//!\n", "\n//\n")
                .replacen("//! ", "// ", 1)
        } else {
            text
        };
        fs::write(out.join(name), text)?;
    }
    Ok(())
}

fn main() -> io::Result<()> {
    let root = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap()).join("..");
    let root = root.canonicalize()?;
    let folder = root.join("doomify");
    let mut files = vec![];
    tomls(&folder, &mut files)?;
    files.sort();

    // One named const per file (`doomify/weapons/colt.toml` is `DOOMIFY_WEAPONS_COLT_TOML`), of the
    // type its place says, then the tables over them
    let mut code = String::new();
    let mut names = Vec::new();
    let (mut weapons, mut sounds, mut config) = (vec![], vec![], None);
    let mut legacy = Vec::new();
    for path in &files {
        let inside = path
            .strip_prefix(&root)
            .unwrap()
            .to_string_lossy()
            .replace('\\', "/");
        let name: String = inside
            .chars()
            .map(|c| {
                if c.is_ascii_alphanumeric() {
                    c.to_ascii_uppercase()
                } else {
                    '_'
                }
            })
            .collect();
        assert!(
            !names.contains(&name),
            "{inside} makes the const name {name} twice"
        );
        let id = path.file_stem().unwrap().to_string_lossy().into_owned();
        let built = |problem: anyhow::Error| io::Error::other(format!("{problem:#}"));
        let kind = if inside.starts_with("doomify/weapons/") {
            // checked as doomify checks a weapon, so a bad one fails here
            doomify::weapon::Weapon::load(path).map_err(built)?;
            doomify::const_toml::write::<doomify::types::Weapon>(path, &inside).map_err(built)?;
            let text = fs::read_to_string(path)?;
            legacy.push((id.clone(), doomify::project::text_keys(&id, &text)));
            weapons.push((id, name.clone()));
            "Weapon"
        } else if inside.starts_with("doomify/sounds/") {
            doomify::sounds::SoundSet::load(path).map_err(built)?;
            doomify::const_toml::write::<doomify::types::SoundSet>(path, &inside).map_err(built)?;
            let cache = format!("sounds-{id}");
            let text = fs::read_to_string(path)?;
            legacy.push((cache.clone(), doomify::project::text_keys(&cache, &text)));
            sounds.push((id, name.clone()));
            "SoundSet"
        } else if inside == "doomify/doomify.toml" {
            doomify::const_toml::write::<doomify::types::Config>(path, &inside).map_err(built)?;
            config = Some(name.clone());
            "Config"
        } else {
            println!("cargo:warning={inside} is no doomify TOML this knows: left out");
            continue;
        };
        code.push_str(&format!(
            "/// `{inside}`, as the repository had it when this was built.\npub const {name}: {kind} = const_toml![{inside:?}];\n"
        ));
        names.push(name);
    }
    let config = config.ok_or_else(|| io::Error::other("doomify/doomify.toml is missing"))?;
    code.push_str("/// The keys doomify's caches of these had when they were keyed on the files' text (by weapon id, or `sounds-<id>`).\npub const LEGACY_KEYS: &[(&str, &[&str])] = &[\n");
    for (cache, keys) in &legacy {
        code.push_str(&format!("    ({cache:?}, &{keys:?}),\n"));
    }
    code.push_str("];\n");
    for (title, doc, kind, entries) in [
        (
            "WEAPONS",
            "The weapons, `doomify/weapons/*.toml`, by id.",
            "Weapon",
            &weapons,
        ),
        (
            "SOUNDS",
            "The sound sets, `doomify/sounds/*.toml`, by id.",
            "SoundSet",
            &sounds,
        ),
    ] {
        code.push_str(&format!(
            "/// {doc}\npub const {title}: &[(&str, {kind})] = &[\n"
        ));
        for (id, name) in entries {
            code.push_str(&format!("    ({id:?}, {name}),\n"));
        }
        code.push_str("];\n");
    }
    code.push_str(&format!(
        "/// doomify's settings for nacht, `doomify/doomify.toml`.\npub const CONFIG: Config = {config};\n"
    ));
    fs::write(
        PathBuf::from(env::var("OUT_DIR").unwrap()).join("embedded.rs"),
        code,
    )?;

    groans(&root)?;
    println!("cargo:rerun-if-changed={}", folder.display());
    for path in &files {
        println!("cargo:rerun-if-changed={}", path.display());
    }
    Ok(())
}
