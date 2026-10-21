import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


class ScriptsRunDirectlyTests(unittest.TestCase):
    """The runbooks run `python tools/<script>.py`, not `python -m`; the scripts must import from there."""

    def check(self, script):
        r = subprocess.run([sys.executable, str(REPO / "tools" / script), "--help"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_mark_help(self):
        self.check("mark.py")

    def test_migrate_help(self):
        self.check("migrate.py")

    def test_build_starter_help(self):
        self.check("build_starter.py")

    def test_release_help(self):
        self.check("release.py")


if __name__ == "__main__":
    unittest.main()
