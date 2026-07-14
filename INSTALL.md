# Install Agent ELN with an AI agent

This is the authoritative installation contract for coding agents. Complete every step
before reporting success.

## Required outcome

Create a new, clean `agent-eln` repository that is ready for real research but contains
no demonstration or user data.

## Safety rules

- If the destination `agent-eln` folder already exists, stop and ask the user to choose
  another location. Do not overwrite, merge, rename, move, or delete it.
- Do not modify other projects or research files.
- Do not create example records to demonstrate the installation.
- Do not commit or push anything during installation.
- Keep dependencies inside the repository's `.venv`; do not install them globally.

## Procedure

If the repository has not yet been cloned, run this from the user's chosen workspace:

```bash
git clone https://github.com/larrywei8/agent-eln.git agent-eln
cd agent-eln
```

Read `README.md` and then read `AGENT.md` completely before operating Agent ELN.

Confirm that Python 3.11 or newer and Git are available. Create an isolated environment,
activate it using the equivalent command for the current platform, and install the
runtime and test dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
```

On systems where `python3` is unavailable but `python` is Python 3.11 or newer, use
`python`. On Windows, activate `.venv` using that shell's standard activation command.

Initialize the local validation workflow and build the disposable views:

```bash
bash tools/install-hooks.sh
python tools/index.py
python tools/dashboard.py
```

Verify the clean installation:

```bash
python tools/validate.py
python tools/health.py
python tools/index.py --check
pytest tools/tests/ -q
git status --short
```

## Acceptance criteria

Installation succeeds only when:

- validation reports zero errors and zero research records;
- health checks complete without errors;
- the generated-index check passes;
- the complete test suite passes;
- `index/dashboard.html` exists; and
- `git status --short` is empty.

Warnings that describe an intentionally empty starter repository are expected. Any
other failure must be reported with the failed command and its error; do not describe a
partial installation as successful.

## Final report

Tell the user:

- the absolute installation path;
- the detected Python version;
- whether the Git hook, indexes, and dashboard were created;
- the validation result and test count; and
- any unresolved warning or failure.

Then stop. Leave the repository empty and wait for the user to begin their first real
project.

