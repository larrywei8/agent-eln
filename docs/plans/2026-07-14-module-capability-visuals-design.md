# Module Capability Visuals Design

## Goal

Show individual wet-lab researchers how Agent ELN reduces data entry, turns successful
work into reusable methods, and builds source-backed research knowledge. The three
visuals extend the existing README artwork without repeating its provenance overview.

## Shared visual system

- Three separate static SVGs in a consistent 16:9 frame.
- Cream paper background, subtle dot grid, heavy black outlines, offset shadows, and
  bold editorial typography.
- Mint represents LIMS, lime represents Methods, cyan represents Wiki, and hot pink is
  reserved for fragmented or unresolved input.
- Large labels, short copy, and realistic fictional IDs remain legible at GitHub and
  mobile widths.
- All technical text is deterministic SVG text rather than generated raster lettering.

## Visual 1 — LIMS inventory capture

**Headline:** Snap it. Say it. It’s registered.

A mixed inventory composition shows three capture lanes: a kit or reagent label, one
information card representing ten mouse cages, and a rack of forty uniquely labeled
tubes. Camera and voice inputs flow through an agent extraction and review step, then
resolve into structured LIMS cards with stable IDs, identity, quantity, lot, and
location fields.

The design must distinguish extracted information from confirmed registration. A
visible review/check state communicates useful automation without implying infallible
computer vision.

## Visual 2 — Methods reuse

**Headline:** Author once. Reuse forever.

Three raw inputs—a notebook workflow, analysis commands, and a one-off script—become
versioned method records: `SOP-0012 v1.0`, `PIP-0008 v2.1`, and `SCR-0021 v1.3`.
These method cards branch into multiple experiments. Version badges make it immediately
clear which exact method revision each experiment used.

The main visual payoff is one authored method becoming reusable, citable, and
reproducible across future work.

## Visual 3 — Wiki knowledge graph

**Headline:** Ingest anything. Build your research brain.

Four source cards—PDF, poster, GitHub repository, and website—flow through ingestion
into a connected graph. The graph contains `LIT-0047`, `CON-0019`, `SOP-0012`,
`TOOL-0008`, `IDEA-0026`, and `EXP-0042`, representing a source, concept, method, tool,
research idea, and informed experiment.

Every extracted knowledge node retains a visible provenance path to a source card. The
result should read as a traceable research knowledge system, not a generic AI brain or
detached collection of summaries.

## README placement

Insert the three short capability sections immediately after “One research system,
four connected parts” and before “What this changes for you”:

1. Register inventory without data entry.
2. Turn successful work into reusable methods.
3. Build connected knowledge from any source.

This preserves the narrative progression: core promise, experiment workflow, module
overview, concrete capability proof, researcher outcomes, and technical credibility.

## Success criteria

- Each visual communicates its transformation without requiring surrounding prose.
- The three graphics feel like one family and match the current README assets.
- IDs and field labels remain exact and readable at README width.
- SVGs are lightweight, accessible, and render from repository-relative paths.
- The README remains concise and does not duplicate later technical sections.

