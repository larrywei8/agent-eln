# hierarchy.md — Tiered ID model (compound IDs)

## Mental model
Compound IDs make tube labels self-describing, but **the single source of truth is
always the frontmatter `derived_from`**; `tools/validate.py` enforces that the two
agree. If they disagree, the frontmatter wins and the ID is wrong.

## Three tiers

- **L1 anchor** — an independently existing, independently numbered record.
  Everything that can stand on its own is an L1: `MUS-0042`, `PLA-0031`, `CL-0007`,
  `STR-0003`, `DAT-2026-0004`, plus every process/timeline record type.
- **L2 first derivation** — meaningful only relative to a parent, and worth showing
  on a label. Example: tissue from a mouse (`MUS-0042-BR1`), plasmid product
  (`PLA-0031-RE1`).
- **L3 second derivation** — derived from an L2. Example: RNA prepared from that
  tissue (`MUS-0042-BR1-RNA1`).

**Capped at L3 (two derivation segments after the anchor).** Anything deeper goes
via `derived_from` only, or mints a fresh L1 anchor.

## Segment syntax

```
<anchor-ID>-<CODE><instance>[-<CODE><instance>]
```

- `anchor-ID` matches the L1 numbering scheme for that prefix
  (`PREFIX-NNNN`, `PREFIX-YYYY-NNNN`, `PREFIX-YYYY-MM-DD-NN`, or `PREFIX-YYYY-MM-DD`).
- `CODE` = a 2–4 uppercase-letter code registered in `vocab.md` (segment codes).
- `instance` = trailing digits, optional but strongly recommended so multiple
  tubes of the same code do not collide (e.g. `BR1` vs `BR2`).
- Segments are separated by `-`. Parsing consumes the anchor first, then splits
  the remaining segments left-to-right.
- **A record's `type` is set by frontmatter, not by the ID's leading prefix.**
  `MUS-0042-BR1` has `type: sample`, not `type: mouse`.

## When to use a compound ID vs a new anchor

- **Single main parent, ≤ 2 derivation segments, tube-facing** → compound ID.
- **Deeper processing chain (RNA → cDNA → library)** → stop at L3 and continue via
  `derived_from`; or register the endpoint directly as a `DAT-`.
- **Multi-parent merge** (e.g. ligation = insert + backbone) → mint a fresh L1
  anchor (`PLA-0055`) and list every parent in `derived_from`.

## Enforced rules (checked by validate.py)

1. The anchor record must exist (`MUS-0042` must have a card).
2. The direct parent (compound ID minus its last segment) must exist as a record.
3. Frontmatter `derived_from` must contain the direct parent — this is the
   compound-ID ↔ `derived_from` consistency check.
4. Each `CODE` should be registered in `vocab.md`; unregistered codes surface as
   warnings, not hard errors.
5. Segment depth ≤ 2 (no L4). Deeper IDs surface as errors.

## Standard operations

- Create a derived record: `python tools/derive.py <parent-id> <CODE> <instance> [--type sample|dna|...]`
- Trace a chain: `python tools/trace.py <id>`
- Rebuild indexes: `python tools/index.py`
- Validate: `python tools/validate.py`

## Customising a tier

Add a `CODE` row under the appropriate parent group in `vocab.md`
(e.g. subdivide heart into `LV`, `RV`, `AT`). Keep codes uppercase, 2–4 letters,
and unique within their parent group. Rerun `validate.py` afterward.
