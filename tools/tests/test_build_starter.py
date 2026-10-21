import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.build_starter import build, render_cfg, servers_dat

REPO = Path(__file__).resolve().parents[2]
MAIN_URL = "https://raw.githubusercontent.com/chrisbmin/cloudmine-pack/main/pack.toml"


class StarterTests(unittest.TestCase):
    def test_servers_dat_exact_bytes(self):
        self.assertEqual(
            servers_dat([("A", "b")]),
            b"\x0a\x00\x00" + b"\x09\x00\x07servers" + b"\x0a" + b"\x00\x00\x00\x01"
            + b"\x08\x00\x04name\x00\x01A" + b"\x08\x00\x02ip\x00\x01b" + b"\x00" + b"\x00")

    def test_render_cfg_sets_url_and_name(self):
        out = render_cfg("name={{NAME}}\nPreLaunchCommand=x {{PACK_URL}}\n", "CloudMine", MAIN_URL)
        self.assertEqual(out, f"name=CloudMine\nPreLaunchCommand=x {MAIN_URL}\n")

    def test_build_zip_layout(self):
        out = Path(tempfile.mkdtemp()) / "s.zip"
        build(REPO / "starter", out, "CloudMine", MAIN_URL)
        with zipfile.ZipFile(out) as z:
            self.assertEqual(sorted(z.namelist()), sorted([
                "instance.cfg", "mmc-pack.json", "cloudmine.png",
                "minecraft/packwiz-installer-bootstrap.jar", "minecraft/servers.dat", "minecraft/options.txt"]))
            cfg = z.read("instance.cfg").decode()
            self.assertIn(f'PreLaunchCommand="$INST_JAVA" -jar packwiz-installer-bootstrap.jar {MAIN_URL}', cfg)
            self.assertIn("iconKey=cloudmine", cfg)
            self.assertIn("name=CloudMine\n", cfg)
            self.assertIn(b"play.cloudmine.thecoldnorth.net", z.read("minecraft/servers.dat"))

    def test_starter_folder_is_packwizignored(self):
        lines = (REPO / ".packwizignore").read_text(encoding="utf-8").split()
        self.assertIn("starter/", lines)


if __name__ == "__main__":
    unittest.main()
