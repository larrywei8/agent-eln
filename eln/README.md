# AI-native Electronic Lab Notebook (ELN)

Pure Markdown + images + scripts. No software to install, no database engine. Any AI agent
that opens the repo should **read `AGENT.md` first** — that's enough to operate the whole library.

## 30-second start
```bash
bash tools/install-hooks.sh                       # one-time: install git hooks (auto index+validate)
python tools/new.py plasmid --name "..." --by me  # allocate an ID and write the file to the right folder
# fill in fields, write the body; only write one-way links (used_resources / produced_resources)
python tools/backlinks.py --write                 # auto-backfill produced_in on the resource side (idempotent)
python tools/index.py                             # one command rebuilds all indexes + graph.json
python tools/validate.py                          # check ID uniqueness, reference validity, required fields
python tools/dashboard.py                         # generate index/dashboard.html (double-click to open)
git add -A && git commit -m "[EXP-...] ..."
```

## Core principles
- **Single source of truth: `tools/registry.py`** — adding a new record type = one entry + one template. That's it.
- **Only write one-way links; backlinks are auto-filled.** The provenance graph and dashboard are fully generated.
- **Project layer `projects/` (PRJ)** groups experiments/data/ideas across days into a research line.

## Structure
- `resources/` resource library · `protocols/` `pipelines/` `scripts/` `skills/`
- `experiments/` daily notes (wet/dry) · `projects/` projects · `literature/` literature · `ideas/` `meetings/`
- `templates/` templates · `tools/` scripts · `index/` auto-generated indexes + `dashboard.html`

See `AGENT.md` (agent operating manual) and `conventions.md` (ID / naming conventions).
