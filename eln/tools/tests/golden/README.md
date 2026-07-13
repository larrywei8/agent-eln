# Golden fixtures (regenerate locally)

These fixtures are **not shipped** in the upstream repo — they encode a specific
lab's records and are impossible to compare against a fresh install.

To regenerate for your own ELN once you have records:

```bash
python eln/tools/index.py --force
cp eln/index/*.csv eln/index/graph.json eln/tools/tests/golden/
```

`test_incremental.test_1_golden_diff` will auto-skip when this directory is
empty, so a fresh clone still passes the rest of the suite.
