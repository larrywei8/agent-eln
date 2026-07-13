---
id: EXP-YYYY-MM-DD-NN
date: {DATE}
type: experiment
mode: wetlab
operator: 
title: 
project:                   # PRJ-xxxx  parent project (optional, useful for filtering by project)
protocols: []              # SOP-xxxx  (stable SOPs, do not modify)
protocol_version:          # protocol version followed for this run
used_resources: []         # PLA/CL/RGT/AB/SMP...
produced_resources: []     # new resources produced (remember to back-fill produced_in)
produced_datasets: []      # DAT-xxxx  datasets produced by this run
n_samples: 
status: complete
tags: []

# —— actual parameters for this run (record any deviation from the protocol here) ——
run_params:                # key-values vary by experiment
  cell_seeding: ""
  transfection_reagent_ratio: ""
  incubation_time: ""
  temperature: ""
deviations: []             # every deviation from the SOP (free-text list)
---
## Goal

## Conditions / Sample Sheet
Per-sample treatment, concentration, replicates. When there are many samples, use the table below (or link to the DAT manifest):

| sample_id | treatment | concentration | replicate | notes |
|---|---|---|---|---|
| SMP-... |  |  |  |  |

## Steps (following the protocol, record **actual** times/amounts/observations and any deviations)
1. (SOP says X; today did Y because ...)

## Results
![](figures/xxx.png)
Dataset: DAT-...

## Conclusions
## Follow-up / TODO
