# {ID} — artifact folder

**Card (authoritative document)**: `../{ID}-{SLUG}.md`

This folder holds all output materials for the experiment. The card is the "report + decision record"; this folder is "data + scripts + figures".

## Structure

```
{ID}-{SLUG}/
├── inputs/         raw inputs (never overwritten or modified)
├── scripts/        analysis scripts (git preserves iteration history)
├── outputs/        main results — latest = truth, updated in place
├── figures/
│   ├── exploratory/  exploratory, will be pruned
│   └── final/        referenced by the report, kept
└── runs/           optional: timestamped snapshots of expensive computations (for parameter comparison)
```

## Managing Outputs from Repeated Analyses

1. **Overwrite in place + let git store history**: rerunning the same analysis overwrites `outputs/foo.tsv`; the iteration trail lives in git log. Do not create `.v1 / .v2 / _final_final` suffixes.
2. **Name iterative figures by date**: `figures/exploratory/2026-07-12-manhattan.png`, not `_v2`. Once finalized, move to `figures/final/` and reference from the report.
3. **Only use timestamped `runs/` snapshots for expensive-to-rerun steps.**
4. **Reports reference outputs, do not duplicate them**: in the md write "see `outputs/foo.tsv`" — do not paste tables into the md.

See `AGENT.md § 3 — Experiment naming + artifact folder conventions` for details.
