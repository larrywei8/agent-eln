import json
import os
import subprocess
import sys
import unittest


TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestJsonContracts(unittest.TestCase):
    def _run_json(self, script):
        proc = subprocess.run(
            [sys.executable, os.path.join(TOOLS, script), "--json"],
            capture_output=True, text=True,
        )
        self.assertIn(proc.returncode, (0, 1), proc.stderr)
        return json.loads(proc.stdout)

    def test_validate_json_schema(self):
        payload = self._run_json("validate.py")
        self.assertIn("ok", payload)
        self.assertIn("counts", payload)
        self.assertIn("findings", payload)
        for finding in payload["findings"]:
            for key in ("severity", "code", "id", "path", "field", "message", "suggestion"):
                self.assertIn(key, finding)

    def test_health_json_schema(self):
        payload = self._run_json("health.py")
        self.assertIn("ok", payload)
        self.assertIn("counts", payload)
        self.assertIn("sections", payload)
        self.assertIn("findings", payload)


if __name__ == "__main__":
    unittest.main()
