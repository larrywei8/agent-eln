# vocab.md — Controlled vocabulary (prevents synonym sprawl)

**Principle: distinguish sub-types with controlled field values, not new ID types.**
Before adding a value, check here; if an extension is truly needed, register it here
so the whole lab stays consistent.

The parser in `tools/vocab.py` reads the tables below by scanning code-block-style
values (backticks). Keep the format machine-friendly: one value per backtick token.

---

## sample_type (physical form of a sample)

- Tissue / cell level: `tissue` `organ` `cell_pellet` `single_cell_suspension` `organoid` `FFPE`
- Nucleic acid: `gDNA` `total_RNA` `mRNA` `cDNA` `amplicon` `library`
- Protein: `protein` `lysate` `IP_eluate` `purified_protein` `membrane_fraction`
- Body fluids: `serum` `plasma` `blood` `urine` `CSF` `supernatant`

## source_tissue (tissue / organ origin — distinguishes "brain vs heart")

`brain` `heart` `liver` `kidney` `lung` `spleen` `muscle` `bone_marrow`
`intestine` `skin` `pancreas` `thymus` `lymph_node` `tumor` `blood` `embryo`

> Finer anatomical parts go in `anatomical_region` (e.g. `hippocampus`, `cortex`,
> `left_ventricle`) — not enumerated here.

## organism

Use Latin binomials (genus + species, italicised in prose):

`Homo sapiens` `Mus musculus` `Rattus norvegicus` `Danio rerio`
`Drosophila melanogaster` `Caenorhabditis elegans` `Saccharomyces cerevisiae`
`Schizosaccharomyces pombe` `Escherichia coli` `Arabidopsis thaliana`
`Gallus gallus` `Xenopus laevis` `Xenopus tropicalis` `Macaca mulatta`
`Sus scrofa`

## preservation

`fresh` `frozen` `LN2` `FFPE` `RNAlater` `fixed_PFA` `glycerol_stock` `lyophilized`

---

## Segment codes (for compound IDs)

Grouped by parent type. Each CODE is 2–4 uppercase letters, **globally unique across
groups**, and registered here. `validate.py` warns on unregistered codes.

The parser expects rows of the shape `| CODE | meaning |` inside the tables below.
Add a new code by appending a row (case-sensitive uppercase).

### Animal tissues (parent = MUS / animal) → L2, `type: sample`, `sample_type: tissue`

| CODE | Tissue |
|---|---|
| TA | tail (genotyping) |
| EAR | ear-punch (genotyping) |
| BR | brain |
| HR | heart |
| LI | liver |
| KD | kidney |
| LU | lung |
| SP | spleen |
| MU | muscle |
| BM | bone-marrow |
| TU | tumor |
| BL | blood |
| SR | serum |
| IN | intestine |
| SK | skin |
| TH | thymus |
| PA | pancreas |
| LN | lymph-node |
| EM | embryo |

### Nucleic-acid / protein preparations (parent = tissue or any sample) → L3, `type: sample`

| CODE | Meaning (sample_type) |
|---|---|
| RNA | total_RNA |
| MRNA | mRNA |
| GDNA | gDNA |
| CDNA | cDNA |
| PROT | protein/lysate |
| LIB | library (usually also registered as a DAT) |
| AMP | amplicon |
| GENO | genotyping product |

### Plasmid processing products (parent = PLA) → L2, `type: sample` or `type: dna`

| CODE | Meaning |
|---|---|
| RE | restriction digest |
| LIN | linearized |
| PCR | PCR product (using this plasmid as template) |
| GIB | Gibson / assembly intermediate |
| MP | miniprep |
| MX | maxiprep |

### Anatomical subdivisions (used as L3 under a tissue L2)

Under **heart** (HR):

| CODE | Region |
|---|---|
| LV | left-ventricle |
| RV | right-ventricle |
| AT | atrium |

> `LV` denotes left-ventricle only when the parent segment is `HR`. `LI` (top-level
> code) means liver; the two never collide because compound-ID parsing consumes
> segments left-to-right and always in context of the immediate parent.

### Cell-line derivatives (parent = CL) → L2, `type: sample` or `type: cell-line`

| CODE | Meaning |
|---|---|
| CLN | single-cell clone |
| PS | passage / subculture |
| KO | knock-out derivative |
| KI | knock-in derivative |

### Dataset derivatives (parent = DAT) → L2, `type: dataset`

| CODE | Meaning |
|---|---|
| TRIM | trimmed reads |
| ALN | alignment |
| CNT | count matrix |
| QC | QC report |

---

## Derivation-chain example (SMP-only chain via `sample_type` + `derived_from`)

```
MUS-0044 (mouse)
  └─ SMP-2026-0201   sample_type: tissue     source_tissue: brain    derived_from:[MUS-0044]
       └─ SMP-2026-0202   sample_type: total_RNA source_tissue: brain    derived_from:[SMP-2026-0201]
            └─ SMP-2026-0203   sample_type: cDNA source_tissue: brain    derived_from:[SMP-2026-0202]
                 └─ SMP-2026-0204   sample_type: library derived_from:[SMP-2026-0203]  → sequencing DAT
```

Compound-ID projection of the same chain (tube-facing view):

```
MUS-0044-BR1                 tissue derived from mouse
MUS-0044-BR1-RNA1            total_RNA from that tissue
MUS-0044-BR1-RNA1-CDNA1      cDNA from that RNA (2-segment cap → mint a fresh anchor if going deeper)
```

---

## Adding a code

1. Append a row to the appropriate group above.
2. Keep it uppercase, 2–4 letters, unique within its parent group.
3. If a subdivision code (`LV`, `RV`, …) reuses letters from another group,
   note the parent context explicitly.
4. Rerun `python tools/validate.py` — unregistered codes surface as warnings.
