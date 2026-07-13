# agent-eln — agent routing map

You are working in the agent-eln monorepo. This file tells you where to go next.

| Subsystem | Path | What it holds | Operating manual |
| --- | --- | --- | --- |
| **ELN** — activities | `eln/` | experiments, meetings, ideas, projects, protocols, pipelines, scripts, skills, literature, reports | **Read `AGENT.md` first** |
| **LIMS** — inventory | `lims/` | plasmids, oligos, dna, samples, mice, cell-lines, reagents, antibodies, chemicals, recipes, kits, strains, viruses, instruments, datasets, persons | `lims/AGENTS.md` |
| **Wiki** — knowledge | `wiki/` | concepts, entities, paper summaries | `wiki/ANYGEN.md` |
| **tools/**, **templates/**, **index/** | root | shared toolkit, record templates, generated indexes | `AGENT.md` |

## Cross-system rules

- **ELN activities reference LIMS resources** via `used_resources` / `produced_resources`
  fields in experiment frontmatter. LIMS records get `produced_in` auto-backfilled by
  `python tools/backlinks.py --write`.
- **ELN literature cards point at wiki summaries** via `wiki_link` fields (repo-relative
  paths like `wiki/summaries/xyz.md`). Run `python tools/wiki_sync.py --fix` to close the
  bidirectional links.
- **Wiki summaries can point at ELN literature** via `sources` frontmatter. The same
  `wiki_sync.py` script maintains parity.
- **`tools/registry.py` is the single source of truth** for record types, ID prefixes,
  folder paths, required fields, and the walk-exclude list.

## Config

All environment-specific values are read from `AGENT_ELN_*` env vars, resolved in
`tools/config.py`. Never hardcode a user, email, or URL. The monorepo directory names
(`eln`, `lims`, `wiki`) can be overridden with `AGENT_ELN_ELN_DIR` / `_LIMS_DIR` / `_WIKI_DIR`.

## Tests

```bash
python -m unittest discover -s tools/tests -v
```
