# lims/ — inventory

This directory holds **things you have**: reusable resources you can bench-touch,
freeze, deplete, expire, or point at. Each resource is a folder (`{ID}-{slug}/`) with
`card.md` + attachments (map files, sequence FASTAs, images, manifests, ...).

Where the other modules sit:

- **`../eln/`** — *events* (an experiment you ran, a meeting you had, a paper you read).
- **`../methods/`** — *how-to* (protocols, pipelines, scripts, skills you author and reuse).
- **`../wiki/`** — external knowledge (paper summaries, concepts, entities).

Operating manual: **`../AGENT.md`** at the repo root.
Schema authority: **`../tools/registry.py`**.

## Subfolders

| Path | Type | What lives here |
| --- | --- | --- |
| `plasmids/` | PLA-XXXX | plasmid maps, sequences, resistance/backbone metadata |
| `oligos/` | OLI-XXXX | primer / probe / gRNA sequences |
| `dna/` | DNA-XXXX | DNA fragments, gBlocks, PCR products |
| `reagents/` | RGT-XXXX | reagents with vendor / catalog / lot / expiry |
| `antibodies/` | AB-XXXX | antibody target / host / clonality / applications |
| `chemicals/` | CHM-XXXX | small molecules, drugs, inhibitors (CAS, SMILES, target) |
| `recipes/` | RCP-XXXX | media / buffers / solutions (components + sterilization) |
| `strains/` | STR-XXXX | strains / competent cells (organism + genotype) |
| `kits/` | KIT-XXXX | commercial kits (vendor / catalog / reactions remaining) |
| `viruses/` | VIR-XXXX | viral preps (titer / transgene / biosafety) |
| `samples/` | SMP-YYYY-XXXX | biological samples (organism, source, derived_from) |
| `mice/` | MUS-XXXX | mice (strain / sex / genotype / cage / DOB) |
| `cell-lines/` | CL-XXXX | cell lines (organism / tissue / passage / mycoplasma) |
| `instruments/` | INS-XXXX | shared equipment (vendor / model / booking / SOP) |
| `datasets/` | DAT-YYYY-XXXX | sequencer / imaging / instrument datasets (manifest + hashes) |
| `persons/` | PER-XXXX | lab members and external contacts (role / ORCID / email) |

## LIMS ↔ ELN boundary

- LIMS owns **state**: is this reagent still available, where is it stored, when does it expire?
- ELN owns **events**: which experiment used it, which experiment produced it?
- The link goes through frontmatter: experiments declare `used_resources` /
  `produced_resources` / `produced_datasets`; `tools/backlinks.py --write` auto-fills the
  reverse `produced_in` on the LIMS card.
