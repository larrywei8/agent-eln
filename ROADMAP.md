# ELN Roadmap

**Current schema:** v6.0 (see `python3 tools/registry.py table` for the current type list).
**Last baseline commit:** `b56d0b5` — Phase 4 baseline (2026-07-13).
**Scope reminder:** this ELN is a **single-lab research knowledge system**, not a
regulated LIMS. Design choices favor scientific reproducibility, provenance, and
literature integration over multi-user transaction safety, chain-of-custody, or
GxP audit compliance. Historical phase specs are in `docs/history/`.

The evaluation from 2026-07-13 (external audit) scored the system:

| Aspect | Score | In-scope? |
|---|---|---|
| Research ELN | 8/10 | ✅ core mission |
| Literature/knowledge management (architecture) | 8/10 | ✅ core mission |
| Small-lab resource registry | 7/10 | ✅ core mission |
| Operational LIMS | 4/10 | ⚠️ partial — only what a single operator needs |
| Regulated/GxP ELN | 2/10 | ❌ **out of scope** |

Sequenced phases below reflect the audit's plan, **re-ranked and pruned** to fit
the single-lab research scope.

## ✅ Done (2026-07-13)

### Phase 0 — Baseline freeze
- Audited 224-file uncommitted change set (Chinese→English translation +
  Phase 4 additions).
- Ran forced index rebuild, validation, health check, dashboard, all tests.
- Committed as `b56d0b5` with baseline stats: **134 records, 8 valid refs,
  26 types, 0 structural errors, 30/30 tests, 56/56 DOI coverage**.
- Known warnings deferred: 2 duplicate DOI pairs, 3 LIT wiki_link gaps.

### Phase 1 — Documentation drift
- `ai-eln-keeper` Skill: 21 → 26 types, `MOU`→`MUS`, `PROT`→`SOP`, English labels.
- `templates/daily-summary.md` and `templates/experiment-wetlab.md`:
  `PROT` → `SOP`.
- `AGENT.md`: removed broken `DESIGN.md` reference.
- Moved `BASELINE.md`, `SPEC-phase1.md`, `SPEC-phase3.md` → `docs/history/`.
- Added `SCHEMA_VERSION` to `tools/registry.py` (bumped to `"6.0"` after the
  Phase 4 baseline and the `methods/` module split).
- Added `tools/tests/test_doc_consistency.py` (5 tests) that fails CI if the
  Skill drifts from the registry or retired prefixes reappear in live docs.

## 🎯 Next (in priority order for a single-lab research ELN)

### Phase 2 — Record-quality profiles *(recommended next)*
Distinguish a valid skeleton from a lab-ready record. Structural validation
(current `validate.py`) stays the hard foundation; add **warning-level**
completeness checks so `health.py` surfaces:

- Reagents missing `location`, `lot`, or `expiry`.
- Cell lines missing `passage` or `mycoplasma` result.
- Instruments missing associated SOP.
- LIT cards that are still outline-only or unlinked to EXP/IDEA/PRJ.

**Do NOT** add roles, approval states, e-signatures, or immutable locks
(that's LIMS/GxP territory and out of scope). Keep it as visible completeness
scores in reports.

### Phase 6 (bumped up) — Close the literature-to-decision loop
This directly serves the research mission and the wiki bridge already exists:

- Enforce DOI uniqueness in `validate.py` (currently a health-report warning).
- Resolve the 2 known duplicate-DOI pairs.
- Fill the 3 recent LIT wiki_link gaps (`LIT-0058`, `LIT-0059`, `LIT-0060`).
- Add `relation` values on LIT cards: `supports`, `contradicts`, `method-from`,
  `background`, `motivates`.
- Require important LIT cards to link to at least one PRJ / IDEA / EXP.

### Phase 5 (trimmed) — Reproducibility of experiments
Focus only on what a single operator running wet+dry mixed work needs:

- Snapshot the SOP version at experiment start (`protocol_version` already
  exists on the wetlab template — enforce it in `validate.py` for finalized
  experiments).
- For computational experiments: record `code_commit`, `env_lockfile`, and
  `output_manifest` in run metadata. `verify_data.py` already handles hashes.
- **Skip** operator/reviewer role fields, approval workflows, and record
  locking. Git history is enough for a single-lab ELN.

### Phase 3 (trimmed) — Physical inventory *(only what's practical)*
Add lightweight fields, **not** an event ledger:

- Add `location`, `lot`, `expiry` to the required-field lists for reagents,
  chemicals, and kits (once existing records have been backfilled — otherwise
  validate will explode).
- Add container/storage hierarchy fields as **optional** frontmatter, filled
  in when convenient.
- **Skip** aliquot records, receive/consume events, barcodes, freeze-thaw
  tracking, and reservation queues. These pay off only in shared multi-user
  labs.

### Phase 4 (already done in schema; deepen if useful)
Compound-ID sample hierarchy (`hierarchy.md`) and vocab controlled sets
(`vocab.md`) shipped in the Phase 4 baseline. If pooling / multi-parent
derivations become common, add a `graph-quality report` (orphans, missing
expected parent, cycles) — but not before there's real data motivating it.

## ❌ Skipped by design (out of single-lab scope)

- **Regulated/GxP ELN features**: electronic signatures, audit-trail
  requirements, validation documentation, immutable locking, approval
  workflows. Out of scope unless the ELN is ever pointed at clinical or FDA
  work — at which point it becomes a separate project, not a retrofit.
- **Concurrent multi-user operation**: repository-level locks, ID allocation
  under contention, per-user permissions. Git conflict-resolution and
  single-operator discipline are sufficient.
- **Backup and disaster recovery drills**: keep documented in `PORTING.md`;
  rely on git remote + workspace snapshots. Formal restore drills only if
  the ELN starts holding irreplaceable primary data (currently: raw data
  lives in `inbox/` → hashed → referenced, not stored).
- **Custom UI beyond the dashboard**: Markdown + editor + generated dashboard
  is the interface. A full CRUD UI is a large project that risks becoming a
  competing source of truth.

## Notes for future agents

- Before touching type/prefix info anywhere, read `tools/registry.py`. That's
  the only source of truth. If you find an inconsistency, fix the doc —
  don't add a second registry.
- `test_doc_consistency.py` will fail CI if the `ai-eln-keeper` Skill drifts
  from the registry. Regenerate its table from
  `python3 tools/registry.py table` and re-run tests.
- Bump `SCHEMA_VERSION` in `registry.py` whenever the type list or a prefix
  changes.
- Historical phase specs live in `docs/history/` — they explain *why* the
  system looks the way it does but are frozen; don't edit them.
