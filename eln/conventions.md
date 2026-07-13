# conventions.md — IDs, naming, tags, field conventions

> **Single source of truth is `tools/registry.py`.** The table below is generated from it
> (`python tools/registry.py table`). Adding a new type = add one entry to registry.py +
> write one templates/ template. Don't scatter manual edits across multiple files.

## ID prefix table
| Category | Prefix | Number format | Example |
|---|---|---|---|
| plasmid | PLA | 4-digit | PLA-0042 |
| oligo | OLI | 4-digit | OLI-0011 |
| DNA sequence | DNA | 4-digit | DNA-0003 |
| reagent | RGT | 4-digit | RGT-0021 |
| antibody | AB | 4-digit | AB-0007 |
| sample | SMP | year-4-digit | SMP-2026-0189 |
| mouse | MUS | 4-digit | MUS-0044 |
| cell line | CL | 4-digit | CL-0003 |
| instrument | INS | 4-digit | INS-0002 |
| virus | VIR | year-4-digit | VIR-2026-0007 |
| dataset | DAT | year-4-digit | DAT-2026-0001 |
| chemical / drug / inhibitor | CHM | 4-digit | CHM-0012 |
| recipe (medium / buffer / solution) | RCP | 4-digit | RCP-0008 |
| strain / competent cells | STR | 4-digit | STR-0003 |
| commercial kit | KIT | 4-digit | KIT-0015 |
| person | PER | 4-digit | PER-0004 |
| SOP (protocol) | SOP | 4-digit | SOP-0012 |
| pipeline | PIPE | 4-digit | PIPE-0007 |
| skill | SKL | 4-digit | SKL-0005 |
| script | SCR | 4-digit | SCR-0009 |
| experiment | EXP | date-2-digit | EXP-2026-07-07-01 |
| daily-summary | DAILY | date | DAILY-2026-07-07 |
| literature | LIT | 4-digit | LIT-0001 |
| idea | IDEA | 4-digit | IDEA-0031 |
| project | PRJ | 4-digit | PRJ-0001 |
| meeting | MTG | date | MTG-2026-07-01 |

Prefixes are authoritatively defined in `tools/registry.py`; `new.py` allocates IDs based
on it, and `validate.py` uses it to check required fields and controlled status values.

## Common required frontmatter fields
`id, type, created, created_by` (experiment types use `date, operator`). **The full
required-field list and allowed status values for each type live in registry.py**, and
`validate.py` enforces them: missing required = error (blocks commit); status out of
range = warning.

## status (controlled)
Each type has its own set of legal statuses, e.g. plasmid: available/depleted/archived;
experiment: planned/in-progress/complete/failed; project: active/paused/done/dropped.
Full list is in `allowed_status` in registry.py.

## tags
Free-form tags for cross-category retrieval, e.g. `[CRISPR, TP53, lentivirus]`. Tags
are not controlled.

## project attribution (optional)
Any record can add `project: PRJ-xxxx`, and the index / dashboard will aggregate by
project automatically. Humans think in terms of projects — using this is much more
intuitive than digging through a flat ID pool.

## Large-file policy
- Goes into git: card.md, sequence fasta/gb, map png, small images, csv tables, scripts.
- Does NOT go into git: fastq/bam/raw imaging/large h5ad. Store in data area, and in the
  record write:
  ```
  data:
    - path: /data/store/GSE12345/           # or s3://... 
      sha256: <checksum>
      size: 42 GB
  ```
- Optional: use git-annex / DVC to manage large-file pointers.

## Naming
Folder name = `<ID>-<lowercase-hyphen-alias>`, e.g. `PLA-0042-plenticrispr-sgTP53/`.
