# wiki/ — knowledge module

> Schema + operating conventions for the wiki. Read this at the start of every
> session together with `wiki/index.md`. Update after every major compile,
> ingest batch, or structural change.

## Scope

This module is a Karpathy-style, self-compiling knowledge base — the *external*
side of what your lab knows. It sits alongside the other three agent-eln modules:

- `eln/` — events (what happened)
- `lims/` — inventory (what you have)
- `methods/` — how-to (how you do things)
- `wiki/` — external knowledge (what you learned from others)

What the wiki covers:

- Anything you want to learn, remember, or reference — research papers, articles,
  project notes, tools, books, ideas, people, and technical concepts.
- Cross-links back to the `eln/literature/` reading queue via `sources:`
  frontmatter and to `wiki/summaries/` from LIT cards via `wiki_link:`.

What the wiki deliberately excludes:

- Daily journals or task lists.
- Sensitive personal information.

## Operations

### Core versus optional

The portable core is `wiki/index.md`, Markdown pages with source frontmatter,
the fast health preflight, ordinary links, and `tools/wiki_sync.py`. Obsidian sync,
Quarto export, semantic-edge experiments, PM discovery reports, and external
llm-wiki Skills are optional extensions. A fresh clone must remain healthy without them.

This wiki follows the `llm-wiki-anygen` skill's five operations: `compile`,
`ingest`, `query`, `lint`, `audit`. Every operation appends an entry to
`log/YYYYMMDD.md`.

### PM / agent loop

Run `python3 wiki/scripts/knowledge_pm.py --mode agent --root wiki` to generate
the wiki's operating reports:

- `outputs/discovery/YYYYMMDD.md` — hidden-theme and cross-link report
- `outputs/gaps/YYYYMMDD.md` — open questions, missing provenance, inbox, and lint-drift queue
- `outputs/evolution/YYYYMMDD.md` — knowledge-state metrics over time
- `outputs/typed-edges/edges.tsv` — typed-edge export for KAG/RAG experiments
- `outputs/ingest-plans/YYYYMMDD.md` — source-intake queue from `raw/inbox/`
- `outputs/hidden-patterns/YYYYMMDD.md` — cross-domain pattern hypotheses
- `outputs/literature-seeds/YYYYMMDD.md` — search-ready prompts from explicit gaps
- `outputs/dashboard.md` — latest report pointers

Use `--mode pm` for a health-report-only run. The agent loop is conservative: it
plans and prioritizes, but it never automatically rewrites wiki pages. Execute
the actual `ingest` operation manually from the generated plan, then rerun lint.

### Fast health preflight (run before lint)

`python3 wiki/scripts/knowledge_pm.py --mode health --root wiki` is a quick,
**side-effect-free** structural preflight to run *before* the expensive `lint`
(which recompiles all `.graph` artifacts). It checks:

- **Empty pages** — FAIL
- **Malformed frontmatter** (indented fence, or no closing `---`) — FAIL
- **Index sync** — every page linked from `wiki/index.md` at least once, every link resolves — FAIL
- **Incomplete frontmatter** (missing any of `title, type, created, updated, confidence, confidence_rationale, sources, tags`) — WARN
- **Duplicate page titles within the same type** — WARN
- **Log coverage** — newest log entry age; pages whose `updated` is newer than the last log entry — WARN

Exit code is `1` if any blocking issue is found. Clean output means it is safe
to run the full `lint`.

### Ad-hoc query modes (read-only)

- `--mode search --query "..."` — BM25 keyword search across every page
- `--mode query --edge-kind <kind> [--source <glob>] [--target <glob>]` — filter typed-edges. Edge kinds: `links_to`, `has_tag`, `source_for`, `has_type`
- `--mode ask --query "..."` — BM25 seeds + 1-hop typed-edge neighbors (retrieval-only, no LLM)
- `--mode audit-entities [--thin-words 200]` — merge candidates (only highly-similar duplicates; thin entities are enrich candidates, never merge)
- `--mode preprint-status [--check-online]` — scan for preprint DOIs; Crossref check for published versions
- `--mode quality` — non-blocking quality report: thin (<120 words), uncited, or structure-poor pages
- `--mode supersession-check` — validate supersession metadata (see § Supersession)

All read-only modes touch no wiki pages and skip lint. `query` and `ask` read
`outputs/typed-edges/edges.tsv`, so run `--mode agent` at least once first.

### Report promotion policy

PM outputs are working reports until promoted:

- `outputs/ingest-plans/` → execute via the normal `ingest` operation, then log and lint
- `outputs/hidden-patterns/` → promote only stable, source-backed patterns into `wiki/concepts/`
- `outputs/literature-seeds/` → search prompts; not citations until real sources are ingested
- `outputs/evolution/` → trend monitoring; promote durable methodology changes to `AGENTS.md`, a scenario card, or a Skill
- `outputs/typed-edges/` → machine-readable export only; do not hand-edit

### Output retention

Each weekly-report category keeps only the **8 most recent dated files**.
Older files are moved into `outputs/_archive/YYYY-MM.tar.gz` by the PM script's
housekeeping step.

## Naming conventions

- **Concept pages** (`wiki/concepts/`): Title Case noun phrases.
- **Folder-split concepts** (`wiki/concepts/<topic>/`): used when a topic exceeds ~1200 words. Contains `index.md` + one file per aspect.
- **Entity pages** (`wiki/entities/`): proper names — people, tools, organizations, papers.
- **Summary pages** (`wiki/summaries/`): kebab-case source slug.

All pages require YAML frontmatter: `title`, `type`, `created`, `updated`,
`confidence`, `confidence_rationale`, `sources`, `tags`.

Optional but recommended: `last_reviewed: YYYY-MM-DD`. Refresh it whenever you
re-read a page and confirm it still holds. The PM evolution report uses it to
flag stale-trusted pages (≥90 days, confidence ≥7) and low-confidence pages
overdue for review (≥30 days, confidence ≤5).

### Diagrams and formulas

- All diagrams are **mermaid**. No ASCII art.
- All formulas are **KaTeX** (inline `$...$` or block `$$...$$`).

### Raw file policy

- **All new source material first lands in `raw/inbox/<bucket>/`** (one of `authored/`, `unread-papers/`, `web-saves/`, `books-highlights/`, `talks-workshops/`, `project-notes/`, `lab-protocols/`). This is the only correct intake path.
- After ingest, move the original into the appropriate **format-based archive** under `raw/articles/`, `raw/papers/`, `raw/notes/`, `raw/protocols/`, `raw/source/`, `raw/tools/`, or `raw/pdf/`. The inbox bucket records *what kind of brain input it was*; the archive directory records *what format it is*.
- Large binaries → create a pointer file at `raw/refs/<slug>.md` with `kind: ref` and `external_path` fields. Do not copy the binary.
- Do not drop new files directly into `raw/articles/`, `raw/papers/`, etc. — those are archive layers, not intake. The PM gap report flags any file lingering in `raw/inbox/` for more than 14 days.
- **Inbox status lifecycle.** Inbox files may carry a `status:` field: `inbox` (default) → `processing` → `ingested` (done; archive it out) or `failed` / `blocked`. Failed/blocked items should also record `attempts:` (integer) and `last_error:` (one-line note).

### Confidence Scoring System

Every wiki page must carry two YAML frontmatter fields:

- `confidence`: integer 0–10 — how much to trust this page on first read
- `confidence_rationale`: string — why this score was assigned

**Source-type baselines:**

| Source type | Baseline | Notes |
| --- | --- | --- |
| Nature / Science / Cell | 9–10 | Gold standard, highest-IF primary research |
| Nature Biotech / Nature Methods / Cell sub-journals | 8–9 | Near-gold standard primary research |
| Other peer-reviewed (high IF) | 7–8 | e.g., Genome Biol, Mol Cell, PNAS |
| Peer-reviewed (mid-range) | 6–7 | Specialty journals |
| Preprints (bioRxiv, etc.) | 5–6 | Not peer-reviewed; can shift after publication |
| Conference proceedings | 4–5 | Variable review quality |
| Expert blogs / social media | 3–5 | Useful perspective but unverified |
| News / general media | 2–4 | May oversimplify |
| Wikipedia | 3–4 | Good starting point; verify primary sources |
| Internal project data | 6–7 | Your own experimental data |
| Personal opinion / notes | 1–3 | Your own notes |

**Modifiers (adjust baseline ±1–2):**

- +1: Well-cited, influential work (100+ citations)
- +1: Multiple independent replications confirm findings
- +1: Directly relevant to your projects
- −1: Small sample size, weak statistics, or poor methodology
- −1: Conflicts with other high-confidence sources
- −2: Known retractions or controversies

**Wiki meta-pages** (convention pages, index, AGENTS, confidence scoring)
default to confidence 10 — trusted by definition.

### Graph protocol

- `lint` validates the wiki and compiles `.graph` artifacts from Markdown links.
- `graph/` stores global graph files for frontends. Do not edit by hand.
- `wiki/**/*.md.graph` are page-local graph caches. Do not edit by hand.
- `.graph-cache/` stores incremental compile state. It may be deleted and regenerated.

### Semantic edge pilot

Typed semantic edges are a **pilot**, not the default retrieval path. Ordinary
CommonMark links remain the canonical readable graph. Semantic edges add a
small typed layer for experiments where a relationship label changes retrieval
quality.

Use invisible CommonMark-compatible HTML comments:

```markdown
<!-- edge: extends -> <wiki/concepts/Some Concept.md> | one-line justification. -->
```

Allowed edge types:

- `extends` — one method builds directly on an earlier method
- `alternative_to` — competing route for a similar goal
- `depends_on` — requires a component, mechanism, tool, or reagent
- `avoids` — explicitly avoids a limitation, component, or mechanism
- `outperforms` — benchmarked improvement on some axis
- `limited_by` — practical bottleneck or unresolved constraint
- `safety_concern` — links a method/component to a risk page
- `enables` — method enables an application or use case

Keep them sparse and evidence-noted. If a semantic edge is not obvious from the
page text or source trail, do not author it.

### Supersession

When newer knowledge replaces older knowledge (preprint → published, method v1 → v2,
a corrected claim), **never delete the old page** — mark it superseded and
cross-link. This preserves the audit trail while making the current truth
unambiguous.

Frontmatter convention:

- On the **superseded (older) page**: add `status: superseded` and `superseded_by: <wiki/path>`. Wrap paths with spaces in angle brackets, e.g. `superseded_by: "<wiki/summaries/foo bar.md>"`.
- On the **superseding (newer) page**: add `supersedes: [<wiki/path>, ...]`. Reciprocity is required.
- The superseded page must carry a **banner** as its first body line: `> ⚠ **Superseded by [New Title](<wiki/path>)** — one-line reason.`
- `status: current` is the implicit default; only superseded pages need the field.

Validate with `python3 wiki/scripts/knowledge_pm.py --mode supersession-check --root wiki`.

## Current articles

> **Authoritative catalog: `wiki/index.md`.** It is rebuilt on every `compile`,
> touched on every `ingest`, and enforced by `lint` (every page listed exactly
> once). Do **not** maintain a second hand-written page list here — it drifts
> out of sync.

## Promotion criteria

The wiki's consolidation tiers are `raw → summary → concept/entity`, feeding
outward into scenario cards and Skills. Explicit promotion rules:

- **`raw/inbox/` → `raw/<archive>/`**: after ingest (status `ingested`), move it to its format archive.
- **source → `wiki/summaries/`**: one summary page per ingested source. Default ingest output.
- **summaries → `wiki/concepts/`**: create/expand a concept page when an idea recurs across **≥3 summaries** or is cross-linked by **≥3 pages** — a concept *synthesizes multiple sources*, it is not a 1:1 restatement of a single summary.
- **concept → folder-split** (`wiki/concepts/<topic>/index.md` + aspect files): when a concept exceeds **~1200 words**.
- **proper noun → `wiki/entities/`**: a person/tool/org/paper earns an entity page when referenced by **≥2 pages** or central to a concept.
- **recurring workflow → scenario card → Skill**: a repeated multi-step route becomes a compact scenario card first; only a stable, reusable procedure graduates to a Skill.
- **PM reports → wiki**: `hidden-patterns` / `literature-seeds` promote only when source-backed, via the normal `ingest` path — never straight into `wiki/`.

Promotion is one-way and additive; demotion is handled by Supersession, not deletion.

## Notes for the LLM

- Language: match the source
- Tone: neutral, clear, technical when appropriate
- Depth: whatever the source material demands
- Handling contradictions: state both sides, cite each source, and record the tension in an open-questions section if unresolved
- Report-vs-write boundary: PM reports can identify gaps and patterns, but wiki pages require the normal source-backed `ingest`, `compile`, `query`, `lint`, or `audit` operation
