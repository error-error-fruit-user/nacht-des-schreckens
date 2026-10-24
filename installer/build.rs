//! Embeds `../doomify.py` and every `../doomify/**/*.toml` into the installer, each as a named const
//! (a `Toml` made by `const_toml!` for a TOML, a `&str` from `include_str!` for the script) (`DOOMIFY_PY`, `DOOMIFY_DOOMIFY_TOML`, `DOOMIFY_WEAPONS_COLT_TOML`, ...), plus the
//! tables `FILES`, `WEAPONS` and `SOUNDS` over them, so the settings it installs are the ones in the repository when it is built: edit them, then
//! rebuild (`cargo build --release`) to customize. (doomify-waw and the other files in `doomify/`
//! are not embedded.)
//!
//! It also brings the voices from installation-groans (`toiling-through-hell.toml`,
//! `computer-speak.toml`) into `OUT_DIR/groans/`, for `const_groan!` to build in: from the
//! workspace's checkout beside nacht's when there is one, or else from GitHub. A voice found in
//! neither is left empty, and the installer speaks plainly.

use std::{
    env, fs, io,
    path::{Path, PathBuf},
};

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

/// installation-groans' voices into `OUT_DIR/groans/`, from beside `root` or else GitHub.
fn groans(root: &Path) -> io::Result<()> {
    const GITHUB: &str =
        "https://raw.githubusercontent.com/error-error-fruit-user/installation-groans/main";
    let out = PathBuf::from(env::var("OUT_DIR").unwrap()).join("groans");
    fs::create_dir_all(&out)?;
    for voice in ["toiling-through-hell.toml", "computer-speak.toml"] {
        let local = root.join("..").join("installation-groans").join(voice);
        println!("cargo:rerun-if-changed={}", local.display());
        let text = fs::read_to_string(&local).ok().or_else(|| {
            let fetched = std::process::Command::new("curl")
                .args(["-fsSL", &format!("{GITHUB}/{voice}")])
                .output()
                .ok()?;
            fetched
                .status
                .success()
                .then(|| String::from_utf8_lossy(&fetched.stdout).into_owned())
        });
        if text.is_none() {
            println!(
                "cargo:warning=installation-groans' {voice} is neither beside nacht nor on GitHub: the installer speaks plainly"
            );
        }
        fs::write(out.join(voice), text.unwrap_or_default())?;
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

    // One named const per file (`doomify/weapons/colt.toml` is `DOOMIFY_WEAPONS_COLT_TOML`), then
    // tables over them: every file to install, and the weapons' and the sounds' settings alone
    let script = root.join("doomify.py");
    let mut entries = vec![("doomify.py".to_string(), script.clone())];
    for path in &files {
        let inside = path
            .strip_prefix(&root)
            .unwrap()
            .to_string_lossy()
            .replace('\\', "/");
        entries.push((inside, path.clone()));
    }
    let mut code = String::new();
    let mut names = Vec::new();
    for (inside, _) in &entries {
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
        if inside.ends_with(".toml") {
            // the macro and `Toml` are main.rs's; the path is from the repository's root
            code.push_str(&format!(
                "/// `{inside}`, as the repository had it when this was built.\npub const {name}: Toml = const_toml![{inside:?}];\n"
            ));
        } else {
            code.push_str(&format!(
                "/// `{inside}`, as the repository had it when this was built.\npub const {name}: &str = include_str!(concat!(env!(\"CARGO_MANIFEST_DIR\"), \"/../\", {inside:?}));\n"
            ));
        }
        names.push(name);
    }
    let table = |title: &str, doc: &str, keep: &dyn Fn(&str) -> bool| {
        let mut table = format!("/// {doc}\npub const {title}: &[(&str, &str)] = &[\n");
        for ((inside, _), name) in entries.iter().zip(&names) {
            if keep(inside) {
                let source = if inside.ends_with(".toml") {
                    format!("{name}.source")
                } else {
                    name.clone()
                };
                table.push_str(&format!("    ({inside:?}, {source}),\n"));
            }
        }
        table.push_str("];\n");
        table
    };
    code.push_str(&table(
        "FILES",
        "Every file to install: where it goes in the install, and what is in it.",
        &|_| true,
    ));
    code.push_str(&table(
        "WEAPONS",
        "The weapons' settings, `doomify/weapons/*.toml`.",
        &|i| i.starts_with("doomify/weapons/"),
    ));
    code.push_str(&table(
        "SOUNDS",
        "The sound sets' settings, `doomify/sounds/*.toml`.",
        &|i| i.starts_with("doomify/sounds/"),
    ));
    fs::write(
        PathBuf::from(env::var("OUT_DIR").unwrap()).join("embedded.rs"),
        code,
    )?;

    groans(&root)?;
    println!("cargo:rerun-if-changed={}", script.display());
    println!("cargo:rerun-if-changed={}", folder.display());
    for path in &files {
        println!("cargo:rerun-if-changed={}", path.display());
    }
    Ok(())
}
