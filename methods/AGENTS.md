# methods/ — how-to

This directory holds **how you do things**: the protocols, pipelines, scripts, and skills
you author, version, and reuse across many experiments. They answer the question
*"how do I do X?"* — as opposed to *what happened* (ELN) or *what you have* (LIMS).

Where the other modules sit:

- **`../eln/`** — *events* that reference these methods (an experiment declares
  `protocols: [SOP-0001]` or `pipeline: PIPE-0004`).
- **`../lims/`** — *materials* that the methods act on (reagents, plasmids, samples).
- **`../wiki/`** — external knowledge (paper summaries, concepts, entities).

Operating manual: **`../AGENT.md`** at the repo root.
Schema authority: **`../tools/registry.py`**.

## Subfolders

| Path | Type | What lives here |
| --- | --- | --- |
| `protocols/` | SOP-XXXX | wet-lab standard operating procedures |
| `pipelines/` | PIPE-XXXX | dry-lab analysis pipelines (nextflow, snakemake, notebook) |
| `scripts/` | SCR-XXXX | reusable scripts (registered as records) |
| `skills/` | SKL-XXXX | AI skills — prompt + code bundles |

## Methods ↔ ELN boundary

- Methods own **the recipe**: version, language/env, entrypoint, category.
- ELN owns **the run**: which experiment invoked which protocol / pipeline / script on which day.
- The link goes through frontmatter: experiments declare `protocols`, `pipeline`, `scripts`;
  `tools/backlinks.py --write` walks the graph so a method's usage history is discoverable.
