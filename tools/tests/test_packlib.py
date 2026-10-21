import unittest

from tools.packlib import category, crlf_files, read_entries, read_versions, set_pack_version
from tools.tests.helpers import make_pack, make_repo, pw_toml


class PackReaderTests(unittest.TestCase):
    def test_read_entries_parses_option_and_side(self):
        pack = make_pack({"mods/sodium.pw.toml": pw_toml(
            "Sodium", "sodium.jar", side="client", mod_id="AANobbMI", version="v1",
            option={"optional": True, "default": True, "description": "Fast"})})
        [e] = read_entries(pack)
        self.assertEqual(e.id, "sodium")
        self.assertEqual(e.folder, "mods")
        self.assertEqual(e.name, "Sodium")
        self.assertEqual(e.filename, "sodium.jar")
        self.assertEqual(e.side, "client")
        self.assertEqual(e.download, "https://cdn.example/x.jar")
        self.assertEqual(e.modrinth_id, "AANobbMI")
        self.assertEqual(e.version_id, "v1")
        self.assertTrue(e.optional)
        self.assertTrue(e.default)
        self.assertEqual(e.description, "Fast")
        self.assertEqual(category(e), "optional")

    def test_missing_side_and_option_defaults(self):
        pack = make_pack({"mods/jei.pw.toml": pw_toml("JEI", "jei.jar")})
        [e] = read_entries(pack)
        self.assertEqual(e.side, "both")
        self.assertFalse(e.optional)
        self.assertFalse(e.default)
        self.assertEqual(e.description, "")
        self.assertIsNone(e.modrinth_id)
        self.assertIsNone(e.version_id)
        self.assertEqual(category(e), "core")

    def test_read_entries_curseforge_ids(self):
        pack = make_pack({"mods/framework.pw.toml": pw_toml("Framework", "framework.jar", side="both", cf=(549225, 7012345))})
        [e] = read_entries(pack)
        self.assertEqual((e.curseforge_project, e.curseforge_file), (549225, 7012345))
        self.assertEqual(e.download, "")
        self.assertIsNone(e.modrinth_id)

    def test_resourcepack_and_shader_categories(self):
        pack = make_pack({
            "resourcepacks/leaves.pw.toml": pw_toml("Leaves", "leaves.zip"),
            "shaderpacks/comp.pw.toml": pw_toml("Complementary", "comp.zip"),
        })
        cats = {e.id: category(e) for e in read_entries(pack)}
        self.assertEqual(cats, {"comp": "shader", "leaves": "resourcepack"})

    def test_entries_sorted_by_id(self):
        pack = make_pack({
            "mods/zeta.pw.toml": pw_toml("Zeta", "z.jar"),
            "resourcepacks/alpha.pw.toml": pw_toml("Alpha", "a.zip"),
            "mods/mid.pw.toml": pw_toml("Mid", "m.jar"),
        })
        self.assertEqual([e.id for e in read_entries(pack)], ["alpha", "mid", "zeta"])

    def test_set_pack_version_changes_only_top_level_version(self):
        pack = make_pack()
        set_pack_version(pack, "2.1.0")
        self.assertEqual(read_versions(pack), {"version": "2.1.0", "minecraft": "1.21.1", "neoforge": "21.1.215"})

    def test_crlf_files_flags_crlf(self):
        repo = make_repo({"lf.txt": b"a\nb\n", "config/crlf.json5": b"a\r\nb\r\n"})
        self.assertEqual(crlf_files(repo), ["config/crlf.json5"])


if __name__ == "__main__":
    unittest.main()
