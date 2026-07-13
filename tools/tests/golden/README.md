# Golden fixtures (regenerate locally)

These fixtures are **not shipped** in the upstream repo — they encode a specific
lab's records and are impossible to compare against a fresh install.

To regenerate for your own records once the library has content:

```bash
python tools/index.py --force
cp index/*.csv index/graph.json tools/tests/golden/
```

`test_incremental.test_1_golden_diff` will auto-skip when this directory is
empty, so a fresh clone still passes the rest of the suite.
