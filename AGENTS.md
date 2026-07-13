# agent-eln — agent routing map

You are working in the agent-eln monorepo. This file tells you where to go next.

| Subsystem | Path | What it holds | Operating manual |
| --- | --- | --- | --- |
| **ELN** — activities (*what happened*) | `eln/` | experiments, meetings, ideas, projects, literature, reports | **Read `AGENT.md` first**, then `eln/AGENTS.md` |
| **LIMS** — inventory (*what you have*) | `lims/` | plasmids, oligos, dna, samples, mice, cell-lines, reagents, antibodies, chemicals, recipes, kits, strains, viruses, instruments, datasets, persons | `lims/AGENTS.md` |
| **Methods** — how-to (*how you do it*) | `methods/` | protocols (SOPs), pipelines, scripts, skills | `methods/AGENTS.md` |
| **Wiki** — knowledge (*what others learned*) | `wiki/` | concepts, entities, paper summaries | `wiki/AGENTS.md` |
| **tools/**, **templates/**, **index/** | root | shared toolkit, record templates, generated indexes | `AGENT.md` |

## Cross-system rules

- **ELN activities reference LIMS resources** via `used_resources` / `produced_resources`
  fields in experiment frontmatter. LIMS records get `produced_in` auto-backfilled by
  `python tools/backlinks.py --write`.
- **ELN activities reference Methods** via `protocols` / `pipeline` / `scripts` fields.
  The backlink writer walks these too, so a method's usage history is discoverable.
- **ELN literature cards point at wiki summaries** via `wiki_link` fields (repo-relative
  paths like `wiki/summaries/xyz.md`). Run `python tools/wiki_sync.py --fix` to close the
  bidirectional links.
- **Wiki summaries can point at ELN literature** via `sources` frontmatter. The same
  `wiki_sync.py` script maintains parity.
- **`tools/registry.py` is the single source of truth** for record types, ID prefixes,
  folder paths, required fields, and the walk-exclude list.

## Config

All environment-specific values are read from `AGENT_ELN_*` env vars, resolved in
`tools/config.py`. Never hardcode a user, email, or URL. The four module directory names
(`eln`, `lims`, `methods`, `wiki`) are fixed — `tools/registry.py` uses those literal
names when computing record paths, so renaming them via env var is not currently
supported.

## Tests

```bash
pytest tools/tests/ -v
```
