# eln/ — activities

This directory holds **things that happen**: experiments, meetings, ideas, projects,
literature (your reading queue), and generated reports.

Where the other modules sit:

- **`../lims/`** — the *materials* used by activities (plasmid, oligo, sample, mouse,
  cell line, reagent, instrument, dataset, ...).
- **`../methods/`** — the *how-to* referenced by activities (protocol / SOP, pipeline,
  script, skill).
- **`../wiki/`** — external knowledge (paper summaries, concepts, entities).

Operating manual: **`../AGENT.md`** at the repo root.
Schema authority: **`../tools/registry.py`**.

## Subfolders

| Path | Type | Record class |
| --- | --- | --- |
| `experiments/<year>/<date>/` | EXP-XXXX, DAILY-XXXX | daily entries + optional artifact folder |
| `meetings/` | MTG-XXXX | meeting notes, PPT transcripts |
| `ideas/` | IDEA-XXXX | sparks of ideas |
| `projects/` | PRJ-XXXX | project cards + subfolders |
| `literature/` | LIT-XXXX | reading queue, wiki-linked |
| `reports/` | (no ID) | generated markdown reports (weekly briefs, health snapshots) |
