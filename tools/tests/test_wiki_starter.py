import os
import subprocess
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(ROOT, "wiki", "scripts", "knowledge_pm.py")


class TestWikiStarter(unittest.TestCase):
    def test_health_accepts_repository_root(self):
        proc = subprocess.run(
            [sys.executable, SCRIPT, "--mode", "health", "--root", ROOT],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_health_accepts_wiki_directory(self):
        proc = subprocess.run(
            [sys.executable, SCRIPT, "--mode", "health", "--root", os.path.join(ROOT, "wiki")],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
