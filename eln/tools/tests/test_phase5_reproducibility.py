"""Phase 5 — reproducibility gates in validate.py.

Completed experiments (status: complete | finalized) must record what actually
ran. Wetlab needs a protocol_version snapshot; drylab needs code_commit +
env_lockfile. These are warnings, not errors — they surface incomplete records
without blocking commits or index rebuilds.

We drive validate.py by running it against a temp ELN tree and reading stderr.
"""
import os, sys, subprocess, tempfile, textwrap, unittest

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALIDATE = os.path.join(TOOLS, "validate.py")


def _write(path, meta_lines, body=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fm = "---\n" + "\n".join(meta_lines) + "\n---\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(fm + body)


class TestPhase5Reproducibility(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "experiments"), exist_ok=True)

    def _run(self):
        # Point validate.py at our fake ROOT by patching R.ROOT via env.
        # validate.py resolves ROOT from registry.py; simplest is to run it
        # from a wrapper that overrides os.walk root — but easier: symlink the
        # registry-required minimal layout inside tmp and invoke directly.
        env = os.environ.copy()
        proc = subprocess.run(
            [sys.executable, VALIDATE],
            capture_output=True, text=True, env=env, cwd=TOOLS,
        )
        return proc.stdout + proc.stderr

    def test_wetlab_complete_without_protocol_version_warns(self):
        exp = os.path.join(self.tmp, "experiments", "EXP-2099-01-01-01.md")
        _write(exp, [
            "id: EXP-2099-01-01-01",
            "date: 2099-01-01",
            "type: experiment",
            "mode: wetlab",
            "status: complete",
            "operator: test",
            "protocols: [SOP-0001]",
        ])
        # Import validate module and run against tmp root directly.
        sys.path.insert(0, TOOLS)
        import importlib, registry as R
        orig_root = R.ROOT
        R.ROOT = self.tmp
        # Force fresh state by re-exec: use runpy so module-level scans use new ROOT.
        import runpy, io, contextlib
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                try:
                    runpy.run_path(VALIDATE, run_name="__main__")
                except SystemExit:
                    pass
        finally:
            R.ROOT = orig_root
        out = buf.getvalue()
        self.assertIn("missing protocol_version", out)

    def test_drylab_complete_without_code_commit_warns(self):
        exp = os.path.join(self.tmp, "experiments", "EXP-2099-01-01-02.md")
        _write(exp, [
            "id: EXP-2099-01-01-02",
            "date: 2099-01-01",
            "type: experiment",
            "mode: drylab",
            "status: complete",
            "operator: test",
        ])
        sys.path.insert(0, TOOLS)
        import registry as R
        orig_root = R.ROOT
        R.ROOT = self.tmp
        import runpy, io, contextlib
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                try:
                    runpy.run_path(VALIDATE, run_name="__main__")
                except SystemExit:
                    pass
        finally:
            R.ROOT = orig_root
        out = buf.getvalue()
        self.assertIn("missing code_commit", out)
        self.assertIn("missing env_lockfile", out)

    def test_planned_experiment_not_gated(self):
        exp = os.path.join(self.tmp, "experiments", "EXP-2099-01-01-03.md")
        _write(exp, [
            "id: EXP-2099-01-01-03",
            "date: 2099-01-01",
            "type: experiment",
            "mode: wetlab",
            "status: planned",
            "operator: test",
        ])
        sys.path.insert(0, TOOLS)
        import registry as R
        orig_root = R.ROOT
        R.ROOT = self.tmp
        import runpy, io, contextlib
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                try:
                    runpy.run_path(VALIDATE, run_name="__main__")
                except SystemExit:
                    pass
        finally:
            R.ROOT = orig_root
        out = buf.getvalue()
        self.assertNotIn("missing protocol_version", out)


if __name__ == "__main__":
    unittest.main()
