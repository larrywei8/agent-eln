import glob
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGoldenWorkflow(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="agent-eln-e2e-")
        for name in ("tools", "templates"):
            shutil.copytree(os.path.join(REPO, name), os.path.join(self.root, name),
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for path in ("eln/experiments", "eln/literature", "eln/ideas", "eln/projects",
                     "lims/plasmids", "lims/mice", "lims/samples", "lims/datasets",
                     "methods/protocols", "methods/pipelines", "methods/scripts", "index"):
            os.makedirs(os.path.join(self.root, path), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def run_tool(self, name, *args):
        proc = subprocess.run([sys.executable, os.path.join(self.root, "tools", name), *args],
                              cwd=self.root, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout

    def test_create_link_backfill_index_validate_trace(self):
        self.run_tool("new.py", "plasmid", "--name", "test vector", "--by", "tester")
        card = glob.glob(os.path.join(self.root, "lims", "plasmids", "PLA-0001-*", "card.md"))[0]
        text = open(card, encoding="utf-8").read().replace("backbone: ", "backbone: pUC\n", 1)
        open(card, "w", encoding="utf-8").write(text)

        self.run_tool("new.py", "experiment-wetlab", "--title", "cloning test", "--by", "tester",
                      "--date", "2099-01-01", "--no-folder")
        exp = glob.glob(os.path.join(self.root, "eln", "experiments", "2099", "2099-01-01", "EXP-*.md"))[0]
        text = open(exp, encoding="utf-8").read().replace("produced_resources: []", "produced_resources: [PLA-0001]")
        open(exp, "w", encoding="utf-8").write(text)

        self.run_tool("backlinks.py", "--write")
        self.assertIn("produced_in: EXP-2099-01-01-01", open(card, encoding="utf-8").read())
        self.run_tool("index.py", "--force")
        self.run_tool("validate.py")
        trace = self.run_tool("trace.py", "PLA-0001")
        self.assertIn("EXP-2099-01-01-01", trace)


if __name__ == "__main__":
    unittest.main()
