import json
import subprocess
import unittest
from datetime import datetime

from tools.packlib import read_entries
from tools.release import (ReleaseError, changelog_entry, diff, guard, main, server_steps, site_mods, snapshot)
from tools.tests.helpers import make_pack, make_repo, pw_toml

NOW = datetime(2026, 10, 21, 12, 0, 0)


def snap(id, filename, side="client", name=None, category="core", default=None, download=None):
    return {"id": id, "name": name or id.title(), "version": filename, "category": category, "side": side,
            "default": default, "description": "", "url": "", "filename": filename,
            "download": download or f"https://cdn.example/{filename}"}


class FakeGit:
    def __init__(self, branch="testing", status="", local_tags="", remote_tags="", eol="i/lf    w/lf    attr/-text\tpack.toml\n"):
        self.replies = {("rev-parse", "--abbrev-ref", "HEAD"): branch, ("status", "--porcelain"): status,
                        ("ls-files", "--eol"): eol}
        self.local_tags, self.remote_tags = local_tags, remote_tags
        self.calls = []

    def __call__(self, args):
        self.calls.append(list(args))
        if args[:2] == ["tag", "-l"]:
            return self.local_tags
        if args[:2] == ["ls-remote", "--tags"]:
            return self.remote_tags
        return self.replies.get(tuple(args), "")


class DiffTests(unittest.TestCase):
    def test_diff_added_removed_updated(self):
        prev = [snap("a", "a-1.jar"), snap("b", "b-1.jar")]
        cur = [snap("a", "a-2.jar"), snap("c", "c-1.jar")]
        d = diff(prev, cur)
        self.assertEqual(d["added"], [{"id": "c", "name": "C", "version": "c-1.jar"}])
        self.assertEqual(d["removed"], [{"id": "b", "name": "B", "version": "b-1.jar"}])
        self.assertEqual(d["updated"], [{"from": {"id": "a", "name": "A", "version": "a-1.jar"},
                                         "to": {"id": "a", "name": "A", "version": "a-2.jar"}}])

    def test_diff_ignores_option_only_changes(self):
        prev = [snap("a", "a.jar", category="optional", default=True)]
        cur = [snap("a", "a.jar", category="optional", default=False)]
        self.assertEqual(diff(prev, cur), {"added": [], "removed": [], "updated": []})


class ServerStepsTests(unittest.TestCase):
    def test_server_steps_client_only_change_is_empty(self):
        self.assertEqual(server_steps([snap("a", "a-1.jar")], [snap("a", "a-2.jar"), snap("n", "n.jar")]),
                         {"add": [], "remove": []})

    def test_server_steps_updated_shared_mod_removes_old_adds_new(self):
        s = server_steps([snap("t", "t-1.jar", side="both")], [snap("t", "t-2.jar", side="both")])
        self.assertEqual(s, {"add": [{"filename": "t-2.jar", "download": "https://cdn.example/t-2.jar"}],
                             "remove": ["t-1.jar"]})

    def test_server_steps_side_change_client_to_both_is_add_and_back_is_remove(self):
        self.assertEqual(server_steps([snap("x", "x.jar")], [snap("x", "x.jar", side="both")]),
                         {"add": [{"filename": "x.jar", "download": "https://cdn.example/x.jar"}], "remove": []})
        self.assertEqual(server_steps([snap("x", "x.jar", side="both")], [snap("x", "x.jar")]),
                         {"add": [], "remove": ["x.jar"]})

    def test_server_steps_removed_shared_mod(self):
        self.assertEqual(server_steps([snap("r", "r.jar", side="both")], []), {"add": [], "remove": ["r.jar"]})

    def test_server_steps_ignore_resource_packs(self):
        rp = snap("rp", "rp.zip", side="both", category="resourcepack")
        self.assertEqual(server_steps([], [rp]), {"add": [], "remove": []})


class SnapshotTests(unittest.TestCase):
    def test_snapshot_version_falls_back_to_filename(self):
        pack = make_pack({
            "mods/sodium.pw.toml": pw_toml("Sodium", "sodium-0.6.jar", side="client", mod_id="AANobbMI", version="vS"),
            "mods/odd.pw.toml": pw_toml("Odd", "odd-1.jar", side="client", mod_id="PO", version="vO"),
            "mods/clouds.pw.toml": pw_toml("Better Clouds", "clouds.jar", side="client", mod_id="PC", version="vC",
                                           option={"optional": True, "default": True, "description": "Nicer clouds"}),
        })
        s = {x["id"]: x for x in snapshot(read_entries(pack), {"vS": "0.6.13", "vC": "1.7"})}
        self.assertEqual(s["sodium"]["version"], "0.6.13")
        self.assertEqual(s["odd"]["version"], "odd-1.jar")
        self.assertIsNone(s["sodium"]["default"])
        self.assertTrue(s["clouds"]["default"])
        self.assertEqual(s["clouds"]["category"], "optional")
        self.assertEqual(s["clouds"]["description"], "Nicer clouds")
        self.assertEqual(s["sodium"]["url"], "https://modrinth.com/project/AANobbMI")
        self.assertEqual(sorted(s["sodium"]), sorted(["id", "name", "version", "category", "side", "default",
                                                      "description", "url", "filename", "download"]))


    def test_snapshot_curseforge_links(self):
        pack = make_pack({"mods/framework.pw.toml": pw_toml("Framework", "framework.jar", side="both", cf=(549225, 7012345))})
        [s] = snapshot(read_entries(pack), {})
        self.assertEqual(s["url"], "https://www.curseforge.com/projects/549225")
        self.assertEqual(s["download"], "https://www.curseforge.com/api/v1/mods/549225/files/7012345/download")
        self.assertEqual(s["version"], "framework.jar")


class ShapeTests(unittest.TestCase):
    def test_changelog_entry_shape(self):
        changes = {"added": [], "removed": [], "updated": []}
        e = changelog_entry("2.1.0", changes, "1.21.1", "21.1.215", "note", NOW)
        self.assertEqual(sorted(e), sorted(["ts", "date", "tag", "track", "minecraft", "loader", "notes", "changes"]))
        self.assertEqual(e["tag"], "CloudMine 2.1.0")
        self.assertEqual(e["track"], "cloudmine")
        self.assertEqual(e["loader"], "NeoForge 21.1.215")
        self.assertEqual(e["date"], "2026-10-21")
        self.assertEqual(e["notes"], "note")
        self.assertIs(e["changes"], changes)

    def test_site_mods_shape(self):
        m = site_mods({"version": "2.0.0", "minecraft": "1.21.1", "neoforge": "21.1.215"}, "2026-10-21", [])
        self.assertEqual(m, {"version": "2.0.0", "minecraft": "1.21.1", "loader": "NeoForge 21.1.215",
                             "released": "2026-10-21", "entries": []})


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.pack = make_pack()  # pack.toml version 2.0.0

    def test_guard_wrong_branch(self):
        with self.assertRaisesRegex(ReleaseError, "testing"):
            guard(self.pack, "2.1.0", FakeGit(branch="main"))

    def test_guard_dirty_tree(self):
        with self.assertRaisesRegex(ReleaseError, "uncommitted"):
            guard(self.pack, "2.1.0", FakeGit(status=" M pack.toml"))

    def test_guard_existing_tag_local(self):
        with self.assertRaisesRegex(ReleaseError, "v2.1.0"):
            guard(self.pack, "2.1.0", FakeGit(local_tags="v2.1.0"))

    def test_guard_existing_tag_remote(self):
        with self.assertRaisesRegex(ReleaseError, "v2.1.0"):
            guard(self.pack, "2.1.0", FakeGit(remote_tags="abc\trefs/tags/v2.1.0"))

    def test_guard_version_not_greater(self):
        for bad in ("1.9.9", "2.0", "x"):
            with self.assertRaises(ReleaseError):
                guard(self.pack, bad, FakeGit(local_tags="v2.0.0"))

    def test_guard_equal_version_only_without_tag(self):
        guard(self.pack, "2.0.0", FakeGit())  # first release: allowed
        with self.assertRaises(ReleaseError):
            guard(self.pack, "2.0.0", FakeGit(local_tags="v2.0.0"))

    def test_guard_unreachable_origin_is_release_error(self):
        def git(args):
            if args[0] == "ls-remote":
                raise subprocess.CalledProcessError(128, ["git", *args])
            return FakeGit()(args)
        with self.assertRaisesRegex(ReleaseError, "GitHub"):
            guard(self.pack, "2.1.0", git)

    def test_guard_greater_version_ok(self):
        guard(self.pack, "2.0.10", FakeGit())

    def test_guard_crlf(self):
        repo = make_repo({"pack.toml": (self.pack / "pack.toml").read_bytes(), "config/x.json5": b"a\r\nb\r\n"})

        def real_git(args):
            if args[0] == "ls-remote":
                return ""  # throwaway repo has no origin
            return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout

        with self.assertRaisesRegex(ReleaseError, "config/x.json5"):
            guard(repo, "2.1.0", real_git)


def writes(calls):
    """git calls that change something (tag -l is a read)."""
    return [c for c in calls if c[0] in ("add", "commit", "checkout", "merge", "tag", "push") and c[:2] != ["tag", "-l"]]


class MainTests(unittest.TestCase):
    def setUp(self):
        self.pack = make_pack({
            "mods/terralith.pw.toml": pw_toml("Terralith", "Terralith-2.6.jar", side="both", mod_id="PT", version="vT"),
            "mods/sodium.pw.toml": pw_toml("Sodium", "sodium.jar", side="client", mod_id="PS", version="vS"),
        })
        self.runs = []

    def call(self, argv, git=None, answer="stopped"):
        self.git = git or FakeGit()
        return main(argv, pack_dir=self.pack, git=self.git, run=lambda cmd, **k: self.runs.append(cmd),
                    lookup=lambda ids: {"vT": "2.6.0", "vS": "0.6.13"}, ask=lambda prompt: answer, now=lambda: NOW)

    def state(self):
        return {p.relative_to(self.pack).as_posix(): p.read_bytes() for p in self.pack.rglob("*") if p.is_file()}

    def test_main_requires_stopped_for_server_steps(self):
        before = self.state()
        self.assertEqual(self.call(["2.1.0"], answer="no"), 1)
        self.assertEqual(self.state(), before)
        self.assertEqual(writes(self.git.calls), [])

    def test_main_dry_run_writes_nothing(self):
        before = self.state()
        self.assertEqual(self.call(["2.1.0", "--dry-run"]), 0)
        self.assertEqual(self.state(), before)
        self.assertEqual(writes(self.git.calls), [])

    def test_main_full_release_order(self):
        self.assertEqual(self.call(["2.1.0", "--notes", "Hello"]), 0)
        mods = json.loads((self.pack / "site-data" / "mods.json").read_text(encoding="utf-8"))
        self.assertEqual(mods["version"], "2.1.0")
        self.assertEqual([e["id"] for e in mods["entries"]], ["sodium", "terralith"])
        log = json.loads((self.pack / "site-data" / "changelog.json").read_text(encoding="utf-8"))
        self.assertEqual(log[0]["tag"], "CloudMine 2.1.0")
        self.assertEqual(log[0]["notes"], "Hello")
        self.assertEqual(len(log[0]["changes"]["added"]), 2)
        self.assertIn('version = "2.1.0"', (self.pack / "pack.toml").read_text(encoding="utf-8"))
        self.assertEqual(writes(self.git.calls), [
            ["add", "-A"], ["commit", "-q", "-m", "Release 2.1.0"], ["checkout", "-q", "main"],
            ["merge", "-q", "--ff-only", "testing"], ["tag", "v2.1.0"], ["push", "origin", "main", "testing", "v2.1.0"],
            ["checkout", "-q", "testing"]])
        self.assertEqual(self.runs.count(["packwiz", "refresh"]), 2)

    def test_main_second_release_prepends_changelog_and_skips_server_for_client_change(self):
        self.assertEqual(self.call(["2.1.0"]), 0)
        (self.pack / "mods" / "sodium.pw.toml").write_text(
            pw_toml("Sodium", "sodium-2.jar", side="client", mod_id="PS", version="vS2"), encoding="utf-8")
        asked = []
        self.git = FakeGit()
        code = main(["2.2.0"], pack_dir=self.pack, git=self.git, run=lambda cmd, **k: None,
                    lookup=lambda ids: {}, ask=lambda p: asked.append(p) or "no", now=lambda: NOW)
        self.assertEqual(code, 0)
        self.assertEqual(asked, [])  # no shared change -> no server prompt
        log = json.loads((self.pack / "site-data" / "changelog.json").read_text(encoding="utf-8"))
        self.assertEqual([e["tag"] for e in log], ["CloudMine 2.2.0", "CloudMine 2.1.0"])
        self.assertEqual([u["to"]["id"] for u in log[0]["changes"]["updated"]], ["sodium"])

    def test_main_guard_failure_exits_1(self):
        self.assertEqual(self.call(["2.1.0"], git=FakeGit(branch="main")), 1)


if __name__ == "__main__":
    unittest.main()
