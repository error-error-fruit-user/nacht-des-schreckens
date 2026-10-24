//! Embeds `../doomify.py` and every `../doomify/**/*.toml` into the installer, with `include_str!`,
//! so the settings it installs are the ones in the repository when it is built: edit them, then
//! rebuild (`cargo build --release`) to customize. (doomify-waw and the other files in `doomify/`
//! are not embedded.)

use std::{env, fs, io, path::{Path, PathBuf}};

fn tomls(folder: &Path, found: &mut Vec<PathBuf>) -> io::Result<()> {
    for entry in fs::read_dir(folder)? {
        let path = entry?.path();
        if path.is_dir() {
            tomls(&path, found)?;
        } else if path.extension().is_some_and(|extension| extension == "toml") {
            found.push(path);
        }
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

    let mut code = String::from("/// The files embedded from the repository: where they go in the install, and what is in them.\n");
    code.push_str("pub const FILES: &[(&str, &str)] = &[\n");
    let script = root.join("doomify.py");
    code.push_str(&format!("    (\"doomify.py\", include_str!({:?})),\n", script.display().to_string()));
    for path in &files {
        let inside = path.strip_prefix(&root).unwrap().to_string_lossy().replace('\\', "/");
        code.push_str(&format!("    ({inside:?}, include_str!({:?})),\n", path.display().to_string()));
    }
    code.push_str("];\n");
    fs::write(PathBuf::from(env::var("OUT_DIR").unwrap()).join("embedded.rs"), code)?;

    println!("cargo:rerun-if-changed={}", script.display());
    println!("cargo:rerun-if-changed={}", folder.display());
    for path in &files {
        println!("cargo:rerun-if-changed={}", path.display());
    }
    Ok(())
}
