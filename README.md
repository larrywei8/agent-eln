# agent-eln

An **AI-native lab operating system**: an Electronic Lab Notebook (ELN), a Laboratory
Information Management System (LIMS), a methods library, and a knowledge wiki — all
stored as plain Markdown + a small Python toolkit.

Any AI agent that clones this repo can operate it. There is no database engine, no server —
just files, `git`, and a handful of scripts.

```
agent-eln/
├── eln/       activities — experiments, meetings, ideas, projects, literature, reports
├── lims/      inventory  — plasmids, oligos, samples, mice, cell lines, reagents, instruments, ...
├── methods/   how-to     — protocols (SOPs), pipelines, scripts, skills
├── wiki/      knowledge  — concepts, entities, paper summaries
├── tools/     shared toolkit (one CLI, one registry, one provenance graph)
└── templates/ record templates
```

**Mental model.** Four modules, four distinct nouns:

- **ELN** logs *what happened* — the experiment you ran, the meeting you had, the paper you read.
- **LIMS** lists *what you have* — the plasmid on the bench, the mouse in the cage, the reagent in the freezer.
- **methods** describes *how you do things* — the SOPs, analysis pipelines, and scripts you author and reuse.
- **wiki** captures *what you learned from others* — summaries of external papers, concepts, and entities.

The provenance graph connects them — every experiment can declare `used_resources` /
`produced_resources` / `protocols` / `pipeline`, and the referenced LIMS/methods records
get an auto-backfilled `produced_in` link.

## Quick start

```bash
git clone <your-fork-url> agent-eln
cd agent-eln
cp config.example.toml config.toml   # optional; env vars work too
pip install -r requirements.txt

# operate the system
bash tools/install-hooks.sh
python tools/new.py plasmid --name "pAAV-CAG-EGFP"     # -> lims/plasmids/
python tools/new.py experiment --title "cloning test"  # -> eln/experiments/
python tools/index.py
python tools/dashboard.py
```

Read **`AGENT.md`** next. That is the operating manual an AI agent needs to run this
system end-to-end.

## Configuration

All environment-specific values (your name, contact email, wiki URL prefix) are read from
environment variables so the code has no personal identifiers. See
[`config.example.toml`](config.example.toml) for the full list. The tools also run with
zero configuration — sensible defaults let you clone and go.

| Variable | Purpose | Default |
| --- | --- | --- |
| `AGENT_ELN_USER` | Default author for `--by` flags | `$USER` |
| `AGENT_ELN_CONTACT_EMAIL` | Polite contact for Crossref / external APIs | `agent-eln@example.org` |
| `AGENT_ELN_WIKI_URL_PREFIX` | URL prefix for links into your wiki | *(empty — plain paths)* |
| `AGENT_ELN_REPO_ROOT` | Override auto-detected repo root | *(auto)* |
| `AGENT_ELN_ELN_DIR` / `AGENT_ELN_LIMS_DIR` / `AGENT_ELN_METHODS_DIR` / `AGENT_ELN_WIKI_DIR` | Rename the four module dirs | `eln` / `lims` / `methods` / `wiki` |

## What's included

| Subsystem | Docs | Highlights |
| --- | --- | --- |
| ELN | `AGENT.md`, `eln/AGENTS.md` | 6 activity record types, DOI-deduped literature, provenance graph, HTML dashboard |
| LIMS | `lims/AGENTS.md` | 16 inventory record types with expiry / status / location tracking |
| Methods | `methods/AGENTS.md` | 4 how-to record types: protocol (SOP), pipeline, script, skill |
| Wiki | `wiki/AGENTS.md` | Vicky-style summaries, concepts, entities, bidirectional links to literature |

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). The test suite lives at `tools/tests/`;
run it with `python -m unittest discover -s tools/tests -v`.

## License

MIT — see [`LICENSE`](LICENSE).
