"""today.py — smoke tests.

Verifies:
- three output modes (md/write/json) do not crash
- JSON schema contains the agreed top-level keys and event fields
- --date accepts a past day without error
"""
import os, sys, json, subprocess, tempfile, unittest

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(TOOLS, "today.py")


class TestToday(unittest.TestCase):
    def test_stdout_md(self):
        r = subprocess.run(["python3", SCRIPT], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Lab Day", r.stdout)
        self.assertIn("Counts", r.stdout)

    def test_past_date(self):
        r = subprocess.run(["python3", SCRIPT, "--date", "2000-01-01"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("2000-01-01", r.stdout)

    def test_write_to_disk(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "day.md")
            r = subprocess.run(
                ["python3", SCRIPT, "--out", out],
                capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(os.path.exists(out))
            with open(out) as f:
                body = f.read()
            self.assertIn("Lab Day", body)

    def test_json_schema(self):
        r = subprocess.run(["python3", SCRIPT, "--json"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        j = json.loads(r.stdout)
        for k in ("date", "count", "events"):
            self.assertIn(k, j)
        self.assertEqual(j["count"], len(j["events"]))
        for ev in j["events"]:
            for k in ("time", "kind", "type", "id", "title", "path"):
                self.assertIn(k, ev)
            self.assertIn(ev["kind"], {"created", "edited", "wiki", "commit"})


if __name__ == "__main__":
    unittest.main()
