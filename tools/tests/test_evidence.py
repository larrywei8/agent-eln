import os
import tempfile
import unittest
from unittest.mock import patch

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import evidence
import records


class TestEvidenceView(unittest.TestCase):
    def test_known_and_freeform_relations(self):
        with tempfile.TemporaryDirectory() as root:
            base = os.path.join(root, "eln", "literature")
            records.atomic_write(os.path.join(base, "a.md"),
                "---\nid: LIT-0001\ntype: literature\ntitle: A\nrelated_projects: [PRJ-0001]\nrelation: supports\n---\n")
            records.atomic_write(os.path.join(base, "b.md"),
                "---\nid: LIT-0002\ntype: literature\ntitle: B\nrelated_projects: [PRJ-0001]\nrelation: useful-comparison\n---\n")
            payload = evidence.build("PRJ-0001", root)
            self.assertEqual(payload["count"], 2)
            self.assertEqual(payload["groups"]["supports"][0]["id"], "LIT-0001")
            self.assertEqual(payload["groups"]["unclassified"][0]["id"], "LIT-0002")


if __name__ == "__main__":
    unittest.main()
