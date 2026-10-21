"""Shared test fixtures: throwaway pack folders and git repos."""
import subprocess
import tempfile
from pathlib import Path

PACK_TOML = '''name = "CloudMine"
author = "chrisbmn"
version = "2.0.0"
pack-format = "packwiz:1.1.0"

[index]
file = "index.toml"
hash-format = "sha256"
hash = "0"

[versions]
minecraft = "1.21.1"
neoforge = "21.1.215"
'''


def pw_toml(name, filename, side=None, mod_id=None, version=None, url="https://cdn.example/x.jar", option=None):
    """Text of a minimal .pw.toml. option is a dict like {"optional": True, "default": False, "description": "x"}."""
    lines = [f'name = "{name}"', f'filename = "{filename}"']
    if side is not None:
        lines.append(f'side = "{side}"')
    lines += ["", "[download]", f'url = "{url}"', 'hash-format = "sha1"', 'hash = "abc"']
    if mod_id is not None:
        lines += ["", "[update]", "[update.modrinth]", f'mod-id = "{mod_id}"', f'version = "{version}"']
    if option is not None:
        lines += ["", "[option]", f'optional = {str(option["optional"]).lower()}']
        if "default" in option:
            lines.append(f'default = {str(option["default"]).lower()}')
        if "description" in option:
            lines.append(f'description = "{option["description"]}"')
    return "\n".join(lines) + "\n"


def make_pack(files=None):
    """A temp pack dir with pack.toml plus {relative path: text} files. Returns its Path."""
    root = Path(tempfile.mkdtemp(prefix="cmpack"))
    (root / "pack.toml").write_text(PACK_TOML, encoding="utf-8", newline="\n")
    for rel, text in (files or {}).items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
    return root


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def make_repo(files):
    """A temp git repo with .gitattributes '* -text' and {path: bytes} committed on branch testing."""
    root = Path(tempfile.mkdtemp(prefix="cmrepo"))
    git(root, "init", "-q", "-b", "testing")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")
    git(root, "config", "core.autocrlf", "false")
    (root / ".gitattributes").write_bytes(b"* -text\n")
    for rel, data in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "init")
    return root
