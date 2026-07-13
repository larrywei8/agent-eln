"""Phase 2 — fm.set_field / get_field contract tests.

Covers all scenarios relied on by backlinks.py / wiki_sync.py after migration:
scalar <-> block <-> inline style interchange, and new field insertion.
"""
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fm


def _wrap(head, body="body\n"):
    return f"---\n{head}---\n{body}"


class TestSetField(unittest.TestCase):
    def test_scalar_replace(self):
        t = _wrap("type: r\nproduced_in: \nid: X\n")
        r = fm.set_field(t, "produced_in", "EXP-1")
        self.assertIn("produced_in: EXP-1\nid: X", r)

    def test_block_list_replaced_with_scalar(self):
        t = _wrap("type: r\nproduced_in:\n  - EXP-A\n  - EXP-B\nid: X\n")
        r = fm.set_field(t, "produced_in", "EXP-C")
        self.assertIn("produced_in: EXP-C\nid: X", r)
        self.assertNotIn("EXP-A", r)
        self.assertNotIn("EXP-B", r)

    def test_block_list_append(self):
        t = _wrap("type: r\nsources:\n  - a\n  - b\nid: X\n")
        r = fm.set_field(t, "sources", ["a", "b", "c"])
        self.assertEqual(r.count("- a\n"), 1)
        self.assertIn("- c\n", r)
        self.assertIn("id: X", r)

    def test_missing_key_inserted_after_type(self):
        t = _wrap("type: literature\nid: LIT-1\n")
        r = fm.set_field(t, "wiki_link", "k/w.md")
        self.assertIn("type: literature\nwiki_link: k/w.md\nid: LIT-1", r)

    def test_inline_list_preserved(self):
        t = _wrap("type: literature\ntags: [a, b]\nid: LIT-1\n")
        r = fm.set_field(t, "tags", ["a", "b", "c"])
        self.assertIn("tags: [a, b, c]", r)

    def test_scalar_upgraded_to_block_list(self):
        t = _wrap("type: r\nauthors: alice\nid: 1\n")
        r = fm.set_field(t, "authors", ["a", "b"])
        self.assertIn("authors:\n  - a\n  - b", r)

    def test_block_at_end_of_frontmatter(self):
        t = _wrap("type: r\nsources:\n  - a\n  - b\n")
        r = fm.set_field(t, "sources", ["a", "b", "c"])
        self.assertIn("- c", r)
        self.assertTrue(r.rstrip().endswith("---\nbody"))

    def test_non_frontmatter_untouched(self):
        t = "no frontmatter here"
        r = fm.set_field(t, "x", "y")
        self.assertEqual(r, t)

    def test_get_field_block(self):
        t = _wrap("type: r\nsources:\n  - a\n  - b\n")
        self.assertEqual(fm.get_field(t, "sources"), ["a", "b"])

    def test_get_field_quoted_scalar_with_colon(self):
        t = _wrap('type: r\ntitle: "a: b"\n')
        self.assertEqual(fm.get_field(t, "title"), "a: b")

    def test_get_field_missing_returns_none(self):
        t = _wrap("type: r\nid: X\n")
        self.assertIsNone(fm.get_field(t, "does_not_exist"))

    def test_backlinks_scenario_block_produced_in(self):
        """Regression: when block-list produced_in receives a new scalar value, the old
        regex would overwrite the first line only and leave orphan `- EXP-B`.
        fm.set_field should cleanly replace the whole block."""
        t = _wrap("type: r\nproduced_in:\n  - EXP-A\n  - EXP-B\nid: X\n")
        r = fm.set_field(t, "produced_in", "EXP-Z")
        # key regression point: no orphan list items remain
        for line in r.splitlines():
            self.assertNotIn("- EXP-A", line)
            self.assertNotIn("- EXP-B", line)


class TestParseRoundTrip(unittest.TestCase):
    def test_parse_after_set_field(self):
        import tempfile, pathlib
        t = _wrap("type: r\nsources:\n  - a\n  - b\nid: X\n")
        r = fm.set_field(t, "sources", ["a", "b", "c"])
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(r)
            path = f.name
        try:
            meta, body = fm.parse(path)
            self.assertEqual(meta["sources"], ["a", "b", "c"])
            self.assertEqual(meta["type"], "r")
            self.assertEqual(meta["id"], "X")
            self.assertEqual(body.strip(), "body")
        finally:
            pathlib.Path(path).unlink()


if __name__ == "__main__":
    unittest.main()
