import hashlib
import tempfile
import unittest
from pathlib import Path

from tools.migrate import apply_plan, build_plan
from tools.packlib import read_entries
from tools.tests.helpers import make_pack, pw_toml


def instance(files):
    """A fake instance minecraft/ dir: {relative path: bytes}."""
    root = Path(tempfile.mkdtemp(prefix="cminst"))
    for rel, data in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    return root


def sha1(data):
    return hashlib.sha1(data).hexdigest()


def fake_lookup(table):
    """table: {bytes: (project_id, version_id, version_number)} -> lookup(hashes) like modrinth_lookup."""
    by_hash = {sha1(k): {"project_id": p, "version_id": v, "version_number": n} for k, (p, v, n) in table.items()}
    return lambda hashes: {h: by_hash[h] for h in hashes if h in by_hash}


class BuildPlanTests(unittest.TestCase):
    def test_tier_is_first_instance_containing_file(self):
        base = instance({"mods/a.jar": b"A"})
        mid = instance({"mods/a.jar": b"A"})
        mx = instance({"mods/a.jar": b"A", "mods/z.jar": b"Z", "shaderpacks/s.zip": b"S"})
        server = instance({})
        plan = build_plan([("base", base), ("mid", mid), ("max", mx)], server,
                          fake_lookup({b"A": ("PA", "va", "1"), b"Z": ("PZ", "vz", "1"), b"S": ("PS", "vs", "1")}))
        tiers = {e["file"]: (e["tier"], e["folder"]) for e in plan["entries"]}
        self.assertEqual(tiers, {"a.jar": ("base", "mods"), "z.jar": ("max", "mods"), "s.zip": ("max", "shaderpacks")})

    def test_shared_detected_and_mismatch_reported(self):
        base = instance({"mods/jade-2.jar": b"J2"})
        server = instance({"jade-1.jar": b"J1"})
        plan = build_plan([("base", base)], server, fake_lookup({b"J2": ("PJ", "v2", "15.10.3"), b"J1": ("PJ", "v1", "15.10.2")}))
        [e] = plan["entries"]
        self.assertTrue(e["shared"])
        self.assertEqual(plan["mismatched"], [{"project_id": "PJ", "client_file": "jade-2.jar", "client_version": "15.10.3",
                                               "server_file": "jade-1.jar", "server_version": "15.10.2"}])

    def test_unresolved_files_listed_not_entries(self):
        base = instance({"mods/known.jar": b"K", "mods/mystery.jar": b"M"})
        plan = build_plan([("base", base)], instance({}), fake_lookup({b"K": ("PK", "vk", "1")}))
        self.assertEqual([e["file"] for e in plan["entries"]], ["known.jar"])
        self.assertEqual(plan["unresolved"], [{"file": "mystery.jar", "folder": "mods", "tier": "base", "shared": False}])

    def test_unresolved_shared_by_filename(self):
        base = instance({"mods/furniture.jar": b"F"})
        server = instance({"furniture.jar": b"F"})
        plan = build_plan([("base", base)], server, fake_lookup({}))
        self.assertEqual(plan["unresolved"], [{"file": "furniture.jar", "folder": "mods", "tier": "base", "shared": True}])
        self.assertEqual(plan["server_only"], [])

    def test_server_only_jars_reported(self):
        base = instance({"mods/a.jar": b"A"})
        server = instance({"a.jar": b"A", "lithium.jar": b"L"})
        plan = build_plan([("base", base)], server, fake_lookup({b"A": ("PA", "va", "1"), b"L": ("PL", "vl", "0.15")}))
        self.assertEqual(plan["server_only"], ["lithium.jar"])

    def test_server_only_latest_reported(self):
        base = instance({})
        server = instance({"lithium.jar": b"L"})
        latest = {"PL": {"version_id": "vl2", "version_number": "0.16", "filename": "lithium-0.16.jar",
                         "url": "https://cdn.modrinth.com/l.jar"}}
        plan = build_plan([("base", base)], server, fake_lookup({b"L": ("PL", "vl", "0.15")}), latest=latest.get)
        self.assertEqual(plan["server_only_latest"], [{"file": "lithium.jar", "project_id": "PL", "version_number": "0.16",
                                                       "url": "https://cdn.modrinth.com/l.jar"}])


class ApplyPlanTests(unittest.TestCase):
    def test_apply_plan_commands_and_marks(self):
        pack = make_pack()
        plan = {"entries": [
            {"file": "terra.jar", "folder": "mods", "tier": "base", "project_id": "PT", "shared": True},
            {"file": "sodium.jar", "folder": "mods", "tier": "base", "project_id": "PS", "shared": False},
            {"file": "sounds.jar", "folder": "mods", "tier": "max", "project_id": "PX", "shared": False},
            {"file": "leaves.zip", "folder": "resourcepacks", "tier": "mid", "project_id": "PR", "shared": False},
        ]}
        slugs = {"PT": ("mods", "terralith"), "PS": ("mods", "sodium"), "PX": ("mods", "sounds"),
                 "PR": ("resourcepacks", "better-leaves")}
        calls = []

        def run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[:3] == ["packwiz", "modrinth", "add"]:
                pid = cmd[cmd.index("--project-id") + 1]
                folder, slug = slugs[pid]
                p = pack / folder / f"{slug}.pw.toml"
                p.parent.mkdir(exist_ok=True)
                p.write_text(pw_toml(slug, slug + ".jar", side="both", mod_id=pid, version="v"), encoding="utf-8")

        apply_plan(plan, pack, run)
        adds = [c for c in calls if c[:3] == ["packwiz", "modrinth", "add"]]
        self.assertEqual(len(adds), 4)
        self.assertTrue(all("--version-id" not in c and "-y" in c for c in adds))
        self.assertEqual(calls[-2:], [["packwiz", "update", "--all", "-y"], ["packwiz", "refresh"]])

        e = {x.id: x for x in read_entries(pack)}
        self.assertEqual(e["terralith"].side, "both")
        self.assertEqual(e["sodium"].side, "client")
        self.assertFalse(e["sodium"].optional)
        self.assertTrue(e["sounds"].optional)
        self.assertFalse(e["sounds"].default)
        self.assertFalse(e["better-leaves"].optional)

    def test_apply_plan_skips_project_already_present_and_marks_dependency_client(self):
        pack = make_pack({"mods/creativecore.pw.toml": pw_toml("CreativeCore", "cc.jar", side="both", mod_id="PC", version="v")})
        plan = {"entries": [{"file": "cc.jar", "folder": "mods", "tier": "max", "project_id": "PC", "shared": False}]}
        calls = []
        apply_plan(plan, pack, lambda cmd, **k: calls.append(cmd))
        self.assertFalse(any(c[:3] == ["packwiz", "modrinth", "add"] for c in calls))
        [cc] = read_entries(pack)
        self.assertEqual(cc.side, "client")


if __name__ == "__main__":
    unittest.main()
