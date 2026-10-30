"""Run disk-power-stats on a recorded set of smartd journal entries.

    python3 -m unittest discover tests
"""
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*args):
    return subprocess.run(
        [str(ROOT / "disk-power-stats"), "--input", str(ROOT / "tests" / "smartd-journal.json"), *args],
        capture_output=True, text=True, check=True, env={**os.environ, "TZ": "UTC"},
    ).stdout


class Stats(unittest.TestCase):
    def test_summary(self):
        out = run()
        self.assertIn("period 2026-12-30 08:00 .. 2026-12-31 14:00 (30h00)", out)
        # two naps: 1h30 and 20 min
        self.assertRegex(out, r"/dev/sda +SERIALA +2 +2 +1h50 +6\.1 +20min +1h30")
        # 24 h until the forced check, 25 min until smartd's restart, 3h20 still asleep at the end
        self.assertRegex(out, r"/dev/sdb +SERIALB +3 +2 +27h45 +92\.5 +25min +3h20")
        self.assertIn("(/dev/sdb is still asleep)", out)

    def test_per_day_and_hour(self):
        out = run()
        self.assertRegex(out, r"2026-12-30 +2 +0")
        self.assertRegex(out, r"2026-12-31 +0 +2")
        self.assertRegex(out, r"10:00 +1 +1")

    def test_events(self):
        out = run("--events")
        self.assertIn("2026-12-31 09:00:00  /dev/sdb   spin-up (forced smartd check)", out)
        self.assertIn("2026-12-31 10:00:00  /dev/sdb   spin-up (smartd start)", out)
        self.assertEqual(out.count("spin-down"), 5)

    def test_no_events(self):
        out = subprocess.run([str(ROOT / "disk-power-stats"), "--input", "-"], input="",
                             capture_output=True, text=True, check=True).stdout
        self.assertIn("no smartd journal entries", out)


if __name__ == "__main__":
    unittest.main()
