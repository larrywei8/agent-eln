# lab-os

An **AI-native lab operating system**: an Electronic Lab Notebook (ELN), a knowledge wiki, and
a stub Laboratory Information Management System (LIMS), stored as plain Markdown + a small
Python toolkit.

Any AI agent that clones this repo can operate it. There is no database engine, no server —
just files, `git`, and a handful of scripts.

```
lab-os/
├── eln/     electronic lab notebook — experiments, protocols, resources, literature
├── wiki/    knowledge base — concepts, entities, paper summaries
└── lims/    laboratory information management (stub — planned)
```

## Quick start

```bash
git clone <your-fork-url> lab-os
cd lab-os
cp config.example.toml config.toml   # optional; env vars work too
pip install -r eln/requirements.txt

# operate the ELN
cd eln
bash tools/install-hooks.sh
python tools/new.py plasmid --name "pAAV-CAG-EGFP"
python tools/index.py
python tools/dashboard.py
```

Read **`eln/AGENT.md`** next. That is the operating manual an AI agent needs to run this
system end-to-end.

## Configuration

All environment-specific values (your name, contact email, wiki URL prefix) are read from
environment variables so the code has no personal identifiers. See
[`config.example.toml`](config.example.toml) for the full list. The tools also run with
zero configuration — sensible defaults let you clone and go.

| Variable | Purpose | Default |
| --- | --- | --- |
| `LABOS_USER` | Default author for `--by` flags | `$USER` |
| `LABOS_CONTACT_EMAIL` | Polite contact for Crossref / external APIs | `labos-agent@example.org` |
| `LABOS_WIKI_URL_PREFIX` | URL prefix for links into your wiki | *(empty — plain paths)* |
| `LABOS_REPO_ROOT` | Override auto-detected repo root | *(auto)* |

## What's included

| Subsystem | Docs | Highlights |
| --- | --- | --- |
| ELN | `eln/AGENT.md`, `eln/README.md`, `eln/ROADMAP.md` | 26 record types, DOI-deduped literature, provenance graph, HTML dashboard |
| Wiki | `wiki/ANYGEN.md` | Vicky-style summaries, concepts, entities, bidirectional links to literature |
| LIMS | `lims/README.md` | Stub — planned (inventory + chain of custody) |

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). The ELN test suite lives at
`eln/tools/tests/`; run it with `cd eln && python -m unittest discover -s tools/tests -v`.

## License

MIT — see [`LICENSE`](LICENSE).
