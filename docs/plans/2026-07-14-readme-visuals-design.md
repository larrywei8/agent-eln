# README Visuals Design

## Goal

Make the README's strongest claims immediately understandable to individual wet-lab
researchers through a small set of pitch-style visuals.

## Visual system

- Cream paper background with a subtle dot grid.
- Heavy black borders, offset shadows, and bold sans-serif typography.
- Mint, lime, and cyan communicate capabilities and connected records.
- Hot pink communicates pain, broken context, and the central ELN experiment node.
- Exact, realistic fictional IDs avoid exposing live UCSD records.

## Deliverables

1. **Hero provenance:** one result connected to the literature, materials, protocol,
   experiment, sample, and dataset that produced it.
2. **Saved but disconnected:** a before/after comparison between scattered research
   artifacts and a connected Agent ELN record.
3. **Agent workflow:** an 8–10 second silent loop showing a natural-language description,
   record discovery, experiment creation, output registration, and graph completion.
4. **Four modules:** a 2×2 ELN/LIMS/Methods/Wiki diagram connected through provenance.

## Fictional record set

- `LIT-0047` — motivating paper
- `SMP-2026-0024` — cultured cells
- `RGT-0018` — treatment reagent
- `SOP-0007` — treatment protocol
- `EXP-2026-07-14-01` — treatment experiment
- `SMP-2026-0031` — extracted RNA
- `DAT-2026-0012` — sequencing dataset

## Placement

- Hero provenance below the opening promise.
- Before/after below the problem section.
- Animated workflow below “From one sentence to a traceable experiment.”
- Four modules below “One research system, four connected parts.”

## Success criteria

- Text and IDs remain legible at GitHub's README width.
- Each visual proves one claim without requiring surrounding prose.
- Static assets are lightweight SVGs; the animation is an optimized GIF with a static
  fallback frame.
- The README renders all assets from repository-relative paths.
- Tests, validation, index checks, and GitHub Actions remain green.
