# Contributing to agent-eln

Thanks for looking at agent-eln. This project is unusual: most PRs come from **AI agents**
operating a running lab notebook. That shapes how we work.

## Read this first

Before writing code, read the operating manuals:

- `AGENT.md` — how any agent should operate the system
- `AGENTS.md` — top-level routing map (eln / lims / wiki)
- `conventions.md` — ID / naming rules
- `hierarchy.md` — record-type hierarchy

## Local dev

```bash
git clone <your-fork-url> agent-eln
cd agent-eln
pip install -r requirements.txt
bash tools/install-hooks.sh          # optional git hooks
python -m unittest discover -s tools/tests -v
```

The test suite lives under `tools/tests/`. New tool code should come with a test.

## PR shape

- One concern per PR. `tools/` and `wiki/scripts/` are the code — the rest is data.
- Do **not** commit personal records (real experiments, real DOIs from your lab, real people)
  into the repo. Use fixtures under `tools/tests/`.
- Do **not** commit anything to `raw/`, `wiki/raw/`, or `wiki/files/` — those are
  gitignored on purpose.

## Reporting bugs

Open an issue with:
1. What you tried (`python tools/... --args`)
2. What happened
3. What you expected

If the bug is in agent behavior, include the agent's transcript.

## License

By contributing you agree your work will be released under the MIT License (see `LICENSE`).
