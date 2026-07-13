---
id: EXP-YYYY-MM-DD-NN
date: {DATE}
type: experiment
mode: drylab
operator: 
title: 
project:                   # PRJ-xxxx  parent project (optional, useful for filtering by project)
pipeline:                  # PIPE-xxxx
scripts: []                # SCR-xxxx
inputs:                    # source of raw data
  - dataset: 
    path: 
    sha256: 
outputs:                   # figures/tables/data produced
  - figures/
  - tables/
used_resources: []
produced_resources: []
code_commit:               # git SHA of the code snapshot used for this run
env_lockfile:              # path to lockfile/requirements/environment.yml (relative to workspace)
output_manifest:           # optional path to a manifest of outputs (paths + sha256)
status: complete
tags: []
---
## Goal
## Data Source and Preprocessing
## Analysis Steps (step by step, each step with command/script + result)
### Step 1
```bash
```
![](figures/step1.png)
## Results (figures/tables)
## Conclusions
## Reproducibility Notes
