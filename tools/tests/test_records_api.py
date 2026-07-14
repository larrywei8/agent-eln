import os
import tempfile
import unittest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import records
import registry


class TestRecordsApi(unittest.TestCase):
    def test_discovery_lookup_edges_and_atomic_write(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "lims", "plasmids", "PLA-0001", "card.md")
            records.atomic_write(path, "---\nid: PLA-0001\ntype: plasmid\n---\nbody\n")
            found, meta = records.find_record("PLA-0001", root)
            self.assertEqual(found, path)
            self.assertEqual(meta["type"], "plasmid")
            edges = records.extract_edges({"id": "EXP-2026-01-01-01", "used_resources": ["PLA-0001"]})
            self.assertEqual(edges, [{"src": "EXP-2026-01-01-01", "dst": "PLA-0001", "rel": "used_resources"}])
            self.assertFalse(any(name.endswith(".tmp") for name in os.listdir(os.path.dirname(path))))

    def test_excluded_directories_are_not_records(self):
        with tempfile.TemporaryDirectory() as root:
            records.atomic_write(os.path.join(root, "tools", "fake.md"), "---\nid: PLA-9999\ntype: plasmid\n---\n")
            self.assertEqual(list(records.iter_record_paths(root)), [])

    def test_registry_root_override_is_absolute(self):
        self.assertTrue(os.path.isabs(registry.ROOT))


if __name__ == "__main__":
    unittest.main()
