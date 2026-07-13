# Contributing to agent-eln

Thanks for looking at agent-eln. This project is unusual: most PRs come from **AI agents**
operating a running lab notebook. That shapes how we work.

## Read this first

Before writing code, read the operating manuals:

- `eln/AGENT.md` — how any agent should operate the ELN
- `eln/conventions.md` — ID / naming rules
- `eln/hierarchy.md` — record-type hierarchy

## Local dev

```bash
git clone <your-fork-url> agent-eln
cd agent-eln
pip install -r eln/requirements.txt
cd eln
bash tools/install-hooks.sh          # optional git hooks
python -m unittest discover -s tools/tests -v
```

The ELN test suite lives under `eln/tools/tests/`. New tool code should come with a test.

## PR shape

- One concern per PR. `eln/tools/` and `wiki/scripts/` are the code — the rest is data.
- Do **not** commit personal records (real experiments, real DOIs from your lab, real people)
  into the repo. Use fixtures under `eln/tools/tests/`.
- Do **not** commit anything to `eln/raw/`, `wiki/raw/`, or `wiki/files/` — those are
  gitignored on purpose.

## Reporting bugs

Open an issue with:
1. What you tried (`python tools/... --args`)
2. What happened
3. What you expected

If the bug is in agent behavior, include the agent's transcript.

## License

By contributing you agree your work will be released under the MIT License (see `LICENSE`).
