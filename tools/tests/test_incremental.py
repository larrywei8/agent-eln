"""Phase 1 test suite —— incremental cache + DuckDB smoke.

How to run (from Projects/ELN):
    python -m unittest tools.tests.test_incremental -v

Each test copies the whole ELN to a tmp directory and runs there, without polluting the real library.
"""
import os, sys, shutil, subprocess, tempfile, unittest, json, csv, glob, re

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN = os.path.join(REPO, "tools", "tests", "golden")

_FIXTURE_EXP = """---
id: EXP-2099-01-01-01
type: experiment
mode: wetlab
date: 2099-01-01
operator: testbot
title: bootstrap fixture
project: none
status: complete
---

# bootstrap fixture

Seed record so tests that inspect record parsing have something to parse on a
fresh clone (no lab data included in the repo).
"""

def _sandbox():
    """Copy the repo's key top-level dirs into a tmp workspace and seed a fixture EXP."""
    tmp = tempfile.mkdtemp(prefix="eln-test-")
    # shared code + templates
    for name in ("tools", "templates"):
        src = os.path.join(REPO, name)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(tmp, name),
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    # empty seed directories
    for sub in ("experiments", "meetings", "ideas", "projects",
                "protocols", "pipelines", "scripts", "skills",
                "literature", "reports"):
        os.makedirs(os.path.join(tmp, "eln", sub), exist_ok=True)
    for sub in ("plasmids", "oligos", "dna", "samples", "mice", "cell-lines",
                "reagents", "antibodies", "chemicals", "recipes", "strains",
                "kits", "viruses", "instruments", "datasets", "persons"):
        os.makedirs(os.path.join(tmp, "lims", sub), exist_ok=True)
    os.makedirs(os.path.join(tmp, "index"), exist_ok=True)
    # seed a fixture EXP so the sandbox has at least one indexable record
    exp_dir = os.path.join(tmp, "eln", "experiments", "2099", "2099-01-01")
    os.makedirs(exp_dir, exist_ok=True)
    fx = os.path.join(exp_dir, "EXP-2099-01-01-01.md")
    with open(fx, "w") as f:
        f.write(_FIXTURE_EXP)
    # pin the mtime to a stable past value; the incremental cache keys on
    # (mtime_ns, size), and a just-written file's mtime is subject to FS
    # rounding on some filesystems (9p/gVisor), which breaks cache hits.
    os.utime(fx, (1_700_000_000, 1_700_000_000))
    return tmp

def _run(root, *args):
    r = subprocess.run([sys.executable, os.path.join(root, "tools", "index.py"), *args],
                       cwd=root, capture_output=True, text=True)
    assert r.returncode == 0, f"index.py failed:\n{r.stdout}\n{r.stderr}"
    return r.stdout + r.stderr

def _count_rows(path):
    with open(path) as f:
        return sum(1 for _ in f) - 1

def _stats(out):
    m = re.search(r"parsed=(\d+) cached=(\d+) dropped=(\d+)", out)
    assert m, f"no stats line in output:\n{out}"
    return {"parsed": int(m.group(1)), "cached": int(m.group(2)), "dropped": int(m.group(3))}


class Phase1Tests(unittest.TestCase):
    def setUp(self):
        self.root = _sandbox()
    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_1_golden_diff(self):
        """Full rebuild output CSV / graph.json must be byte-identical to golden.

        Skipped on fresh installs: goldens are lab-specific and must be
        regenerated locally (see tools/tests/golden/README.md).
        """
        golden_files = [f for f in (os.listdir(GOLDEN) if os.path.isdir(GOLDEN) else [])
                        if not f.startswith((".", "README"))]
        if not golden_files:
            self.skipTest("no golden fixtures; regenerate locally per golden/README.md")
        _run(self.root, "--force")
        for f in golden_files:
            g = os.path.join(GOLDEN, f)
            n = os.path.join(self.root, "index", f)
            self.assertTrue(os.path.exists(n), f"missing output {f}")
            with open(g, "rb") as a, open(n, "rb") as b:
                self.assertEqual(a.read(), b.read(), f"byte diff in {f}")

    def test_2_cache_hit(self):
        """Run twice in a row: second run should have 100% cache hits."""
        _run(self.root, "--stats")   # cold start
        s = _stats(_run(self.root, "--stats"))
        self.assertEqual(s["parsed"], 0, "second run should parse 0 files")
        self.assertGreater(s["cached"], 0)

    def test_3_single_edit(self):
        """After modifying one md, only that file is re-parsed."""
        _run(self.root, "--stats")
        # find one already-indexed .md, append a space to bump mtime + size
        target = None
        for dp, _, fs in os.walk(self.root):
            if "/tools" in dp or "/templates" in dp or "/index" in dp: continue
            for fn in fs:
                if fn.endswith(".md"):
                    target = os.path.join(dp, fn); break
            if target: break
        with open(target, "a") as f: f.write("\n")
        s = _stats(_run(self.root, "--stats"))
        self.assertEqual(s["parsed"], 1, f"expected parsed=1, got {s}")

    def test_4_delete(self):
        """Delete an EXP, records.csv should have one less row."""
        # synthesize an EXP fixture (repo may not have real EXP data)
        exp_dir = os.path.join(self.root, "experiments", "2099", "2099-01-01")
        os.makedirs(exp_dir, exist_ok=True)
        victim = os.path.join(exp_dir, "EXP-2099-01-01-99.md")
        with open(victim, "w") as f:
            f.write("---\nid: EXP-2099-01-01-99\ntype: experiment\nmode: wetlab\n"
                    "date: 2099-01-01\noperator: testbot\ntitle: fixture\n"
                    "project: none\nstatus: complete\n---\n\n# fixture\n")
        _run(self.root)
        n_before = _count_rows(os.path.join(self.root, "index", "records.csv"))
        os.remove(victim)
        _run(self.root)
        n_after = _count_rows(os.path.join(self.root, "index", "records.csv"))
        self.assertEqual(n_after, n_before - 1)

    def test_5_duckdb_smoke(self):
        """data.duckdb records table row count should equal records.csv data row count."""
        try:
            import duckdb
        except ImportError:
            self.skipTest("duckdb not installed")
        _run(self.root)
        n_csv = _count_rows(os.path.join(self.root, "index", "records.csv"))
        con = duckdb.connect(os.path.join(self.root, "index", "data.duckdb"), read_only=True)
        n_db = con.execute("SELECT count(*) FROM records").fetchone()[0]
        con.close()
        self.assertEqual(n_db, n_csv)

    def test_6_registry_change(self):
        """After registry.py is modified, a full rebuild should be triggered."""
        _run(self.root, "--stats")
        reg = os.path.join(self.root, "tools", "registry.py")
        os.utime(reg, None)   # bump mtime
        s = _stats(_run(self.root, "--stats"))
        self.assertGreater(s["parsed"], 0, "registry mtime change should force rebuild")
        self.assertEqual(s["cached"], 0)


if __name__ == "__main__":
    unittest.main()
