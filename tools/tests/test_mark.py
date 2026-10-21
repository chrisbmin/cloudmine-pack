import tomllib
import unittest

from tools.mark import main, set_option, set_required, set_side
from tools.packlib import read_entries
from tools.tests.helpers import make_pack, pw_toml


def one_entry(pack):
    [e] = read_entries(pack)
    return e


class MarkTests(unittest.TestCase):
    def setUp(self):
        self.pack = make_pack({"mods/leaves.pw.toml": pw_toml("Falling Leaves", "leaves.jar", side="client",
                                                              mod_id="P", version="V")})
        self.pw = self.pack / "mods" / "leaves.pw.toml"

    def test_set_option_round_trips(self):
        set_option(self.pw, True, 'Adds "falling" leaves \\ and more')
        e = one_entry(self.pack)
        self.assertTrue(e.optional)
        self.assertTrue(e.default)
        self.assertEqual(e.description, 'Adds "falling" leaves \\ and more')
        with self.pw.open("rb") as f:
            tomllib.load(f)

    def test_set_option_emoji_description_parses(self):
        set_option(self.pw, False, "Zoom \U0001f50d like a spyglass")
        self.assertEqual(one_entry(self.pack).description, "Zoom \U0001f50d like a spyglass")

    def test_set_option_control_character_refused_and_file_unchanged(self):
        before = self.pw.read_bytes()
        with self.assertRaises(ValueError):
            set_option(self.pw, False, "bad\x7fdescription")
        with self.assertRaises(ValueError):
            set_option(self.pw, False, "two\nlines")
        self.assertEqual(self.pw.read_bytes(), before)

    def test_set_option_twice_keeps_one_option_table(self):
        set_option(self.pw, True, "one")
        set_option(self.pw, False, "two")
        text = self.pw.read_text(encoding="utf-8")
        self.assertEqual(text.count("[option]"), 1)
        e = one_entry(self.pack)
        self.assertFalse(e.default)
        self.assertEqual(e.description, "two")

    def test_set_required_removes_option(self):
        set_option(self.pw, True, "x")
        set_required(self.pw)
        self.assertNotIn("[option]", self.pw.read_text(encoding="utf-8"))
        self.assertFalse(one_entry(self.pack).optional)

    def test_set_side_replaces_and_inserts(self):
        before = one_entry(self.pack)
        set_side(self.pw, "both")
        after = one_entry(self.pack)
        self.assertEqual(after.side, "both")
        self.assertEqual((after.download, after.hash, after.modrinth_id), (before.download, before.hash, before.modrinth_id))
        self.assertEqual(self.pw.read_text(encoding="utf-8").count("side ="), 1)

        pw2 = self.pack / "mods" / "jei.pw.toml"
        pw2.write_text(pw_toml("JEI", "jei.jar"), encoding="utf-8", newline="\n")
        set_side(pw2, "client")
        with pw2.open("rb") as f:
            data = tomllib.load(f)
        self.assertEqual(data["side"], "client")
        self.assertEqual(data["download"]["url"], "https://cdn.example/x.jar")

    def test_unknown_id_exits_2_and_changes_nothing(self):
        before = {p: p.read_bytes() for p in self.pack.rglob("*") if p.is_file()}
        calls = []
        code = main(["nope", "--required"], pack_dir=self.pack, run=lambda *a, **k: calls.append(a))
        after = {p: p.read_bytes() for p in self.pack.rglob("*") if p.is_file()}
        self.assertEqual(code, 2)
        self.assertEqual(before, after)
        self.assertEqual(calls, [])

    def test_cli_optional_refreshes(self):
        calls = []
        code = main(["leaves", "--optional", "--default", "on", "--description", "Leaves fall"],
                    pack_dir=self.pack, run=lambda cmd, **k: calls.append(cmd))
        self.assertEqual(code, 0)
        self.assertEqual(calls, [["packwiz", "refresh"]])
        e = one_entry(self.pack)
        self.assertTrue(e.optional and e.default)
        self.assertEqual(e.description, "Leaves fall")


if __name__ == "__main__":
    unittest.main()
