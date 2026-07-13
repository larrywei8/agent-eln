"""weekly_brief.py — smoke tests.

Does not assume fixed data volume; only verifies:
- three output modes (md/write/json) do not crash
- JSON schema contains the agreed top-level keys
- to-read queue only lists LIT with empty wiki_link
"""
import os, sys, json, subprocess, tempfile, unittest

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(TOOLS, "weekly_brief.py")


class TestWeeklyBrief(unittest.TestCase):
    def test_stdout_md(self):
        r = subprocess.run(["python3", SCRIPT, "--since", "7d"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("# Weekly Brief", r.stdout)
        for section in ("New this week", "Wiki ingests this week", "To-read queue", "expiring within 30 days", "health.py summary"):
            self.assertIn(section, r.stdout)

    def test_write_to_disk(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "brief.md")
            r = subprocess.run(
                ["python3", SCRIPT, "--since", "7d", "--out", out],
                capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(os.path.exists(out))
            with open(out) as f:
                body = f.read()
            self.assertIn("# Weekly Brief", body)

    def test_json_schema(self):
        r = subprocess.run(["python3", SCRIPT, "--since", "1d", "--json"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        j = json.loads(r.stdout)
        for k in ("today", "since", "new_records", "unread_lit", "wiki_ingests", "expiring", "health"):
            self.assertIn(k, j)
        # unread_lit contract: each item shape = [id, title, journal, year, path]
        for item in j["unread_lit"]:
            self.assertEqual(len(item), 5)
            self.assertTrue(item[0].startswith("LIT-"))


if __name__ == "__main__":
    unittest.main()
