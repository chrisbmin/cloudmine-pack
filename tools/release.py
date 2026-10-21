"""Release what's on the testing branch to every member.

    python tools/release.py 2.1.0 --dry-run          # show what would change, touch nothing
    python tools/release.py 2.1.0 --notes "Text"     # release for real

Checks you're on a clean, pushed-ready `testing`, works out what changed since the last release, writes the
website's data (site-data/mods.json, site-data/changelog.json), bumps the pack version, and publishes:
testing is fast-forwarded into main, tagged v<version>, and both branches plus the tag are pushed.

If any mod that also runs on the server changed, it prints the server steps first and waits until you type
`stopped` (or pass --server-done).
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))  # so `python tools/release.py` can import the tools package

from tools.packlib import category, parse_eol, read_entries, read_versions, set_pack_version  # noqa: E402

USER_AGENT = "chrisbmin/cloudmine-pack (https://github.com/chrisbmin/cloudmine-pack)"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


class ReleaseError(Exception):
    pass


def modrinth_versions(version_ids: list[str]) -> dict[str, str]:
    out = {}
    for i in range(0, len(version_ids), 100):
        ids = urllib.parse.quote(json.dumps(version_ids[i:i + 100]))
        req = urllib.request.Request(f"https://api.modrinth.com/v2/versions?ids={ids}",
                                     headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            for v in json.load(resp):
                out[v["id"]] = v["version_number"]
    return out


def snapshot(entries, versions: dict[str, str]) -> list[dict]:
    out = []
    for e in entries:
        cat = category(e)
        url, download = "", e.download
        if e.modrinth_id:
            url = f"https://modrinth.com/project/{e.modrinth_id}"
        elif e.curseforge_project:
            # CurseForge entries have no download url in the pack; members' installers resolve it from the ids.
            url = f"https://www.curseforge.com/projects/{e.curseforge_project}"
            if not download and e.curseforge_file:
                download = (f"https://www.curseforge.com/api/v1/mods/{e.curseforge_project}"
                            f"/files/{e.curseforge_file}/download")
        out.append({
            "id": e.id, "name": e.name or e.id,
            "version": versions.get(e.version_id or "", "") or e.filename,
            "category": cat, "side": e.side,
            "default": e.default if cat == "optional" else None,
            "description": e.description,
            "url": url, "filename": e.filename, "download": download,
        })
    return out


def _short(s: dict) -> dict:
    return {"id": s["id"], "name": s["name"], "version": s["version"]}


def diff(prev: list[dict], cur: list[dict]) -> dict:
    old = {s["id"]: s for s in prev}
    new = {s["id"]: s for s in cur}
    by_name = lambda x: x["name"].lower()  # noqa: E731
    added = sorted((_short(new[i]) for i in new.keys() - old.keys()), key=by_name)
    removed = sorted((_short(old[i]) for i in old.keys() - new.keys()), key=by_name)
    updated = sorted(({"from": _short(old[i]), "to": _short(new[i])} for i in new.keys() & old.keys()
                      if (old[i]["filename"], old[i]["download"]) != (new[i]["filename"], new[i]["download"])),
                     key=lambda u: u["to"]["name"].lower())
    return {"added": added, "removed": removed, "updated": updated}


def server_steps(prev: list[dict], cur: list[dict]) -> dict:
    """Jars to remove from / add to the server's mods/ folder: only mods that run on both sides."""
    def shared(snap):
        return {s["id"]: s for s in snap if s["side"] == "both" and s["category"] in ("core", "optional")}
    old, new = shared(prev), shared(cur)
    remove = [old[i]["filename"] for i in sorted(old) if i not in new or new[i]["filename"] != old[i]["filename"]]
    add = [{"filename": new[i]["filename"], "download": new[i]["download"]} for i in sorted(new)
           if i not in old or old[i]["filename"] != new[i]["filename"]]
    return {"add": add, "remove": remove}


def changelog_entry(version: str, changes: dict, minecraft: str, neoforge: str, notes: str, now: datetime) -> dict:
    return {"ts": int(now.timestamp()), "date": now.strftime("%Y-%m-%d"), "tag": f"CloudMine {version}",
            "track": "cloudmine", "minecraft": minecraft, "loader": f"NeoForge {neoforge}", "notes": notes,
            "changes": changes}


def site_mods(versions_info: dict, released: str, snap: list[dict]) -> dict:
    return {"version": versions_info["version"], "minecraft": versions_info["minecraft"],
            "loader": f"NeoForge {versions_info['neoforge']}", "released": released, "entries": snap}


def _vtuple(v: str) -> tuple:
    return tuple(int(x) for x in v.split("."))


def _count(out: str) -> int:
    out = out.strip()
    return int(out) if out.isdigit() else 0


def guard(repo: Path, version: str, git) -> None:
    if not VERSION_RE.match(version):
        raise ReleaseError(f"version must look like 2.1.0, got {version!r}")
    branch = git(["rev-parse", "--abbrev-ref", "HEAD"]).strip()
    if branch != "testing":
        raise ReleaseError(f"release from the testing branch (you're on {branch!r}): git checkout testing")
    if git(["status", "--porcelain"]).strip():
        raise ReleaseError("there are uncommitted changes: commit and push them to testing first")
    try:
        git(["fetch", "-q", "origin"])
    except subprocess.CalledProcessError:
        raise ReleaseError("couldn't reach GitHub (git fetch failed): check your internet connection and try again")
    if _count(git(["rev-list", "--count", "testing..origin/testing"])):
        raise ReleaseError("GitHub's testing branch has commits you don't have: run git pull first")
    if _count(git(["rev-list", "--count", "main..origin/main"])):
        raise ReleaseError("GitHub's main branch has commits your main doesn't: run git checkout main, git pull, "
                           "git checkout testing, then try again")
    try:
        git(["merge-base", "--is-ancestor", "main", "testing"])
    except subprocess.CalledProcessError:
        raise ReleaseError("main has commits that testing doesn't, so it can't be fast-forwarded: run git merge main "
                           "on testing and push, then try again")
    tag = f"v{version}"
    try:
        remote_tag = git(["ls-remote", "--tags", "origin", tag]).strip()
    except subprocess.CalledProcessError:
        raise ReleaseError("couldn't reach GitHub to check tags: check your internet connection and try again")
    if git(["tag", "-l", tag]).strip() or remote_tag:
        raise ReleaseError(f"{tag} already exists: pick a higher version")
    current = read_versions(repo)["version"]
    if VERSION_RE.match(current) and _vtuple(version) < _vtuple(current):
        raise ReleaseError(f"{version} is lower than the pack's current version {current}")
    if VERSION_RE.match(current) and _vtuple(version) == _vtuple(current) and git(["tag", "-l", f"v{current}"]).strip():
        raise ReleaseError(f"{version} is already released: pick a higher version")
    crlf = parse_eol(git(["ls-files", "--eol"]))
    if crlf:
        raise ReleaseError("these files have Windows (CRLF) line endings and would break members' syncs: "
                           + ", ".join(crlf))


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _print_server_steps(steps: dict) -> None:
    print("\nThis release changes mods that also run on the SERVER. Do these first:")
    print("  1. In Crafty, take a backup of the CloudMine server, then STOP it.")
    n = 2
    if steps["remove"]:
        print(f"  {n}. Delete these jars from the server's mods/ folder:")
        for f in steps["remove"]:
            print(f"       - {f}")
        n += 1
    if steps["add"]:
        print(f"  {n}. Upload these jars into the server's mods/ folder (download each link):")
        for a in steps["add"]:
            print(f"       - {a['filename']}\n         {a['download']}")
        n += 1
    print(f"  {n}. Make sure the new files are owned 1000:0 (Crafty uploads already are).")
    print("  Leave the server stopped. Start it after this release finishes.\n")


def _shown(cmd: list[str]) -> str:
    return "git " + " ".join(f'"{a}"' if " " in a else a for a in cmd if a != "-q")


def _print_recovery(cmds: list[list[str]], failed: int, server: bool) -> None:
    print(f"\nRelease stopped: `{_shown(cmds[failed])}` failed. Nothing is lost.", file=sys.stderr)
    print("Do not pick a new version and don't run release.py again for this one. Fix the cause (usually the "
          "internet connection), then run these from the repo folder, in order:", file=sys.stderr)
    for cmd in cmds[failed:]:
        print(f"    {_shown(cmd)}", file=sys.stderr)
    if server:
        print("Keep the server stopped until the push succeeds, then start it in Crafty.", file=sys.stderr)


def main(argv=None, pack_dir: Path = REPO, git=None, run=subprocess.run, lookup=modrinth_versions, ask=input,
         now=datetime.now) -> int:
    p = argparse.ArgumentParser(description="Release the testing branch to every member.")
    p.add_argument("version", help="new pack version, e.g. 2.1.0")
    p.add_argument("--notes", default="", help="a sentence shown on the changelog (e.g. a NeoForge change)")
    p.add_argument("--dry-run", action="store_true", help="show what would change; change nothing")
    p.add_argument("--server-done", action="store_true", help="server already stopped and updated; don't ask")
    args = p.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):  # mod names can hold emoji the Windows console can't print
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    pack_dir = Path(pack_dir)
    if git is None:
        def git(a):
            return subprocess.run(["git", "-C", str(pack_dir), *a], check=True, capture_output=True, text=True).stdout

    try:
        guard(pack_dir, args.version, git)
    except ReleaseError as e:
        print(f"Not released: {e}", file=sys.stderr)
        return 1

    mods_path = pack_dir / "site-data" / "mods.json"
    log_path = pack_dir / "site-data" / "changelog.json"
    prev = _read_json(mods_path, {}).get("entries", [])
    entries = read_entries(pack_dir)
    cur = snapshot(entries, lookup(sorted({e.version_id for e in entries if e.version_id})))
    changes = diff(prev, cur)
    steps = server_steps(prev, cur)

    print(f"CloudMine {args.version}: {len(changes['added'])} added, {len(changes['updated'])} updated, "
          f"{len(changes['removed'])} removed")
    for kind in ("added", "updated", "removed"):
        for c in changes[kind]:
            label = f"{c['from']['name']} {c['from']['version']} -> {c['to']['version']}" if kind == "updated" \
                else f"{c['name']} {c['version']}"
            print(f"  {kind:8} {label}")
    if steps["add"] or steps["remove"]:
        _print_server_steps(steps)
    if args.dry_run:
        print("Dry run: nothing changed.")
        return 0
    if (steps["add"] or steps["remove"]) and not args.server_done:
        if ask("Type 'stopped' once the server is stopped and its mods are swapped: ").strip() != "stopped":
            print("Not released: the server step wasn't confirmed. Nothing changed.", file=sys.stderr)
            return 1

    run(["packwiz", "refresh"], cwd=pack_dir, check=True)  # not on a dry run, which must change nothing
    set_pack_version(pack_dir, args.version)
    run(["packwiz", "refresh"], cwd=pack_dir, check=True)
    versions_info = read_versions(pack_dir)
    stamp = now()
    _write_json(mods_path, site_mods(versions_info, stamp.strftime("%Y-%m-%d"), cur))
    log = _read_json(log_path, [])
    log.insert(0, changelog_entry(args.version, changes, versions_info["minecraft"], versions_info["neoforge"],
                                  args.notes, stamp))
    _write_json(log_path, log)

    tag = f"v{args.version}"
    publish = [["add", "-A"], ["commit", "-q", "-m", f"Release {args.version}"], ["checkout", "-q", "main"],
               ["merge", "-q", "--ff-only", "testing"], ["tag", tag], ["push", "origin", "main", "testing", tag],
               ["checkout", "-q", "testing"]]
    for i, cmd in enumerate(publish):
        try:
            git(cmd)
        except subprocess.CalledProcessError:
            _print_recovery(publish, i, bool(steps["add"] or steps["remove"]))
            return 1
    print(f"Released CloudMine {args.version}. Members get it the next time they press Play.")
    if steps["add"] or steps["remove"]:
        print("Now start the server in Crafty and join to confirm.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
