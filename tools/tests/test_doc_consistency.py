"""Doc consistency — assert that human-authored docs match the live registry.

The registry (tools/registry.py) is the single source of truth for record types
and prefixes. This test catches drift between the registry and docs that agents
or humans rely on to know what types exist:

  * ai-eln-keeper Skill lists every current prefix and does not mention retired ones
  * AGENT.md / README.md / conventions.md do not mention retired prefixes as
    active operational instructions

Retired prefixes are intentionally allowed inside docs/history/ (frozen specs).
"""
import os, sys, re, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import registry as R

ELN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(ELN_ROOT))
SKILL_PATH = os.path.join(WORKSPACE_ROOT, "Skills", "ai-eln-keeper", "SKILL.md")

# Prefixes retired during Phase 4. Any operational doc still using them is drift.
RETIRED_PREFIXES = {"MOU", "PROT"}

# Docs whose current-instruction text must match the live registry.
LIVE_DOCS = [
    os.path.join(ELN_ROOT, "AGENT.md"),
    os.path.join(ELN_ROOT, "AGENTS.md"),
    os.path.join(ELN_ROOT, "README.md"),
    os.path.join(ELN_ROOT, "conventions.md"),
    os.path.join(ELN_ROOT, "ROADMAP.md"),
    os.path.join(ELN_ROOT, "eln", "AGENTS.md"),
    os.path.join(ELN_ROOT, "lims", "AGENTS.md"),
    os.path.join(ELN_ROOT, "methods", "AGENTS.md"),
    os.path.join(ELN_ROOT, "wiki", "AGENTS.md"),
]

for base in (os.path.join(ELN_ROOT, "docs"),):
    if os.path.isdir(base):
        LIVE_DOCS.extend(
            os.path.join(dp, fn)
            for dp, _, files in os.walk(base)
            for fn in files
            if fn.endswith(".md") and "history" not in dp.split(os.sep)
        )


def _live_prefixes():
    return {t["prefix"] for t in R.TYPES.values()}


class TestSkillMatchesRegistry(unittest.TestCase):
    """The ai-eln-keeper Skill's type table is checked against registry.py."""

    def setUp(self):
        if not os.path.exists(SKILL_PATH):
            self.skipTest(f"Skill not installed at {SKILL_PATH}")
        with open(SKILL_PATH) as f:
            self.text = f.read()

    def test_skill_lists_every_live_prefix(self):
        missing = [p for p in _live_prefixes() if not re.search(rf"\b{p}\b", self.text)]
        self.assertFalse(
            missing,
            f"ai-eln-keeper SKILL.md is missing live prefixes: {sorted(missing)}. "
            "Regenerate its type table from `python3 tools/registry.py table`.",
        )

    def test_skill_declares_correct_type_count(self):
        m = re.search(r"##\s*(\d+)\s+record types", self.text)
        self.assertIsNotNone(m, "SKILL.md is missing a `## N record types` heading")
        declared = int(m.group(1))
        self.assertEqual(
            declared, len(R.TYPES),
            f"SKILL.md declares {declared} record types but registry has {len(R.TYPES)}.",
        )

    def test_skill_has_no_retired_prefixes(self):
        for retired in RETIRED_PREFIXES:
            self.assertNotRegex(
                self.text, rf"\b{retired}\b",
                f"SKILL.md still references retired prefix {retired!r}.",
            )


class TestLiveDocsHaveNoRetiredPrefixes(unittest.TestCase):
    """Root docs (excluding docs/history/) must not use retired prefixes."""

    def test_no_retired_prefixes_in_live_docs(self):
        offenders = []
        for path in LIVE_DOCS:
            if not os.path.exists(path):
                continue
            with open(path) as f:
                text = f.read()
            for retired in RETIRED_PREFIXES:
                for match in re.finditer(rf"\b{retired}\b", text):
                    line = text[: match.start()].count("\n") + 1
                    offenders.append(f"{os.path.relpath(path, ELN_ROOT)}:{line}: {retired}")
        self.assertFalse(
            offenders,
            "Retired prefixes appear in live docs (move mention to docs/history/ "
            "if it's a historical spec):\n  " + "\n  ".join(offenders),
        )


class TestSchemaVersionExists(unittest.TestCase):
    def test_schema_version_present(self):
        self.assertTrue(hasattr(R, "SCHEMA_VERSION"))
        self.assertRegex(R.SCHEMA_VERSION, r"^\d+\.\d+")


class TestLiveDocsHaveNoBrokenLocalClaims(unittest.TestCase):
    def test_no_inaccessible_baseline_or_missing_porting_doc(self):
        roadmap = open(os.path.join(ELN_ROOT, "ROADMAP.md"), encoding="utf-8").read()
        self.assertNotIn("b56d0b5", roadmap)
        self.assertNotIn("`PORTING.md`", roadmap)


if __name__ == "__main__":
    unittest.main()
