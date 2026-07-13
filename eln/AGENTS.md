# eln/ — activities

This directory holds **things that happen**: experiments, meetings, ideas, projects,
protocols, pipelines, scripts, skills, literature, and generated reports.

If a record represents a **material or resource** you can bench-touch or point at
(plasmid, oligo, sample, mouse, cell line, reagent, instrument, dataset, ...), it belongs
under `../lims/`, not here.

Operating manual: **`../AGENT.md`** at the repo root.
Schema authority: **`../tools/registry.py`**.

## Subfolders

| Path | Type | Record class |
| --- | --- | --- |
| `experiments/<year>/<date>/` | EXP-XXXX, DAILY-XXXX | daily entries + optional artifact folder |
| `meetings/` | MTG-XXXX | meeting notes, PPT transcripts |
| `ideas/` | IDEA-XXXX | sparks of ideas |
| `projects/` | PRJ-XXXX | project cards + subfolders |
| `protocols/` | SOP-XXXX | wet-lab standard operating procedures |
| `pipelines/` | PIPE-XXXX | dry-lab analysis pipelines |
| `scripts/` | SCR-XXXX | reusable scripts (registered as records) |
| `skills/` | SKL-XXXX | AI skills — prompt + code bundles |
| `literature/` | LIT-XXXX | reading queue, wiki-linked |
| `reports/` | (no ID) | generated markdown reports (weekly briefs, health snapshots) |
