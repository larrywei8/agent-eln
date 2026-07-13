"""Phase 3 test suite —— literature closed loop (LIT ingest + wiki sync + health).

How to run (from Projects/ELN):
    python -m unittest tools.tests.test_phase3 -v

Each test runs in a temporary sandbox, without polluting the real library or knowledge/wiki.
Crossref network calls are monkey-patched; no network required.
"""
import os, sys, shutil, subprocess, tempfile, unittest, json, re, importlib.util

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "phase3")


def _sandbox(with_workspace=False):
    """Copy the whole agent-eln repo layout into a tmp directory.

    Layout mirrors the real one: tools/, templates/, index/, references/ at root;
    eln/ holds activities; lims/ holds inventory. `with_workspace=True` also
    seeds an empty wiki/summaries/ (for cross-sync tests).

    Kept legacy return signature (tmp_ws, root) — under the new layout both are
    the same path because there is no wrapper directory.
    """
    tmp_ws = tempfile.mkdtemp(prefix="eln-p3-ws-")
    # copy shared code + templates + references
    for name in ("tools", "templates", "references"):
        src = os.path.join(REPO, name)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(tmp_ws, name),
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    # seed empty data directories
    for sub in ("experiments", "meetings", "ideas", "projects",
                "protocols", "pipelines", "scripts", "skills",
                "literature", "reports"):
        os.makedirs(os.path.join(tmp_ws, "eln", sub), exist_ok=True)
    for sub in ("plasmids", "oligos", "dna", "samples", "mice", "cell-lines",
                "reagents", "antibodies", "chemicals", "recipes", "strains",
                "kits", "viruses", "instruments", "datasets", "persons"):
        os.makedirs(os.path.join(tmp_ws, "lims", sub), exist_ok=True)
    os.makedirs(os.path.join(tmp_ws, "index"), exist_ok=True)
    if with_workspace:
        os.makedirs(os.path.join(tmp_ws, "wiki", "summaries"), exist_ok=True)
    return tmp_ws, tmp_ws


def _run(root, script, *args, env_override=None, expect_zero=True):
    env = os.environ.copy()
    if env_override: env.update(env_override)
    r = subprocess.run([sys.executable, os.path.join(root, "tools", script), *args],
                       cwd=root, capture_output=True, text=True, env=env)
    if expect_zero:
        assert r.returncode == 0, f"{script} {args} failed\nstdout: {r.stdout}\nstderr: {r.stderr}"
    return r


class DoiIngestTests(unittest.TestCase):
    def setUp(self):
        self.ws, self.root = _sandbox()
    def tearDown(self):
        shutil.rmtree(self.ws, ignore_errors=True)

    def test_1_doi_stub_happy_path(self):
        """--stub mode does not need network, writes a valid LIT card."""
        r = _run(self.root, "lit_from_doi.py", "10.1038/nature12345",
                 "--stub", "--by", "test", "--no-index")
        self.assertIn("LIT-0001", r.stdout)
        cards = [f for f in os.listdir(os.path.join(self.root, "eln", "literature")) if f.startswith("LIT-0001")]
        self.assertEqual(len(cards), 1)
        with open(os.path.join(self.root, "eln", "literature", cards[0])) as f:
            content = f.read()
        self.assertIn("doi: 10.1038/nature12345", content)
        self.assertIn("paper_type: preprint", content)
        self.assertIn("created_by: test", content)

    def test_2_doi_dedup(self):
        """Inserting the same DOI a second time should hit dup, no new card created."""
        _run(self.root, "lit_from_doi.py", "10.1038/nature54321", "--stub", "--by", "test")
        # LIT-0001 should now be in the index
        r = _run(self.root, "lit_from_doi.py", "10.1038/nature54321", "--stub", "--no-index")
        self.assertIn("[dup]", r.stdout)
        self.assertIn("LIT-0001", r.stdout)
        cards = [f for f in os.listdir(os.path.join(self.root, "eln", "literature")) if f.startswith("LIT-")]
        self.assertEqual(len(cards), 1, f"should have only one card, actual: {cards}")

    def test_3_doi_normalization(self):
        """https://doi.org/... prefix / mixed case should all normalize to bare DOI."""
        r = _run(self.root, "lit_from_doi.py", "https://doi.org/10.1038/S41586-026-XYZ",
                 "--stub", "--no-index", "--by", "t")
        card_files = [f for f in os.listdir(os.path.join(self.root, "eln", "literature")) if f.startswith("LIT-")]
        with open(os.path.join(self.root, "eln", "literature", card_files[0])) as f:
            content = f.read()
        self.assertIn("doi: 10.1038/s41586-026-xyz", content)


class PdfIngestTests(unittest.TestCase):
    def setUp(self):
        self.ws, self.root = _sandbox()
        self.fx = tempfile.mkdtemp(prefix="eln-p3-pdf-")
    def tearDown(self):
        shutil.rmtree(self.ws, ignore_errors=True)
        shutil.rmtree(self.fx, ignore_errors=True)

    def test_4_pdf_with_doi(self):
        """text-file contains a DOI -> auto delegate to lit_from_doi."""
        txt = os.path.join(self.fx, "paper.txt")
        with open(txt, "w") as f:
            f.write("Title of the paper\nSome preamble\nDOI: 10.1101/2026.05.01.591234\nAbstract...")
        r = _run(self.root, "lit_from_pdf.py", "dummy.pdf",
                 "--text-file", txt, "--stub", "--no-index", "--by", "t")
        self.assertIn("10.1101/2026.05.01.591234", r.stdout)
        cards = [f for f in os.listdir(os.path.join(self.root, "eln", "literature")) if f.startswith("LIT-")]
        self.assertEqual(len(cards), 1)

    def test_5_pdf_no_doi(self):
        """text-file with no DOI -> non-zero exit, no card created."""
        txt = os.path.join(self.fx, "nodoi.txt")
        with open(txt, "w") as f:
            f.write("This is a paper about biology but no DOI here.")
        r = _run(self.root, "lit_from_pdf.py", "dummy.pdf",
                 "--text-file", txt, "--no-index", expect_zero=False)
        self.assertNotEqual(r.returncode, 0)
        cards = [f for f in os.listdir(os.path.join(self.root, "eln", "literature")) if f.startswith("LIT-")]
        self.assertEqual(cards, [])


class DuckdbDoiTests(unittest.TestCase):
    def setUp(self):
        self.ws, self.root = _sandbox()
    def tearDown(self):
        shutil.rmtree(self.ws, ignore_errors=True)

    def test_6_duckdb_doi_index(self):
        """After creating a card and running index -> DuckDB.records should have a non-empty doi column, SELECT-able."""
        _run(self.root, "lit_from_doi.py", "10.1038/nature99999", "--stub", "--by", "t")
        try:
            import duckdb
        except ImportError:
            self.skipTest("duckdb not installed")
        con = duckdb.connect(os.path.join(self.root, "index", "data.duckdb"), read_only=True)
        rows = con.execute("SELECT id, doi, paper_type FROM records WHERE type='literature'").fetchall()
        con.close()
        self.assertEqual(len(rows), 1)
        rid, doi, ptype = rows[0]
        self.assertEqual(doi, "10.1038/nature99999")
        self.assertEqual(ptype, "preprint")


class WikiSyncTests(unittest.TestCase):
    def setUp(self):
        self.ws, self.root = _sandbox(with_workspace=True)
    def tearDown(self):
        shutil.rmtree(self.ws, ignore_errors=True)

    def test_7_wiki_sync_forward(self):
        """LIT card wiki_link points to a summary; after --fix the summary's sources contains the LIT path."""
        # create a LIT card
        _run(self.root, "lit_from_doi.py", "10.1234/wikisync-test", "--stub", "--by", "t")
        # find card
        cards = [f for f in os.listdir(os.path.join(self.root, "eln", "literature")) if f.startswith("LIT-")]
        card_path = os.path.join(self.root, "eln", "literature", cards[0])
        # create wiki summary
        summary_dir = os.path.join(self.ws, "wiki", "summaries")
        summary_path = os.path.join(summary_dir, "wikisync-test.md")
        with open(summary_path, "w") as f:
            f.write("---\ntitle: Test\ntype: summary\nsources:\n  - some/other.md\n---\n\nBody.\n")
        # fill in the LIT's wiki_link
        with open(card_path) as f: c = f.read()
        c = re.sub(r"^wiki_link:.*$", "wiki_link: wiki/summaries/wikisync-test.md", c, count=1, flags=re.M)
        with open(card_path, "w") as f: f.write(c)
        # run --fix
        r = _run(self.root, "wiki_sync.py", "--fix")
        self.assertIn("fix", r.stdout.lower())
        with open(summary_path) as f: s = f.read()
        # the LIT card's repo-relative path should appear
        self.assertIn("eln/literature/", s)


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.ws, self.root = _sandbox()
    def tearDown(self):
        shutil.rmtree(self.ws, ignore_errors=True)

    def test_8_health_9_dimensions(self):
        """Seed a DOI-missing LIT card -> health should catch it on dimension 6."""
        # manually write a LIT card (not via lit_from_doi, intentionally leaving DOI empty)
        os.makedirs(os.path.join(self.root, "eln", "literature"), exist_ok=True)
        card = """---
id: LIT-0001
type: literature
title: Broken card for health test
authors: []
year:
journal:
doi:
pmid:
paper_type:
tags: []
status: to-read
created: 2026-07-11
created_by: t
wiki_link:
related_experiments: []
related_ideas: []
related_literature: []
---

# Broken

Just a stub. [TBD]
"""
        with open(os.path.join(self.root, "eln", "literature", "LIT-0001-broken.md"), "w") as f:
            f.write(card)
        # run index once so health takes the duckdb path
        subprocess.run([sys.executable, os.path.join(self.root, "tools", "index.py")],
                       cwd=self.root, capture_output=True)
        r = subprocess.run([sys.executable, os.path.join(self.root, "tools", "health.py")],
                           cwd=self.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        # key checks: dim 6 DOI missing, dim 2 [TBD]
        self.assertIn("DOI missing", r.stdout)
        self.assertIn("[TBD]", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
