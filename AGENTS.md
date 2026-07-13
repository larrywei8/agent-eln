# agent-eln — agent routing map

You are working in the agent-eln monorepo. This file tells you where to go next.

| Subsystem | Path | Operating manual |
| --- | --- | --- |
| **ELN** — experiments, protocols, resources, literature | `eln/` | **Read `eln/AGENT.md` first** |
| **Wiki** — concepts, entities, paper summaries | `wiki/` | `wiki/ANYGEN.md` |
| **LIMS** — inventory, samples (stub) | `lims/` | `lims/README.md` |

## Cross-system rules

- **ELN records point at wiki summaries** via `wiki_link` fields (relative paths like
  `wiki/summaries/xyz.md`). Run `python eln/tools/wiki_sync.py --fix` to close the
  bidirectional links.
- **Wiki summaries can point at ELN literature** via `sources` frontmatter. The same
  `wiki_sync.py` script maintains parity.
- **LIMS is planned; not yet built.** Resource state (location, quantity) currently lives
  in ELN `resources/`; migration happens gradually as LIMS grows.

## Config

All environment-specific values are read from `AGENT_ELN_*` env vars, resolved in
`eln/tools/config.py`. Never hardcode a user, email, or URL.

## Tests

```bash
cd eln
python -m unittest discover -s tools/tests -v
```
