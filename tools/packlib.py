"""Read the CloudMine packwiz pack: entries (.pw.toml files), pack versions, and line-ending checks."""
import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

FOLDERS = ("mods", "resourcepacks", "shaderpacks")


@dataclass
class Entry:
    id: str
    folder: str
    name: str
    filename: str
    side: str
    download: str
    hash: str
    modrinth_id: str | None
    version_id: str | None
    optional: bool
    default: bool
    description: str


def _entry(path: Path, folder: str) -> Entry:
    with path.open("rb") as f:
        data = tomllib.load(f)
    download = data.get("download", {})
    modrinth = data.get("update", {}).get("modrinth", {})
    option = data.get("option", {})
    return Entry(
        id=path.name.removesuffix(".pw.toml"),
        folder=folder,
        name=data.get("name", ""),
        filename=data.get("filename", ""),
        side=data.get("side", "both"),
        download=download.get("url", ""),
        hash=download.get("hash", ""),
        modrinth_id=modrinth.get("mod-id"),
        version_id=modrinth.get("version"),
        optional=bool(option.get("optional", False)),
        default=bool(option.get("default", False)),
        description=option.get("description", ""),
    )


def read_entries(pack_dir: Path) -> list[Entry]:
    entries = []
    for folder in FOLDERS:
        for path in (Path(pack_dir) / folder).glob("*.pw.toml"):
            entries.append(_entry(path, folder))
    return sorted(entries, key=lambda e: e.id)


def category(e: Entry) -> str:
    if e.folder == "resourcepacks":
        return "resourcepack"
    if e.folder == "shaderpacks":
        return "shader"
    return "optional" if e.optional else "core"


def read_versions(pack_dir: Path) -> dict:
    with (Path(pack_dir) / "pack.toml").open("rb") as f:
        data = tomllib.load(f)
    versions = data.get("versions", {})
    return {"version": data.get("version", ""), "minecraft": versions.get("minecraft", ""),
            "neoforge": versions.get("neoforge", "")}


def set_pack_version(pack_dir: Path, version: str) -> None:
    path = Path(pack_dir) / "pack.toml"
    text = path.read_text(encoding="utf-8")
    # Only the top-level key: it comes before the first [table] header.
    head, sep, rest = text.partition("\n[")
    head = re.sub(r'(?m)^version\s*=\s*".*"$', f'version = "{version}"', head, count=1)
    path.write_text(head + sep + rest, encoding="utf-8", newline="\n")


def crlf_files(repo: Path) -> list[str]:
    out = subprocess.run(["git", "-C", str(repo), "ls-files", "--eol"], check=True,
                         capture_output=True, text=True).stdout
    return parse_eol(out)


def parse_eol(out: str) -> list[str]:
    """Paths from `git ls-files --eol` output whose index or working copy has CRLF line endings."""
    bad = []
    for line in out.splitlines():
        # "<index eol> <worktree eol> attr/<attrs>\t<path>"
        info, _, path = line.partition("\t")
        if "i/crlf" in info or "w/crlf" in info:
            bad.append(path)
    return bad
