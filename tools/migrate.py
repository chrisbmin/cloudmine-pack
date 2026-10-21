"""One-time import of the CloudMine v1.0.4 Prism instances (Base, Mid, Max) into this packwiz pack.

    python tools/migrate.py plan --base DIR --mid DIR --max DIR --server-mods DIR --out migration-plan.json
    python tools/migrate.py apply migration-plan.json

Each DIR is an instance's minecraft/ folder. `plan` looks every jar/zip up on Modrinth by hash and writes a
plan for review; `apply` adds every resolved project at its LATEST 1.21.1 NeoForge version, marks shared mods
(also on the server) side = both and everything else side = client, and marks Mid/Max mods optional (off).
Nothing unresolved is ever added; the owner decides those by hand.
"""
import argparse
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))  # so `python tools/migrate.py` can import the tools package

from tools.mark import set_option, set_side  # noqa: E402
from tools.packlib import read_entries  # noqa: E402

USER_AGENT = "chrisbmin/cloudmine-pack (https://github.com/chrisbmin/cloudmine-pack)"
API = "https://api.modrinth.com/v2"
SCAN = (("mods", "*.jar"), ("resourcepacks", "*.zip"), ("shaderpacks", "*.zip"))


def sha1_file(path: Path) -> str:
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()


def _request(url: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def modrinth_lookup(hashes: list[str]) -> dict[str, dict]:
    out = {}
    for i in range(0, len(hashes), 100):
        found = _request(f"{API}/version_files", {"hashes": hashes[i:i + 100], "algorithm": "sha1"})
        for h, v in found.items():
            out[h] = {"project_id": v["project_id"], "version_id": v["id"], "version_number": v["version_number"]}
    return out


def latest_version(project_id: str) -> dict | None:
    query = urllib.parse.urlencode({"loaders": '["neoforge"]', "game_versions": '["1.21.1"]'})
    versions = _request(f"{API}/project/{project_id}/version?{query}")
    if not versions:
        return None
    v = versions[0]
    files = v.get("files", [])
    f = next((x for x in files if x.get("primary")), files[0] if files else {})
    return {"version_id": v["id"], "version_number": v["version_number"], "filename": f.get("filename", ""),
            "url": f.get("url", "")}


def build_plan(instances: list[tuple[str, Path]], server_mods: Path, lookup, latest=None) -> dict:
    # Client files: first tier that has each (folder, filename).
    client = {}
    for tier, root in instances:
        for folder, pattern in SCAN:
            for path in sorted((Path(root) / folder).glob(pattern)):
                client.setdefault((folder, path.name), {"tier": tier, "sha1": sha1_file(path)})
    server = {p.name: sha1_file(p) for p in sorted(Path(server_mods).glob("*.jar"))}

    found = lookup(sorted({c["sha1"] for c in client.values()} | set(server.values())))
    server_by_project = {}
    for name, h in server.items():
        if h in found:
            server_by_project[found[h]["project_id"]] = (name, found[h])

    plan = {"entries": [], "unresolved": [], "mismatched": [], "server_only": [], "server_only_latest": []}
    client_projects, client_names = set(), set()
    for (folder, name), info in client.items():
        client_names.add(name)
        hit = found.get(info["sha1"])
        if hit is None:
            plan["unresolved"].append({"file": name, "folder": folder, "tier": info["tier"],
                                       "shared": folder == "mods" and name in server})
            continue
        pid = hit["project_id"]
        client_projects.add(pid)
        shared = folder == "mods" and pid in server_by_project
        plan["entries"].append({"file": name, "folder": folder, "tier": info["tier"], "project_id": pid,
                                "version_id": hit["version_id"], "version_number": hit["version_number"],
                                "shared": shared})
        if shared:
            s_name, s_hit = server_by_project[pid]
            if s_hit["version_id"] != hit["version_id"]:
                plan["mismatched"].append({"project_id": pid, "client_file": name,
                                           "client_version": hit["version_number"], "server_file": s_name,
                                           "server_version": s_hit["version_number"]})

    for name, h in server.items():
        hit = found.get(h)
        if (hit and hit["project_id"] in client_projects) or (not hit and name in client_names):
            continue
        plan["server_only"].append(name)
        if hit and latest is not None:
            newest = latest(hit["project_id"])
            if newest:
                plan["server_only_latest"].append({"file": name, "project_id": hit["project_id"],
                                                   "version_number": newest["version_number"], "url": newest["url"]})
    for key in ("entries", "unresolved"):
        plan[key].sort(key=lambda e: (e["folder"], e["file"].lower()))
    return plan


def apply_plan(plan: dict, pack_dir: Path, run) -> None:
    pack_dir = Path(pack_dir)
    present = {e.modrinth_id for e in read_entries(pack_dir)}
    for e in plan["entries"]:
        if e["project_id"] in present:
            continue  # already in the pack, e.g. pulled in as another mod's dependency
        run(["packwiz", "modrinth", "add", "--project-id", e["project_id"], "-y"], cwd=pack_dir, check=True)
        present = {x.modrinth_id for x in read_entries(pack_dir)}

    by_project = {e["project_id"]: e for e in plan["entries"]}
    for entry in read_entries(pack_dir):
        pw = pack_dir / entry.folder / f"{entry.id}.pw.toml"
        planned = by_project.get(entry.modrinth_id)
        set_side(pw, "both" if planned and planned["shared"] else "client")
        if planned and entry.folder == "mods" and planned["tier"] in ("mid", "max"):
            set_option(pw, False, "")
    run(["packwiz", "update", "--all", "-y"], cwd=pack_dir, check=True)
    run(["packwiz", "refresh"], cwd=pack_dir, check=True)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="One-time import of the v1.0.4 Prism instances.")
    sub = p.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("plan", help="look everything up and write a plan to review")
    for tier in ("base", "mid", "max"):
        pp.add_argument(f"--{tier}", required=True, type=Path, help=f"{tier} instance minecraft/ folder")
    pp.add_argument("--server-mods", required=True, type=Path, help="the server's mods/ folder (local mirror)")
    pp.add_argument("--out", default="migration-plan.json", type=Path)
    pa = sub.add_parser("apply", help="add everything in a reviewed plan to the pack")
    pa.add_argument("plan", type=Path)
    args = p.parse_args(argv)

    if args.cmd == "plan":
        plan = build_plan([("base", args.base), ("mid", args.mid), ("max", args.max)], args.server_mods,
                          modrinth_lookup, latest=latest_version)
        args.out.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        print(f"entries {len(plan['entries'])}, unresolved {len(plan['unresolved'])}, "
              f"mismatched {len(plan['mismatched'])}, server_only {len(plan['server_only'])} -> {args.out}")
    else:
        import subprocess
        apply_plan(json.loads(args.plan.read_text(encoding="utf-8")), REPO, subprocess.run)
        print("applied; review with `packwiz list` and `git status`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
