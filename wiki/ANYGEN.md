# Larry's Wiki Knowledge Base

> Schema document — read at the start of every session together with `file wiki/index.md`.
> Update after every major compile, ingest batch, or structural change.

## Scope

Canonical project address: `/home/workspace/knowledge`.

`wiki/` inside this project means `/home/workspace/knowledge/wiki/`, the generated knowledge page subtree. There should not be a separate active top-level `/home/workspace/wiki` project; the early duplicate scaffold from 2026-05-07 was archived at `/home/workspace/Archive/wiki-legacy-20260507` on 2026-05-11 after confirming its content was already represented here.

What this wiki covers:

- Anything I want to learn, remember, or reference — research papers, articles, project notes, tools, books, ideas, people, and technical concepts
- No subject is off-limits; this is a general-purpose personal knowledge base

What this wiki deliberately excludes:

- Daily journals or task lists (those go elsewhere)
- Sensitive personal information I wouldn't want surfaced

## Operations

This wiki follows the llm-wiki-anygen skill's five operations: `compile`, `ingest`, `query`, `lint`, `audit`.
Every operation appends an entry to `file log/YYYYMMDD.md`.

### Weekly PM / agent loop

Run `python3 knowledge/scripts/knowledge_pm.py --mode agent` from `/home/workspace` to generate the wiki's second-brain operating reports:

- `outputs/discovery/YYYYMMDD.md` — "unknown known" hidden-theme and cross-link report
- `outputs/gaps/YYYYMMDD.md` — open questions, missing provenance, inbox, and lint-drift work queue
- `outputs/evolution/YYYYMMDD.md` — time-series style knowledge-state metrics
- `outputs/typed-edges/edges.tsv` — lightweight typed-edge export for future KAG/RAG experiments
- `outputs/ingest-plans/YYYYMMDD.md` — source-intake queue from `raw/inbox/` with recommended Vicky actions
- `outputs/hidden-patterns/YYYYMMDD.md` — weekly cross-domain pattern hypotheses and reflection prompts
- `outputs/literature-seeds/YYYYMMDD.md` — search-ready prompts from explicit gaps and high-frequency themes
- `outputs/dashboard.md` — latest report pointers

Use `--mode pm` for the original health-report-only run. The agent loop is still conservative: it plans and prioritizes ingest, gap research, and hidden-pattern review, but it does not automatically rewrite wiki pages or send emails. Vicky should execute the actual `ingest` operation from the generated plan, then rerun lint.

#### Fast health preflight (run before lint)

`python3 knowledge/scripts/knowledge_pm.py --mode health` is a quick, **side-effect-free** structural preflight to run *before* the expensive `lint` (which also recompiles all `.graph` artifacts). It does not write reports, touch pages, or compile the graph. It checks:

- **Empty pages** (no body text) — FAIL
- **Malformed frontmatter** (indented fence, or no closing `---`) — FAIL. Note: `lint` does **not** validate frontmatter completeness, so this catches truncated/corrupt pages lint passes.
- **Index sync** — every page linked from `wiki/index.md` at least once (no orphans) and every index link resolves (no dead links) — FAIL. Multiple listings of the same page across index sections are expected and not flagged.
- **Pages with no / incomplete frontmatter** (missing any of `title, type, created, updated, confidence, confidence_rationale, sources, tags`) — WARN (convention drift lint doesn't enforce)
- **Duplicate page titles within the same type** — WARN
- **Log coverage** — newest `log/` entry age, and pages whose `updated` date is newer than the last log entry (possibly unlogged edits) — WARN

Exit code is `1` if any blocking (FAIL) issue is found, `0` otherwise — so it can gate a pipeline before `lint`. Clean output means it is safe to run the full `lint`.

#### Ad-hoc query modes (interactive, no side effects)

The same script also supports read-only queries:

- `python3 knowledge/scripts/knowledge_pm.py --mode search --query "..." [--limit N]` — BM25 keyword search across every wiki page (title, tags, body). Use for "where did I write about X" lookups.
- `python3 knowledge/scripts/knowledge_pm.py --mode query --edge-kind <kind> [--source <glob>] [--target <glob>] [--limit N]` — filter the typed-edge export. Edge kinds: `links_to`, `has_tag`, `source_for`, `has_type`. Globs accept `*` wildcards (e.g. `--source "wiki/concepts/*"`).
- `python3 knowledge/scripts/knowledge_pm.py --mode ask --query "..." [--seed-limit 5] [--neighbor-limit 8]` — closed-loop retrieval: BM25 top-N seeds + their 1-hop typed-edge neighbors. Produces a "based on these pages you should read" answer with no LLM call.
- `python3 knowledge/scripts/knowledge_pm.py --mode audit-entities [--thin-words 200] [--limit N]` — writes `outputs/audits/entity-audit-YYYYMMDD.md`. **Merge candidates are only highly-similar duplicates** (entities whose normalized title or an alias collides) — thin or low-inlink entities are *never* merge candidates (the full entity roster is preserved). Thin entities are listed separately as *enrich* candidates to expand when convenient.
- `python3 knowledge/scripts/knowledge_pm.py --mode preprint-status [--check-online] [--limit N]` — scans `raw/refs/*.md` for preprint DOIs (bioRxiv `10.1101`/`10.64898`, Research Square, OSF, Preprints.org, arXiv). With `--check-online`, queries Crossref for `is-preprint-of` relations and flags newly-published transitions for confidence re-check. Writes `outputs/audits/preprint-status-YYYYMMDD.md`.
- `python3 knowledge/scripts/knowledge_pm.py --mode quality` — non-blocking quality report (A6). Flags thin (<120 words), uncited (no `sources`), or structure-poor (no sub-headings / no outbound links) pages to `outputs/audits/quality-YYYYMMDD.md`. WARN-only: it never edits pages and never gates. Feeds the human/Vicky `audit/` loop.
- `python3 knowledge/scripts/knowledge_pm.py --mode supersession-check` — validates supersession metadata (A1). Confirms `superseded_by`/`supersedes` links resolve and are reciprocal, that superseded pages carry `status: superseded` + the banner, and lists preprint-sourced pages as supersession candidates. Writes `outputs/audits/supersession-YYYYMMDD.md`. Non-blocking.

All read-only modes touch no wiki pages, write no reports outside `outputs/audits/`, and skip lint. The `query` and `ask` modes read `outputs/typed-edges/edges.tsv`, so run `--mode agent` at least once first.

#### Automation

Zo automation runs this PM / agent loop weekly on Mondays at 08:00 America/Los_Angeles. Clean runs should stay silent. Report to Larry only when:

- the script fails,
- wiki lint fails,
- `outputs/ingest-plans/YYYYMMDD.md` shows queued source files in `raw/inbox/`,
- a generated gap/hidden-pattern report clearly needs a user decision.

The automation is a report-and-triage loop, not an autonomous writer. It must not rewrite wiki pages, delete sources, or send external messages without an explicit user request.

#### Report promotion policy

PM outputs are working reports until promoted:

- `outputs/ingest-plans/` → execute via the normal `ingest` operation, then log and lint.
- `outputs/hidden-patterns/` → promote only stable, source-backed patterns into `wiki/concepts/`; otherwise leave as reflection prompts.
- `outputs/literature-seeds/` → use as search prompts; do not treat them as citations until real sources are fetched and ingested.
- `outputs/evolution/` → use for trend monitoring; promote durable methodology changes to `ANYGEN.md`, `Memory/scenarios/`, or a Skill.
- `outputs/typed-edges/` → machine-readable export only; do not hand-edit.

#### Output retention

Each weekly-report category (`discovery/`, `gaps/`, `evolution/`, `typed-edges/`, `ingest-plans/`, `hidden-patterns/`, `literature-seeds/`) keeps only the **8 most recent dated files**. Older files are moved into `outputs/_archive/YYYY-MM.tar.gz` (grouped by the source file's month) by the PM script's housekeeping step. `outputs/queries/`, `outputs/dashboard.md`, `outputs/typed-edges/edges.tsv` (current snapshot), `outputs/lint-*.log`, and any README/asset files are exempt.

## Naming conventions

- **Concept pages** (`wiki/concepts/`): Title Case noun phrases.
- **Folder-split concepts** (`wiki/concepts/<topic>/`): used when a topic exceeds \~1200 words. Contains `file index.md` + one file per aspect.
- **Entity pages** (`wiki/entities/`): Proper names — people, tools, organizations, papers.
- **Summary pages** (`wiki/summaries/`): kebab-case source slug.

All pages require YAML frontmatter: `title`, `type`, `created`, `updated`, `confidence`, `confidence_rationale`, `sources`, `tags`.

Optional but recommended: `last_reviewed: YYYY-MM-DD`. Set or refresh it whenever you re-read a page and confirm it still holds. The PM evolution report uses it to flag stale-trusted pages (≥90 days, confidence ≥7) and low-confidence pages overdue for review (≥30 days, confidence ≤5). Pages without the field appear in a separate bootstrap list.

### Diagrams and formulas

- All diagrams are **mermaid**. No ASCII art.
- All formulas are **KaTeX** (inline `$...$` or block `$$...$$`).

### Raw file policy

- **All new source material first lands in `raw/inbox/<bucket>/`** (one of `authored/`, `unread-papers/`, `web-saves/`, `books-highlights/`, `talks-workshops/`, `project-notes/`, `lab-protocols/`). This is the only correct intake path. See `raw/inbox/README.md`.
- After Vicky ingests an inbox file, move the original into the appropriate **format-based archive** under `raw/articles/`, `raw/papers/`, `raw/notes/`, `raw/protocols/`, `raw/source/`, `raw/tools/`, or `raw/pdf/`. The inbox bucket records *what kind of brain input it was*; the archive directory records *what format it is*.
- Large binaries → create a pointer file at `file raw/refs/<slug>.md` with `kind: ref` and `external_path` fields. Do not copy the binary.
- For research papers, record whether full text was captured in the **Full-text coverage of papers** table below (not in per-file frontmatter). When a fetch is blocked, leave a `raw/refs/<slug>-access.md` note describing the routes attempted.
- Do not drop new files directly into `raw/articles/`, `raw/papers/`, etc. — those are archive layers, not intake. The PM gap report flags any file lingering in `raw/inbox/` for more than 14 days.
- **Inbox status lifecycle.** Inbox files may carry a `status:` frontmatter field: `inbox` (default, awaiting ingest) → `processing` → `ingested` (done; archive it out of inbox) or `failed` / `blocked` (attempted but couldn't complete). Failed/blocked items should also record `attempts:` (integer) and `last_error:` (one-line note, e.g. a paywall/Cloudflare block). The PM `ingest-plan` report excludes `ingested` files from the active queue, surfaces `failed`/`blocked` items in a dedicated "needs a human decision" section with their error and attempt count, and reminds you to archive any `ingested` file still sitting in the inbox. See `raw/inbox/README.md`.

### Quarto bridge

Quarto belongs beside the wiki, not inside it. Keep `.qmd` projects under `Projects/` or another research-project folder; do **not** convert `wiki/**` pages to `.qmd` and do not add Quarto-only syntax to canonical wiki pages.

Two bridge directions are allowed:

- **Wiki → Quarto:** a `.qmd` may cite wiki pages with ordinary Markdown links. Run `python3 knowledge/scripts/quarto_bridge.py export-citations <path/to/file.qmd>` to resolve those links and export stable snapshots plus `wiki-citations.bib` under `outputs/quarto-bridge/<qmd-slug>/`.
- **Quarto → Wiki:** mark durable conclusions in a `.qmd` with `<!-- wiki-promote: start --> ... <!-- wiki-promote: end -->`, then run `python3 knowledge/scripts/quarto_bridge.py promote-finding <path/to/file.qmd>`. The helper writes a provenance-rich note to `raw/inbox/project-notes/`; Vicky must then perform the normal `ingest` operation before any `wiki/` page is created or updated.

Worked Q3 proof: `Projects/quarto-pilot/demo-executable/csv-analysis-demo/csv-analysis.qmd` exports cited pages to `outputs/quarto-bridge/csv-analysis/`, promotes a finding to `raw/inbox/project-notes/20260707-quarto-csv-analysis-bridge-finding.md`, and is ingested as `wiki/summaries/quarto-csv-analysis-bridge-finding-20260707.md`.

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
| Peer-reviewed (mid-range) | 6–7 | Specialty journals, solid but narrower impact |
| Preprints (bioRxiv, etc.) | 5–6 | Not peer-reviewed; can shift after publication |
| Conference proceedings | 4–5 | Variable review quality |
| Expert blogs / WeChat / social media | 3–5 | Useful perspective but unverified |
| News articles / general media | 2–4 | Lay summaries, may oversimplify |
| Wikipedia | 3–4 | Good starting point, verify primary sources |
| Internal project data | 6–7 | Your own experimental data |
| Personal opinion / notes | 1–3 | Your own notes |

**Modifiers (adjust baseline ±1–2):**

- +1: Well-cited, influential work (100+ citations)
- +1: Multiple independent replications confirm findings
- +1: Directly relevant to your projects
- −1: Small sample size, weak statistics, or poor methodology
- −1: Conflicts with other high-confidence sources
- −2: Known retractions or controversies

**Wiki meta-pages** (convention pages, index, ANYGEN, confidence scoring) default to confidence 10 — trusted by definition.

### Graph protocol

- `lint` validates the wiki and compiles `.graph` artifacts from Markdown links.
- `graph/` stores global graph files for frontends. Do not edit by hand.
- `wiki/**/*.md.graph` may appear as page-local graph caches. Do not edit by hand.
- `.graph-cache/` stores incremental graph compile state. It may be deleted and regenerated.

### Semantic edge pilot

A2 semantic edges are a **pilot**, not the default retrieval path. Ordinary CommonMark links remain the canonical readable graph. Semantic edges add a small typed layer for experiments where a relationship label changes retrieval quality.

Use invisible CommonMark-compatible HTML comments:

```markdown
<!-- edge: extends -> <wiki/concepts/Twin Prime Editing.md> | PA uses twinPE-generated flaps as the target-site priming layer. -->
```

Allowed edge types:

- `extends` — one method builds directly on an earlier method.
- `alternative_to` — competing route for a similar editing goal.
- `depends_on` — requires a component, mechanism, tool, or enabling reagent.
- `avoids` — explicitly avoids a limitation, component, or mechanism.
- `outperforms` — benchmarked improvement on payload, efficiency, or safety axis.
- `limited_by` — practical bottleneck or unresolved constraint.
- `safety_concern` — links a method/component to a risk page.
- `enables` — method enables an application, cargo, or cell-type use case.

The pilot parser in `knowledge/scripts/knowledge_pm.py` emits these comments into `outputs/typed-edges/edges.tsv` and surfaces them in `--mode ask --semantic` only. Keep them sparse and evidence-noted. If a semantic edge is not obvious from the page text or source trail, do not author it.

### Supersession

When newer knowledge replaces older knowledge (preprint → published, method v1 → v2, a corrected claim), **never delete the old page** — mark it superseded and cross-link. This preserves the audit trail (the whole point of `Memory/.git` + immutable `raw/`) while making the current truth unambiguous.

Frontmatter convention:

- On the **superseded (older) page**: add `status: superseded` and `superseded_by: <wiki/path>`. Wrap paths with spaces in angle brackets, e.g. `superseded_by: "<wiki/summaries/foo bar.md>"`.
- On the **superseding (newer) page**: add `supersedes: [<wiki/path>, ...]`. Reciprocity is required — each end must point at the other.
- The superseded page must also carry a **banner** as its first body line: `> ⚠ **Superseded by [New Title](<wiki/path>)** — one-line reason.`
- `status: current` is the implicit default; only superseded pages need the field.

Validate with `python3 knowledge/scripts/knowledge_pm.py --mode supersession-check` (checks resolution, reciprocity, status, banner; lists preprint candidates). This is a Larry-local validator; emitting a `supersedes` typed edge from `lint_wiki.py` into `graph/` is a planned follow-up — do not hand-edit `.graph` files.

## Current articles

> **Authoritative catalog: [`wiki/index.md`](wiki/index.md).** It is rebuilt on every `compile`, touched on every `ingest`, and enforced by `lint` (every page listed exactly once). Do **not** maintain a second hand-written page list here — it drifts out of sync (that was the cause of the 2026-06-08 cleanup). This section records only counts and the last health check.

*Counts as of 2026-06-15 (lint clean):* **295 graph nodes, 1315 graph edges, 0 lint issues.** Use `wiki/index.md` and `graph/stats.graph` for exact current counts; this line is only a coarse health snapshot.

### 2026-06-08 maintenance notes (for other agents)

- The old per-type article list that used to live here was removed in favor of the pointer above. If you need the catalog, read `wiki/index.md`.
- Duplicate entities were merged: `Co-Scientist.md` → **`Google Co-Scientist.md`** (canonical), and `David R Liu.md` → **`David R. Liu.md`** (canonical, with the period). Do not recreate the dropped variants.
- `wiki/concepts/RegVelo.md` never existed (only the entity `wiki/entities/RegVelo.md`); earlier text here that implied a RegVelo *concept* page was stale.
- Links to not-yet-written pages (Grok, LlamaIndex, DeepMind, Gemini Models, Multi-Agent Scientific Discovery, SpatialAgent, MCP) were converted to plain text rather than left as dead links. Create real pages before re-linking.
- Run `python3 /home/workspace/Skills/llm-wiki-anygen/scripts/lint_wiki.py .` after edits; it regenerates all `graph/` artifacts. Never hand-edit `.graph` files.

## Full-text coverage of papers

> Tracks which ingested research papers have full text vs. only an abstract/metadata. **Update this table whenever you ingest a paper or later obtain a full text.** Status values: `full` = full text or PDF stored; `partial` = abstract + figure captions + supplementary only, main text gated; `abstract` = abstract/metadata only.
> Full-text PDFs live in `files/papers/`; extracted text in `raw/papers/`; access attempts are recorded in `raw/refs/*-access.md` / `*-pdf.md`. This table is the authoritative per-paper status (per-file frontmatter is unreliable because some papers span several raw files and a few raw notes have malformed/indented frontmatter).

### Recently resolved (full text obtained 2026-06-08)

Fetched open-access from the Zo server; see `raw/refs/20260608-fulltext-batch-access.md`. Binaries in `files/papers/20260608-fulltext-fetch/`, extracted text in `raw/papers/20260608-fulltext-fetch/`.

- Liu et al. 2019 (Cell) — PMC6553491
- Boyle et al. 2017 (Cell) — PMC5536862
- Freimer et al. 2022 (Nat. Genet.) — PMC10035359
- Cas12a2 RNA-triggered cell killing (Nature 2026) — Nature OA PDF
- scpFormer (arXiv:2604.20003) — arXiv PDF
- The Last Human-Written Paper / Agent-Native Research Artifacts (arXiv:2604.24658) — arXiv PDF
- Meng et al. 2026 — ScientistOne: Towards Human-Level Autonomous Research via Chain-of-Evidence (arXiv:2605.26340) — arXiv PDF and extracted full text; official project page and generated-artifact repository also captured
- Gerlach/Milind 2025 — High false sign rates in TWAS (bioRxiv) — HTML full text via institutional Mac browser; `raw/papers/20260608-fulltext-fetch/gerlach-milind-2025-twas-fsr-fulltext.txt`

### Papers still missing full text (abstract/metadata only)

| Paper | Venue | DOI / ID | Blocker | Retrieval route |
|---|---|---|---|---|
| Milind et al. — Gene dosage response curves | Cell Genomics 2026 | 10.1016/j.xgen.2026.101221 | Cell press (Cloudflare); not yet fetched | OA — institutional browser or retry |
| Zhu/Dann — Genome-scale Perturb-seq in CD4+ T cells | bioRxiv 2025 | 10.64898/2025.12.23.696273 | Cloudflare 403 (server); large paper (~130k chars) | bioRxiv OA — institutional browser / manual PDF |
| Zeng et al. — GeneBayes gene constraint | Nat. Genet. 2024 | 10.1038/s41588-024-01820-9 | No PMC; paywall | Institutional browser |
| Hu et al. — Cas13 RNA base editing for HCM | Circulation 2026 | 10.1161/CIRCULATIONAHA.125.076905 | No PMC; closed access | Institutional browser |
| Bergmann & Jovinge — Isolation of cardiomyocyte nuclei | JoVE 2012 | 10.3791/4205 | PMC3476409 is a metadata stub; publisher block | Institutional browser (JoVE) |
| Hoffman — Dog/cat/human bed partners | Anthrozoös 2018 | — | Paywall; author-interview + press release only | Institutional browser |
| Zhang et al. — SPAC-seq / TARDIS spatial CRISPR screening | Cell 2026 | 10.1016/j.cell.2026.04.049 / PMID 42190664 | Cell PDF route returned blocked HTML from Zo server; PubMed/Crossref/TARDIS repo captured | Institutional browser or user-supplied PDF |

### Papers with partial full text

| Paper | Venue | DOI | What's stored |
|---|---|---|---|
| Decima — Decoding sequence determinants of gene expression | Nature Methods 2026 | 10.1038/s41592-026-03102-0 | Abstract, figure captions, data/code availability + **supplementary PDF & table**; main text still gated |

All other ingested papers have full text stored (PDF in `files/papers/` and/or extracted text in `raw/papers/`).

### Recently resolved (full text obtained 2026-06-19)

Fetched open-access from Nature on the Zo server; PDFs in `files/papers/20260619-natbiotech-prime-editing/`, extracted text in `raw/papers/20260619-natbiotech-prime-editing/`, source refs in `raw/refs/`.

- Sakai et al. 2026 — Directed evolution of small RNA-stabilizing motifs that improve prime-editing efficiency — Nature Biotechnology — DOI `10.1038/s41587-026-03123-2`
- Tao et al. 2026 — AI-guided redesign of laboratory-evolved reverse transcriptases enhances prime editing — Nature Biotechnology — DOI `10.1038/s41587-026-03149-6`

### Recently resolved (full text obtained 2026-06-22)

Fetched open-access from Nature on the Zo server; PDF in `files/papers/20260622-pe-lnp/`, extracted text in `raw/papers/20260622-pe-lnp/`, source refs in `raw/refs/`.

- Jiang et al. 2026 — Efficient prime editing in vivo and in vitro using lipid nanoparticles — Nature Nanotechnology — DOI `10.1038/s41565-026-02200-6`

### Recently resolved (full text obtained 2026-06-28)

Larry provided the valid bioRxiv PDF after the server-side route was blocked by a JavaScript/cookie gate; PDF in `files/papers/20260628-proto-fulltext/`, extracted text in `raw/papers/20260628-proto-fulltext/`, source ref in `raw/refs/proto-biorxiv-fulltext-2026.md`.

- Merchant et al. 2026 — A high-level programming language for generative biology with Proto — bioRxiv — DOI `10.64898/2026.06.22.733870`

### Recently resolved (full text obtained 2026-06-29)

Fetched open-access from arXiv on the Zo server; PDF in `files/papers/20260629-logos/`, HTML and extracted text in `raw/papers/20260629-logos/`.

- Li et al. 2026 — Speaking the Language of Science: Toward a General-Purpose Generative Foundation Model for the Natural Sciences — arXiv — ID `2606.16905`

### Recently source-captured (PDF blocked 2026-06-29)

Nature Biotechnology HTML and extracted text preserved from Larry's Google/Nature share; direct PDF endpoints returned HTML access shells, so the source is not yet full PDF-backed.

- Buchholz 2026 — A retargeted recombinase for precise insertion of large DNA — Nature Biotechnology News & Views — DOI `10.1038/s41587-026-03198-x`
- Fauser et al. 2026 — Retargeted serine integrases for one-step, precise integration of large DNA sequences in human cells — Nature Biotechnology — DOI `10.1038/s41587-026-03186-1`

## Open research questions

Genuine open scientific questions only. Tool/skill adoption decisions live in `backlog/tools-adoption.md`. Source ingest TODOs live in `backlog/ingest-queue.md`.

### Genome editing

- Which SCN1A Dravet syndrome alleles are directly base-editable, and can delivery be made transient and broad enough for human CNS translation?
- Can PA reach beyond 11 kb with optimized multi-donor strategies?
- Can QuadPE and PA be combined (e.g., QuadPE flaps + linear donor synergy)?
- What are the structural constraints on QuadPE cargo beyond 26 kb?
- How can TJ-PE's template-jumping mechanism be improved for cargoes >800 bp? Split circular petRNA shows promise — can it reach >1 kb?
- Can the TJ-PE concept of a single-pegRNA be merged with QuadPE (4 pegRNAs) or PA (linear donors) for non-viral in vivo applications?
- Is AZD-7648 safe enough for therapeutic prime assembly applications, or are alternative NHEJ inhibitors needed?
- What genome-wide off-target effects distinguish TJ-PE, PA, and QuadPE — has anyone done a head-to-head comparison?
- Can MINT-style retargeted Bxb1 preserve high on-target large-payload insertion while controlling pseudosite integration, inversions, and off-target rearrangements in primary therapeutic cell types?

### Single-cell / computational biology

- How well does scpFormer generalize across unseen clinical cohorts, antibody panels, and disease contexts?
- Is RegVelo practically usable on Larry's single-cell datasets, and does adding GRN priors improve fate-driver ranking over CellRank/scVelo/dynamo baselines?
- Can IRISeq reproduce its brain-aging findings in human tissue, FFPE samples, or perturbation models that separate lymphocyte depletion from DNA-repair defects?
- Can OINS niche-instruction principles be tested in human organoids or organ-on-chip systems, especially by perturbing ECM-integrin and LOX-mediated matrix crosslinking?

## Backlog pointers

- Tool / skill / framework adoption decisions → `backlog/tools-adoption.md`
- Paper / source ingest queue → `backlog/ingest-queue.md`

Items move *out* of these backlogs only when (a) ingested into `wiki/`, (b) installed as a `Skill`, or (c) explicitly rejected with a one-line rationale.

## Audit backlog

*(none — run* `python3 scripts/audit_review.py <wiki-root> --open` *to refresh)*

## Notes for the LLM

- Language: en
- Tone: neutral, clear, technical when appropriate
- Depth: whatever the source material demands — from high-level overviews to deep technical breakdowns
- Handling contradictions: state both sides, cite each source, and add to Open Research Questions if unresolved
- Report-vs-write boundary: PM reports can identify gaps and patterns, but generated wiki pages require the normal source-backed `ingest`, `compile`, `query`, `lint`, or `audit` operation.
- Promotion path: recurring report patterns should become compact scenario cards before becoming Skills; source-backed external knowledge should go through `raw/` and `wiki/`, not directly into Memory.

## Promotion criteria

The wiki's implicit consolidation tiers are `raw → summary → concept/entity`, feeding outward into `Memory/` scenario cards and `Skills/`. Make the promotion rules explicit so any agent applies them the same way:

- **`raw/inbox/` → `raw/<archive>/`**: after Vicky ingests an inbox file (status `ingested`), move it to its format archive. Automatic, per the Raw file policy.
- **source → `wiki/summaries/`**: one summary page per ingested source. This is the default ingest output.
- **summaries → `wiki/concepts/`**: create/expand a concept page when an idea recurs across **≥3 summaries** or is cross-linked by **≥3 pages** — a concept *synthesizes multiple sources*, it is not a 1:1 restatement of a single summary. (Example: `Complex Trait Regulatory Genetics` synthesizes the omnigenic/polygenic summary cluster; `Perturb-seq Cost Reduction Strategies` folds several method papers.)
- **concept → folder-split** (`wiki/concepts/<topic>/index.md` + aspect files): when a concept exceeds **~1200 words**.
- **proper noun → `wiki/entities/`**: a person/tool/org/paper earns an entity page when referenced by **≥2 pages** or central to a concept.
- **recurring workflow → `Memory/scenarios/` → `Skills/`**: a repeated multi-step route becomes a compact scenario card first; only a stable, reusable procedure graduates to a Skill (per root `AGENTS.md` promotion path).
- **PM reports → wiki**: `hidden-patterns`/`literature-seeds` promote only when source-backed, via the normal `ingest` path — never straight into `wiki/` or `Memory/` (see Report promotion policy).

Promotion is one-way and additive; demotion is handled by Supersession, not deletion.
