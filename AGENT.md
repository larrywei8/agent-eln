# AGENT.md — operating manual (any AI agent entering here: read this file first)

You are now inside **agent-eln**: an AI-native Electronic Lab Notebook + LIMS + wiki. It is a
folder of pure Markdown + images + scripts — no database engine, no server. You can
operate the whole thing with read/write file ops, grep, and the scripts under `tools/`.

The repo is split into three top-level modules that share one registry, one provenance
graph, one CLI:
- `eln/` — **activities**: what happens (experiments, meetings, ideas, projects,
  protocols, pipelines, scripts, skills, literature, reports).
- `lims/` — **inventory**: what you have (plasmids, oligos, dna, samples, mice, cell-lines,
  reagents, antibodies, chemicals, recipes, kits, strains, viruses, instruments, datasets,
  persons).
- `wiki/` — **knowledge**: concepts, entities, paper summaries. Cross-linked from
  ELN literature via `wiki_link` / `sources`.

> Companion specs: `conventions.md` (IDs and naming), `hierarchy.md` (tiered compound-ID
> model), `vocab.md` (controlled vocabulary for `sample_type` / `source_tissue` /
> segment codes), `ROADMAP.md` (current phase, planned work, historical specs at
> `docs/history/`).

## 0. System mental model
- **File system = database**: each record = a `.md` file with a unique ID (resource-type
  records are a folder containing `card.md` + attachments).
- **YAML frontmatter = structured fields (queryable); body = free text readable by both
  humans and AI.**
- **Relations are expressed as ID references**: the frontmatter fields `used_resources /
  produced_resources / derived_from / produced_in / protocols / pipeline / inputs /
  outputs` form the provenance graph.
- **IDs never change and are never reused.** Display names can change; the ID is the anchor.
- **Single source of truth = `tools/registry.py`.** Every type's prefix / directory /
  required fields / status vocabulary / dedicated-table columns is defined there;
  new/validate/index/type_tables/dashboard all read from it. **To add a new record type:
  add one entry in registry.py + write one templates/ template — those two steps only.**
  Don't scatter edits.
- **Only write one-way links; backlinks are auto-filled.** You only need to write
  `produced_resources / produced_datasets` in the experiment; running
  `python tools/backlinks.py --write` idempotently backfills `produced_in` on the
  resource card.
- **Project layer `project: PRJ-xxxx`** (optional): tag records with their owning project;
  the index and dashboard aggregate by project automatically.

## 1. Directory map
Shared at the repo root:
- `tools/`       indexing/validation/scaffold scripts; **`registry.py` is the schema**
- `templates/`   one template per record type
- `index/`       **fully auto-generated (do not edit by hand)**: records.csv, grouping tables,
                 per-type dedicated tables, backlinks.csv (backlinks), graph.json (provenance graph),
                 **dashboard.html (a double-click-to-open dashboard)**
- `raw/`         raw sequencer / imaging output (gitignored; point at DVC / git-annex / NAS)

**`eln/`** — activities that happen over time:
- `eln/experiments/` daily experiment notes (wet/dry) — `experiments/<year>/<date>/EXP-XXXX.md` +
                     an optional **same-named artifacts folder** `EXP-XXXX/` (see § 3 "experiment artifacts")
- `eln/projects/`    project layer (PRJ): group cross-day experiments/ideas/data/literature into a research line
- `eln/ideas/`       sparks of ideas
- `eln/meetings/`    meeting notes + PPT transcripts
- `eln/protocols/`   wet-lab SOPs
- `eln/pipelines/`   dry-lab analysis pipelines
- `eln/scripts/`     reusable code
- `eln/skills/`      AI skills (prompt + code)
- `eln/literature/`  literature library + reading notes (linked to wiki/summaries)
- `eln/reports/`     generated markdown reports (weekly briefs, health snapshots)

**`lims/`** — reusable resources you can bench-touch or point at:
- `lims/plasmids/  lims/oligos/  lims/dna/  lims/reagents/  lims/antibodies/`
- `lims/samples/  lims/mice/  lims/cell-lines/  lims/viruses/`
- `lims/chemicals/  lims/recipes/  lims/strains/  lims/kits/`
- `lims/instruments/  lims/datasets/  lims/persons/`

**`wiki/`** — Vicky-style summaries, concepts, entities, external raw sources.

## 2. ID scheme (authoritative definition in tools/registry.py; full table in conventions.md)
PLA (plasmid) OLI (oligo) DNA RGT (reagent) AB (antibody) SMP (sample) MUS (mouse) CL (cell line)
INS (instrument) VIR (virus) DAT (dataset) CHM (chemical) RCP (recipe) STR (strain) KIT (kit) PER (person)
SOP (protocol) PIPE (pipeline) SKL (skill) SCR (script)
EXP (experiment) DAILY (daily summary) LIT (literature) IDEA PRJ (project) MTG (meeting)

## 3. Standard operations you can perform
### Create a record
1. `python tools/new.py <type> --name "..." --by <you>` — **auto-allocates the ID and
   writes the file to the correct directory** (resource → folder + card.md;
   experiment → experiments/<year>/<date>/). See registry for type names.
2. Fill in required frontmatter fields (validate will check) and write the body.
3. **Only write one-way links**: if you used a resource, put it in the experiment's
   `used_resources`; new resources / data you produced go in `produced_resources` /
   `produced_datasets`. **Don't write `produced_in` by hand** — the next step fills it.
4. `python tools/backlinks.py --write` — auto-backfill `produced_in` on the resource side
   (idempotent; conflicts only warn).
5. `python tools/index.py` (rebuilds records/grouping/dedicated tables/backlinks/graph) →
   `python tools/validate.py`.
6. `python tools/dashboard.py` (optional) — refresh index/dashboard.html.
7. `git add -A && git commit -m "[EXP-...] ..."` (if the hook is installed, index+validate
   run automatically).

One-time install of the git hook: `bash tools/install-hooks.sh` (if the repo isn't
initialized, it auto-runs git init). After that, every commit auto-runs index + validate
and blocks the commit if validation fails.

### Create a derived (compound-ID) record
When the new record is a shallow derivation of an existing anchor — e.g. tissue
from a mouse, RNA prepared from that tissue, a restriction digest of a plasmid —
use `tools/derive.py` instead of `new.py`. Compound IDs are the tube-facing
projection of `derived_from` (full spec: `hierarchy.md`).

```bash
python tools/derive.py MUS-0042 BR 1                   # -> MUS-0042-BR1 (tissue: brain)
python tools/derive.py MUS-0042-BR1 RNA 1              # -> MUS-0042-BR1-RNA1 (total_RNA)
python tools/derive.py PLA-0031 RE 1 --type dna        # -> PLA-0031-RE1 (restriction digest)
python tools/derive.py MUS-0042 BR 1 --dry-run         # preview path, no writes
```

`derive.py` verifies the parent exists, checks the depth cap (≤ 2 segments after
the anchor), warns if the segment CODE is not registered in `vocab.md`, fills
`derived_from` with the parent, and infers `sample_type` / `source_tissue` /
`organism` from the CODE and inherited parent fields. `validate.py` then enforces
that anchor + direct parent exist and that `derived_from` matches the compound
ID (`hierarchy.md` rules 1–5). Go deeper than two segments by continuing via
`derived_from` alone, or mint a fresh L1 anchor for multi-parent merges.

### Query
- Trace a derivation chain: `python tools/trace.py <ID>` walks ancestors and
  descendants through the provenance graph (`--up-only` / `--down-only` /
  `--depth N` / `--json` supported; reads `index/graph.json`).
- Human view: double-click `index/dashboard.html` — an interactive provenance graph + 4 tabs:
  - **Records**: searchable / type-filterable record table (click ID to jump)
  - **This week**: all records created ≤7 days ago, sorted by date descending
  - **To read**: LIT with empty `wiki_link` (not yet ingested into Vicky wiki)
  - **Expiring**: resources with `expiry`/`expiration` within 30 days
- Find "who used PLA-0042": `grep -rl "PLA-0042" .` or read `index/records.csv`.
- Tabular queries: read `index/<type>.csv` (e.g. plasmids.csv columns = backbone/resistance/insert)
  or the grouping tables `index/lims.csv` / `index/datasets.csv` / `index/experiments.csv`.
- Backlinks ("which experiment produced this resource"): read `index/backlinks.csv` or the
  resource card's `produced_in`.
- By project: records.csv has a `project` column; or read `projects/PRJ-xxxx/card.md`.
- Provenance graph (machine-readable): `index/graph.json` (nodes = records, edges = reference
  relations, includes `(auto)` reverse edges).
- **SQL queries** (if `duckdb` is installed): `python tools/query.py "SELECT ..."` queries
  the three tables records/edges/backlinks. Example:
  `python tools/query.py "SELECT type, count(*) FROM records GROUP BY 1"`. See examples in
  `tools/query_examples.md`. The database file `index/data.duckdb` is emitted by `index.py`
  as a side effect; if duckdb isn't installed, that step is skipped and CSV/JSON are unaffected.
- **Incremental indexing**: `index.py` uses an `(mtime_ns, size)` cache (`index/.cache.json`);
  unchanged files are skipped in milliseconds. If you suspect the cache is stale →
  `python tools/index.py --force`. Add `--stats` to see parsed/cached/dropped counts.
- **Single-field frontmatter writes** (Phase 2): `tools/fm.py` provides `fm.set_field(txt, key,
  value)` / `fm.get_field(txt, key)`, auto-dispatching over block-list (`- item`), inline-list
  (`[a,b]`), and scalar styles. `backlinks.py` / `wiki_sync.py` / `new.py` have been migrated
  to this API; every backfill/append touches only the target field, no other bytes.
  **When new scripts modify frontmatter, don't use regex — call `fm.set_field` directly.**

### Literature ingest (Phase 3)
- **DOI → LIT card**: `python tools/lit_from_doi.py 10.xxxx/yyy`
  Queries Crossref for metadata → builds `literature/LIT-XXXX-<slug>.md`; DuckDB
  auto-dedups (a second run on the same DOI prints "dup" and exits).
  When there's no network / the paper is an early preprint without a DOI, add `--stub`
  to create a skeleton card first and fill metadata later.
- **PDF → LIT card**: `python tools/lit_from_pdf.py path/to/paper.pdf`
  Uses `markitdown` to extract first-page text → regex-hunts for a DOI → delegates to
  `lit_from_doi.py`; if no DOI is found, prints the first 400 chars as a hint.
- **↔ Vicky wiki bidirectional link**: the LIT card writes `wiki_link: knowledge/wiki/summaries/<slug>.md`;
  running `python tools/wiki_sync.py --fix` appends the LIT path to the corresponding
  summary's `sources:`. Use `--check` (default) to inspect without modifying.
- **Clickable wiki link**: the LIT card body must contain one line
  `📖 **Detailed notes**: [slug](../../../<wiki_link>)`. It's auto-rendered by
  `lit_from_doi.py` from the frontmatter `wiki_link`; when `wiki_link` is empty it shows
  a "Not yet studied in depth" placeholder. Don't touch this line when hand-editing the card.
- **Health check**: `python tools/health.py` runs a 9-dimension soft-quality check (DOI
  coverage, `[TBD]` markers, outline-only pages, cache drift, wiki backlink dead links,
  LIT health score, etc.); `--write` writes the report to `reports/health-YYYYMMDD.md`.
  **Does not block commits** — it's just a health check.
- **Weekly brief**: `python tools/weekly_brief.py` prints new records added this week /
  LITs to read / wiki ingests / expiring resources / a health summary.
  `--write` writes it to `reports/weekly-brief-YYYYMMDD.md`, `--json` outputs an
  automation-readable format, and `--since 14d` customizes the window.

### Core architectural principle: physical location ≠ logical attribution
Files are **always physically filed by type into lims/** (plasmid → plasmids/,
data → datasets/, sample → samples/). **Never** scatter today's outputs inside
`experiments/<date>/` as "storage". "What was obtained / produced today" is recovered
via three things:
1. Today's `experiments/<date>/_daylog.md` (inbox log, auto-appended by ingest.py);
2. Today's experiment entries' `produced_resources` / `produced_datasets` fields;
3. Edges in `index/graph.json` filtered by date.
Rationale: resources are reused long-term and looked up across days — if you leave them
scattered in a date folder, you'll never find them again. The "today's view" reconstructs
perfectly from log + links, so there's no need to actually move the files into the date
directory. **The one exception is figures/ (experimental figures)**: they sit right next
to the experiment entry.

### Resources with sequence files (plasmids etc.): card + attachments side-by-side
One resource = one folder: `card.md` (metadata + human-readable) + sequence/map files
side-by-side:
```
lims/plasmids/PLA-0042-.../ card.md  sequence.fasta  map.gb  map.png
```
Sequences **do not go into the markdown body**; the card.md `files:` field points at them.
Prefer `.gb` (GenBank — plain text + annotations, git-friendly, opens in SnapGene/Benchling)
as the primary format; `.fasta` as a pure-sequence backup; `.dna` (SnapGene binary) only
for archival.
Query all plasmids: `python tools/type_tables.py` → `index/plasmids.csv`
(columns = backbone/resistance/insert/location), filterable in any spreadsheet.
Every resource type has a dedicated table (oligos.csv/samples.csv/...).

**Auto-fill card from .gb**: `python tools/gb_annotate.py <plasmid_dir>/map.gb --write`
parses the GenBank file, writes length/topology/resistance into the frontmatter, and
appends a "## Sequence Features (auto)" table in card.md (idempotent — reruns update
only that section, not your hand-written content). Resistance genes (AmpR/PuroR/KanR...)
are auto-identified by label.

### Auto-explode a whole delivery folder from a vendor/instrument (no manual copy-paste)
Drop the whole folder into `inbox/`, then:
`python tools/ingest.py inbox/<folder> --kind fastq --exp EXP-2026-07-09-01 --instrument INS-0005 --name "..."`
It will: ① allocate a DAT- ID and build a dataset card; ② scan and compute sha256 to
generate a manifest skeleton; ③ **not move large files by default** (only register absolute
paths); add `--copy` to copy small files into the library; ④ append a log line to today's
`_daylog.md` linked to the DAT.
After that, you just fill in the manifest's sample_id/condition columns and add the DAT
to the experiment entry's produced_datasets.

**Sequencing-vendor deliveries (Novogene/BGI, with nested directories + bundled MD5)**:
use `vendor_ingest.py` instead of `ingest.py`:
`python tools/vendor_ingest.py inbox/<delivery_folder> --exp EXP-... --instrument INS-0005 --name "..."`
It will: ① auto-detect the vendor layout and **recursively** find all fastq buried under
raw_data/Sample_*/; ② find the bundled MD5.txt/*.md5, recompute md5 per file to compare,
and tag each line in the manifest as verified/MISMATCH/no-md5-listed;
③ any MISMATCH triggers a ⚠️ marker in the card and `_daylog.md` — **it means the transfer
is corrupted; re-download from the vendor**.

### Managing batch data files (fastq / FACS / gel etc. — dozens or hundreds per batch)
Don't build a card per file. Use a **two-layer structure**:
1. One `DAT-` dataset card (templates/dataset.md) = one node in the knowledge graph,
   recording the instrument (`instrument: INS-`), which experiment produced it
   (`produced_in: EXP-`), the storage path, file count, and a pointer to the manifest.
2. One manifest table (manifest.csv) = one row per file: filename, sample_id (SMP-),
   condition / concentration / replicate / gate etc. **per-sample conditions**, path,
   sha256, size.

Standard flow:
- `python tools/make_manifest.py <data_folder> --ext .fastq.gz` — auto-compute sha256 and
  generate a manifest skeleton.
- Fill in the sample_id / condition columns in a spreadsheet → build the DAT- card →
  in the experiment that produced it, write `produced_datasets: [DAT-...]`.
- **Never rename raw instrument files** (the original name is the provenance evidence);
  large files don't go into git (only path + sha256 + size in the manifest); gel images
  are small enough for git, but pair them with a lanes.csv lane table.
- Verify data integrity: `python tools/verify_data.py <manifest.csv>` (checks file
  existence and hash drift).

### Record each experiment's actual conditions and deviations (protocol is a stable SOP — don't edit it)
Each experiment's actual concentration / time / sample count / MOI etc. goes in the
**experiment entry**, not the protocol:
- `run_params:` records the actual parameters for this run; `deviations:` logs each
  deviation from the SOP and its reason.
- "Conditions/sample table for this run" — use a markdown table listing per-sample
  treatment / concentration / replicate; when there are many samples, link to the DAT's
  manifest.
- In steps, write "SOP says X, today we actually did Y, because Z". These are essential
  for analyzing batch effects and reproducing experiments.

### Experiment naming + artifacts folder convention (since 2026-07-12)

**Naming rule**: the experiment card filename and its same-named artifacts folder both
use the form `EXP-YYYY-MM-DD-NN-<slug>`, so you can see "what was done" at a glance. The
`id` in the frontmatter stays in the short form `EXP-YYYY-MM-DD-NN` (validate recognizes
this); the slug lives only at the filesystem layer.

`tools/new.py` supports `--slug` explicitly (or derives one from `--name/--title`):

```bash
# First dry-run to confirm path / slug
python tools/new.py experiment-drylab --slug guide-rna-library-design \
    --title "Guide RNA library design for 50-gene CRISPRoff screen" --by me --dry-run
# Once satisfied, actually create (drop --dry-run)
python tools/new.py experiment-drylab --slug guide-rna-library-design \
    --title "Guide RNA library design for 50-gene CRISPRoff screen" --by me
# → experiments/2026/2026-07-12/EXP-2026-07-12-01-crisproff-grna-library-design.md    (card)
# → experiments/2026/2026-07-12/EXP-2026-07-12-01-crisproff-grna-library-design/       (artifacts folder, auto)
#     ├── inputs/ scripts/ outputs/ figures/{exploratory,final}/ runs/
#     └── README.md   ← rendered from templates/exp-artifacts-readme.md
```

Slug length ≤ 60 chars, only `[a-z0-9-]`; `slugify()` converts automatically.

**Other useful flags**:
- `--dry-run`: only print the ID / path / skeleton that would be created; nothing lands.
  Use to confirm the slug.
- `--no-folder`: create the card but **not** the artifacts folder skeleton (good for
  "pure-record" experiments that don't need scripts/data).
- `--print`: only print md content, not even the path. Legacy behavior; retained.

**Renaming a slug after the fact** (you built the experiment, then thought of a better
description):
```bash
# First dry-run to see what would change
python tools/rename_experiment.py EXP-2026-07-12-01 crisproff-guide-library --dry-run
# Once satisfied, actually rename
python tools/rename_experiment.py EXP-2026-07-12-01 crisproff-guide-library
```
The tool will:
1. Locate the .md card and the same-named artifacts folder for that ID
2. Rename both in one shot (prefers `git mv`, falls back to `os.rename`)
3. In-place replace all `EXP-XXX-<old-slug>` → `EXP-XXX-<new-slug>` references in
   **the card + the folder README**
4. Grep the whole repo for **other references** (other EXP cards, project cards,
   scripts, ...) and list them — **without auto-editing** — so you decide the risk
5. The `EXP-XXX` part is never touched (ID is stable)

**One-shot manual batch replace of references elsewhere** (the tool prints this command
verbatim at the end):
```bash
grep -rl --include='*.md' -e 'EXP-XXX-<old>' Projects/ELN \
   | xargs sed -i 's|EXP-XXX-<old>|EXP-XXX-<new>|g'
```

**Rule**: the card (`EXP-XXXX-<slug>.md`) sits beside a **same-named folder**
(`EXP-XXXX-<slug>/`) that holds every output. Card = report + decision record;
folder = data + scripts + figures.

**Recommended skeleton**:

```
experiments/<year>/<date>/
├── EXP-XXXX-<slug>.md       # card (authoritative doc; put a RESUME section at the top for easy resumption)
└── EXP-XXXX-<slug>/         # same-named artifacts folder
    ├── README.md            # short artifacts manifest (optional but recommended)
    ├── inputs/              # raw inputs (never overwrite or modify)
    ├── scripts/             # analysis scripts
    ├── outputs/             # main results — latest = truth, overwrite in place
    │   ├── step0/           # organize by step (optional, depending on complexity)
    │   ├── step1/
    │   └── ...
    ├── figures/
    │   ├── exploratory/     # exploratory; will be pruned
    │   └── final/           # referenced by the report; kept
    └── runs/                # optional: timestamped snapshots of expensive computations, for comparing runs
```

**Managing outputs of iterative analysis** (to avoid the `.v1 / .v2 / _final_final`
suffix disaster):
1. **Overwrite in place + let git store history**: `outputs/stepN/foo.tsv` is the current
   truth; a re-run overwrites it. The ELN is already in git, so
   `git log --follow outputs/stepN/foo.tsv` gives you history.
2. **Iteration figures use date-naming**: `figures/exploratory/2026-07-12-manhattan.png`,
   not `_v2`. Once finalized, move to `figures/final/manhattan.png` and reference the
   latter in the report.
3. **Only use timestamped `runs/` snapshots for steps that are expensive to rerun**:
   e.g. scRNA clustering while tuning the resolution parameter and you want to compare
   several results — `runs/2026-07-12T10-30-clustering-res0.5/`. Don't use it for
   lightweight analysis.
4. **The report references artifacts; it doesn't copy them**: write "see
   `outputs/step4/foo.tsv`" in the md; don't paste tables into the md. When you
   overwrite via re-run, the narrative automatically maps to the new data.

**Card path convention**: the card's `inputs.path`, body `outputs`, and any file
reference in the body all use **paths relative to `experiments/<year>/<date>/`**
(e.g. `EXP-XXXX/inputs/foo.xlsx`). The frontmatter `outputs:` field is a list of IDs
(validate checks this), not file paths — put file paths in the body, and put only the
final OLI/DAT/CL etc. resource IDs into `outputs:`.

### Writing a "daily summary" page
Read all entries under `experiments/<year>/<date>/` → aggregate into a human-readable
daily summary (see templates/daily-summary.md), and list every resource / protocol /
skill used with links, so a reader knows "on this day, who used which resources, went
through which flow, obtained which samples/conclusions, and where to find them".

## 4. Hard rules
- After changing any file, you must run `python tools/index.py` + `python tools/validate.py`
  and validate must pass before commit (the `tools/install-hooks.sh` hook auto-runs
  these). `index.py` rebuilds all indexes in one command.
- Every ID referenced in frontmatter must exist and every required field must be present
  (validate enforces this; missing = blocked commit).
- Adding a new record type: edit `tools/registry.py` + write a template. Don't scatter edits.
- `status` uses a controlled vocabulary (see `allowed_status` in registry.py);
  out-of-range values warn.
- Compound IDs must satisfy `hierarchy.md`: the anchor and direct parent both
  exist as records, `derived_from` contains the direct parent, and depth ≤ 2.
  Structural violations block commit; unregistered segment codes only warn.
- `sample_type` / `source_tissue` / `organism` / `preservation` should draw
  values from `vocab.md`; unknown values only warn — extend the vocab rather
  than piling on synonyms.
- Raw big data (sequencing fastq, raw microscopy images) does not go into git; store on
  a data server / object storage, and in the record write only path + sha256 checksum
  + size (see "large files" in conventions.md).
- PPT / PDF must be converted to AI-readable markdown (using tools/ppt2md.py / pdf2md.py)
  before being added to the library.
- Commit messages use the `[EXP-2026-07-07-01] description` prefix format for traceability.
