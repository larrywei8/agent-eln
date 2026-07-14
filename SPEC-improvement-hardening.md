# agent-eln Improvement and Hardening Specification

## Goal

Implement the 2026-07-14 whole-system review recommendations while preserving agent-eln's intended scope: a portable, single-lab research ELN, lightweight LIMS, methods library, and literature wiki built on Markdown and Git.

The work must improve release quality, scientific provenance, agent operability, portability, and test confidence without adding regulated-LIMS workflows, a second canonical database, or a CRUD web application.

## Constraints

- Markdown records remain canonical; generated CSV, JSON, HTML, and DuckDB remain derived views.
- Preserve all existing user changes, especially the current uncommitted `today.py`, its tests, the pitch document, and the Obsidian portability patch.
- Do not add GxP signatures, approvals, role-based access control, inventory transaction ledgers, barcode workflows, or multi-user locking.
- Core workflows must work in a standalone clone without `/home/workspace`-specific dependencies.
- Mutating commands must retain or gain preview-safe behavior. In this project, `--dry-run`
  means **compute and print the planned paths and field changes without writing anything**;
  it does not mutate a temporary copy unless a command explicitly documents a separate test mode.
  Every mutating command's `--help` must state this contract.
- Existing record IDs and schemas remain backward compatible. The shared record API must
  produce no schema-visible or byte-level frontmatter changes merely by reading and
  rewriting a record; any intentional migration requires a separate documented command
  and regression fixture.
- External input paths and metadata are untrusted. Ingest and conversion tools must avoid
  `eval`, shell interpolation, and `shell=True`; subprocesses receive argument arrays and
  writes stay within explicitly selected destinations.
- Core runtime dependencies use compatible version ranges; CI/dev dependencies are kept
  separate or constrained. Reproducible deployments should use a generated lock/constraints
  file, while the library must not pretend optional platform-specific converters are core.

## Implementation plan

### 1. Release and documentation baseline

- Resolve the empty-day `today.py` output/test disagreement.
- Add a minimal valid starter `wiki/index.md` so a fresh clone passes wiki health preflight.
- Separate reusable-template status from private deployed-lab statistics in `ROADMAP.md`.
- Remove or replace the inaccessible baseline commit and missing `PORTING.md` reference.
- Replace retired prefixes in current documentation.
- Expand documentation-consistency tests across root manuals, module manuals, roadmap, and current docs.
- Document which index artifacts are canonical, committed derived outputs, or local caches.

### 2. Canonical record library

- Add a small shared internal record API for walking, loading, locating, validating IDs, extracting edges, and atomic writes.
- Migrate duplicate implementations one script at a time, each with regression coverage.
  Begin with read-only consumers (`validate.py`, then `index.py`), then migrate mutators
  (`new.py`, `derive.py`, and `backlinks.py`) only after their golden-path tests pass.
- Preserve CLI behavior and support environment-root overrides for isolated tests.
- Refactor validation into callable functions returning structured findings while preserving human-readable CLI output.
- Do not hold the additive provenance, literature, CI, or release fixes behind completion
  of this migration; shared-API slices are interleaved where they reduce risk.

### 3. Structured command contracts

- Add stable JSON output and exit behavior to validation and health commands first.
- Add or normalize `--json` and `--dry-run` behavior for core mutation/query commands where useful.
- Represent findings with severity, code, record ID, path, field, message, and suggested correction when applicable.

### 4. Provenance semantics

- Add target-type validation for typed fields such as `protocols`, `pipeline`, `scripts`, `project`, `produced_datasets`, and produced/used resources.
- Detect self-links and duplicate edges. Add lightweight `derived_from` cycle detection,
  but treat it as a non-blocking graph-quality safeguard rather than a delivery gate.
- Clarify in documentation that generated graph edges expose method usage, whereas materialized `produced_in` backlinks apply only to produced resources and datasets.
- Add a graph-quality report or validation section suitable for single-lab research provenance.

### 5. Experiment reproducibility

- Standardize protocol-version snapshots for completed wet-lab experiments.
- Standardize a compact computational-run block containing code commit, entrypoint/command, environment lockfile, inputs, outputs, and manifest/hash references.
- Keep these as warning-level completeness checks unless a field is structurally invalid.
- Add documentation and fixtures demonstrating both wet-lab and dry-lab completion.

### 6. Literature-to-research integration

- Support multiple **optional-typed** literature relationships. Known relation values receive
  validation and evidence-view grouping when present; free-form or unclassified links remain
  valid and no paper is forced into a taxonomy.
- Add a concise `why_it_matters`/lab-relevance field for papers promoted to `read`, reported as a completeness warning rather than a structural error.
- Generate project evidence views separating supporting, contradictory, method-source, and motivating literature.
- Preserve general unlinked background reading as valid.
- Extend preprint-to-publication reconciliation checks across LIT and wiki records.

### 7. Wiki core and optional extensions

- Define and document a minimal built-in wiki contract: index, pages, sources, health/lint, and LIT sync.
- Label Obsidian, Quarto, semantic-edge experiments, PM discovery reports, and external llm-wiki Skills as optional extensions.
- Ensure fresh-clone health and core tests do not require external Skills or workspace-specific paths.
- Avoid a cosmetic rewrite of `knowledge_pm.py`; split modules only where implementation changes require it.

### 8. Generated artifact and CI policy

- Make cache/DuckDB handling explicit and exclude machine-local artifacts where appropriate.
- Add a non-mutating `index.py --check` path that detects stale committed derived outputs.
- Expand CI to run tests, structural validation, wiki health, and generated-artifact consistency on Python 3.11 and 3.12.
- Replace the permanently skipped golden regression test with committed deterministic fixtures or a meaningful alternative.

### 9. End-to-end workflow coverage

Add isolated golden-path tests for:

1. resource creation → experiment production link → backlink → index → validate → trace;
2. parent sample → derived child → hierarchy validation → graph;
3. DOI ingest/stub → duplicate rejection → wiki synchronization;
4. dataset ingest → manifest → checksum verification → experiment linkage;
5. GenBank annotation idempotence when Biopython is available;
6. experiment rename with stable ID and artifact-folder preservation;
7. empty fresh clone health and full documented smoke commands;
8. dashboard generation with empty and representative mixed records.

## Delivery stages

To keep review and rollback manageable, implementation will be divided into commits or clearly separable change groups:

1. Release blockers and documentation consistency.
2. JSON contracts for `validate.py` and `health.py`.
3. Provenance and reproducibility deltas, including existing Phase 5 scaffolding.
4. Literature/wiki improvements with optional-typed relationships.
5. Generated-artifact policy, CI, and end-to-end temporary-repository tests.
6. Shared record API migrations interleaved per script: `validate.py` → `index.py` →
   `new.py` → `derive.py` → `backlinks.py`. Each slice must preserve behavior and pass
   its own regression tests before the next migration.

No commit or push will be performed unless explicitly requested. Existing uncommitted work will remain distinguishable from new changes.

## Verification

The completed implementation must satisfy:

- `pytest tools/tests/ -q` passes with no unexplained skips.
- `python3 tools/validate.py` passes on the starter repository.
- JSON validation output parses and matches the documented schema.
- `python3 wiki/scripts/knowledge_pm.py --mode health --root wiki` passes on a fresh clone.
- `python3 tools/index.py --check` reports generated artifacts current.
- End-to-end tests run entirely in temporary repositories and do not alter live lab records.
- Current documentation contains no retired operational prefixes, broken local links, inaccessible commit claims, or workspace-specific required paths.
- Existing CLI workflows remain backward compatible.

## Success criteria

An arbitrary AI agent can clone the repository, understand the four-module model, initialize and operate it without Larry-specific workspace dependencies, receive machine-readable failures, create scientifically traceable records, and reproduce documented wet- and dry-lab workflows while the human retains plain Markdown and Git as the transparent source of truth.
