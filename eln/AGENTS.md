# AGENTS.md — read this first when entering this repo

This repo is an **AI-native Electronic Lab Notebook (ELN)**: pure Markdown + images +
standard-library Python scripts, no database, no server. Any agent can operate it
fully with "read/write files + grep + run scripts under `tools/`".

## Authoritative operating manual
> **Read [`AGENT.md`](./AGENT.md) for full rules.** This file is only a common entry-point
> pointer for the various agents, plus a 30-second must-know. The single source of truth
> for types/fields/IDs is [`tools/registry.py`](./tools/registry.py).

## 30-second must-know (details in AGENT.md)
- **One record = one markdown file with a unique ID** (resource types are folders with
  `card.md` + attachments). Frontmatter = queryable structured fields; body = free text.
- **IDs never change and are never reused.** Relations are expressed by ID references
  (`used_resources / produced_resources / produced_datasets / derived_from / produced_in ...`),
  forming the provenance graph.
- **Only write one-way links** (in experiments, write used/produced). The reverse link
  `produced_in` is auto-backfilled by `python tools/backlinks.py --write`.
- **Adding a new record type = add one entry to `tools/registry.py` + write one `templates/`
  template.** Only these two places.

## Standard actions
```bash
python tools/new.py <type> --name "..." --by <you>   # create a record (auto-allocate ID + write to disk)
python tools/backlinks.py --write                     # auto-backfill backlinks
python tools/index.py                                 # rebuild all indexes + graph.json
python tools/validate.py                              # validate (must pass before commit)
python tools/dashboard.py                             # refresh index/dashboard.html
```

## Hard rules
- After changing any file, run `index.py` + `validate.py`; validate must pass before commit
  (auto-run if `tools/install-hooks.sh` was executed).
- Every referenced ID must actually exist, and required fields must be complete (validate checks this).
- Raw large data (fastq / raw imaging etc.) does not go into git — only the path + sha256 + size.
- Convert PPT/PDF to markdown before adding to the library.

First time on a new machine: `bash tools/install-hooks.sh` to install the hooks; optional
dependencies are in `requirements.txt`. Full steps for migrating to another machine/agent
are in `PORTING.md`.
