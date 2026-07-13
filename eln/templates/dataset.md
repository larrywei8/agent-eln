---
id: DAT-YYYY-XXXX
type: dataset
name: 
created: {DATE}
created_by: 
instrument:                # INS-xxxx  instrument that produced this data
data_kind:                 # fastq | fcs(FACS) | gel-image | microscopy | csv | ...
produced_in:               # EXP-xxxx  which experiment produced it
storage:
  location:                # /data/store/... or s3://...  (actual location of large files)
  in_git: false            # whether raw large files are stored in git (true only for gel images)
n_files: 
total_size: 
manifest: manifest.csv     # row-level sample sheet (one row per file)
derived_from: []           # upstream samples/resources
tags: []
---
## Description
What this data is and how it was produced.
## Manifest Notes
Each row = one file. Column meanings are documented in the manifest.csv header. Sample conditions are recorded in this table.
## QC / Notes
