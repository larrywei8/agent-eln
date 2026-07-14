# One-Prompt Agent Installation Design

## Goal

Let a researcher ask any capable coding agent to install Agent ELN using one short,
non-intimidating prompt while keeping the complete, verifiable procedure inside the
repository.

## User-facing prompt

```text
Install Agent ELN from https://github.com/larrywei8/agent-eln into a new `agent-eln`
folder and follow its installation instructions.
```

The prompt deliberately describes the outcome rather than embedding shell commands. It
works across Codex, Claude Code, OpenClaw, Hermes, Zo Computer, and other agents that can
clone a repository, read files, and run commands.

## README placement

Add an “Install with your AI agent” section immediately before “Quick start.” It shows
the single prompt in a block quote, briefly states what the agent will do, and retains
the existing manual Quick Start for people who prefer terminal commands.

## Repository installation contract

Add a root-level `INSTALL.md` as the platform-neutral installation authority. The
installing agent must:

1. refuse to overwrite an existing `agent-eln` destination;
2. clone the repository into a new folder;
3. read `AGENT.md` completely before operating the system;
4. create and use `.venv` where supported;
5. install runtime and development dependencies;
6. install the repository Git validation hook;
7. generate indexes and the local dashboard;
8. run validation, health checks, and the complete test suite;
9. leave a clean empty system without demo or real research records; and
10. report the installation path, completed checks, and any unresolved failure.

## Safety and failure behavior

The installer must stop rather than delete, merge into, or rename an existing
destination. It must not invent records to demonstrate success. A partial setup is not
reported as successful: failures are named with the failed command and the remaining
unverified steps.

## Success criteria

- The visible prompt remains short enough to copy without editing.
- The same prompt can be used with multiple agent products.
- Installation details live in one versioned file rather than the README prompt.
- A successful run ends with an empty, validated, tested Agent ELN repository.
- The existing manual installation path remains available.

