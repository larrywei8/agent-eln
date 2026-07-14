"""Phase 2 — completeness / lab-readiness checks in health.py.

Verifies that:
  * check_10_lab_readiness flags reagent/chemical/kit records missing
    location/lot/expiry, cell-lines missing passage/mycoplasma, and
    instruments missing sop.
  * check_11_lit_linkage flags LIT cards with no incoming or outgoing
    EXP/IDEA/PRJ reference, and DOES NOT flag LITs that are linked
    either direction.
  * Empty / "unknown" / "TBD" values are all treated as unfilled.

These are warning-level checks: they must never raise, and must report
findings as (id, msg, path) tuples exactly like the other health checks.
"""
import os
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import health as H


def _write(path, meta_lines, body=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fm = "---\n" + "\n".join(meta_lines) + "\n---\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(fm + body)


class TestLabReadiness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Patch health.ROOT so relpath output stays inside the fake tree.
        self._patch = patch.object(H, "ROOT", self.tmp)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()

    def _run(self, files):
        return H.check_10_lab_readiness(files)

    def test_reagent_missing_all_three_fields(self):
        p = os.path.join(self.tmp, "RGT-9001.md")
        _write(p, [
            "id: RGT-9001",
            "type: reagent",
            "name: TestReagent",
            'location: ""',
            'lot: ""',
            'expiry: ""',
        ])
        issues = self._run([p])
        ids = [i[1] for i in issues]
        self.assertEqual(len(issues), 3)
        self.assertTrue(any("location" in m for m in ids))
        self.assertTrue(any("lot" in m for m in ids))
        self.assertTrue(any("expiry" in m for m in ids))

    def test_reagent_fully_filled_no_issue(self):
        p = os.path.join(self.tmp, "RGT-9002.md")
        _write(p, [
            "id: RGT-9002",
            "type: reagent",
            "name: FullReagent",
            'location: "-80C freezer A shelf 1"',
            'lot: "ABC123"',
            'expiry: "2027-01-01"',
        ])
        self.assertEqual(self._run([p]), [])

    def test_reagent_structured_location_satisfies_check(self):
        """Structured storage_unit + container should count as a valid location
        even when the freeform 'location' field is empty."""
        p = os.path.join(self.tmp, "RGT-9003.md")
        _write(p, [
            "id: RGT-9003",
            "type: reagent",
            "name: StructuredReagent",
            'location: ""',
            'storage_unit: "-80C freezer 2"',
            'container: "box-3"',
            'position: "B7"',
            'lot: "XYZ"',
            'expiry: "2028-01-01"',
        ])
        issues = self._run([p])
        # No 'location' warning — structured pair satisfies it.
        self.assertFalse(any("location" in i[1] for i in issues))

    def test_reagent_structured_missing_container_still_warns(self):
        """storage_unit alone (without container) does not satisfy location."""
        p = os.path.join(self.tmp, "RGT-9004.md")
        _write(p, [
            "id: RGT-9004",
            "type: reagent",
            "name: PartialStructured",
            'location: ""',
            'storage_unit: "-80C freezer 2"',
            'container: ""',
            'lot: "L"',
            'expiry: "2028"',
        ])
        issues = self._run([p])
        self.assertTrue(any("location" in i[1] for i in issues))

    def test_unknown_and_tbd_treated_as_empty(self):
        p = os.path.join(self.tmp, "CL-9001.md")
        _write(p, [
            "id: CL-9001",
            "type: cell-line",
            "name: TestLine",
            "passage: unknown",
            "mycoplasma: TBD",
        ])
        issues = self._run([p])
        self.assertEqual(len(issues), 2)
        for _, msg, _ in issues:
            self.assertIn("biological QC field", msg)

    def test_instrument_without_sop(self):
        p = os.path.join(self.tmp, "INS-9001.md")
        _write(p, [
            "id: INS-9001",
            "type: instrument",
            "name: TestInstrument",
            'sop: ""',
        ])
        issues = self._run([p])
        self.assertEqual(len(issues), 1)
        self.assertIn("SOP", issues[0][1])

    def test_non_covered_type_is_skipped(self):
        p = os.path.join(self.tmp, "PLA-9001.md")
        _write(p, [
            "id: PLA-9001",
            "type: plasmid",
            "name: TestPlasmid",
        ])
        # Plasmids aren't in the covered set — should produce zero warnings.
        self.assertEqual(self._run([p]), [])

    def test_template_ids_are_skipped(self):
        p = os.path.join(self.tmp, "RGT-XXXX.md")
        _write(p, [
            "id: RGT-XXXX",
            "type: reagent",
            "name: TemplateReagent",
            'location: ""',
        ])
        self.assertEqual(self._run([p]), [])


class TestLitLinkage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._patch = patch.object(H, "ROOT", self.tmp)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()

    def test_lit_with_outgoing_link_is_not_unlinked(self):
        lit = os.path.join(self.tmp, "LIT-9001.md")
        _write(lit, [
            "id: LIT-9001",
            "type: literature",
            "title: T",
            "related_experiments:",
            "  - EXP-2026-07-13-01",
        ])
        issues = H.check_11_lit_linkage([lit], [lit])
        self.assertEqual(issues, [])

    def test_lit_referenced_by_another_record_is_not_unlinked(self):
        lit = os.path.join(self.tmp, "LIT-9002.md")
        exp = os.path.join(self.tmp, "EXP-2026-07-13-01.md")
        _write(lit, ["id: LIT-9002", "type: literature", "title: T"])
        _write(exp, [
            "id: EXP-2026-07-13-01",
            "type: experiment",
            "related:",
            "  - LIT-9002",
        ])
        issues = H.check_11_lit_linkage([lit], [lit, exp])
        self.assertEqual(issues, [])

    def test_isolated_lit_is_flagged(self):
        lit = os.path.join(self.tmp, "LIT-9003.md")
        _write(lit, ["id: LIT-9003", "type: literature", "title: T"])
        issues = H.check_11_lit_linkage([lit], [lit])
        self.assertEqual(len(issues), 1)
        self.assertIn("unlinked", issues[0][1])

    def test_read_lit_without_relevance_is_flagged(self):
        lit = os.path.join(self.tmp, "LIT-9004.md")
        _write(lit, ["id: LIT-9004", "type: literature", "title: T", "status: read"])
        issues = H.check_12_lit_relevance([lit])
        self.assertEqual(len(issues), 1)
        self.assertIn("why_it_matters", issues[0][1])


if __name__ == "__main__":
    unittest.main()
