#!/usr/bin/env python3
"""registry.py — single source of truth for the whole library.

**To add a new record type, add one entry here** and write a templates/<template>.md.
new.py / validate.py / type_tables.py / index.py / dashboard.py all read from here;
do not scatter type information elsewhere. The ID table in conventions.md can also be
auto-generated from this file (see `python tools/registry.py table` at the end).

Per-field notes:
  prefix        : ID prefix (unique).
  id_style      : numbering style
                  seq4       -> PLA-0042            (global 4-digit sequence)
                  year-seq4  -> SMP-2026-0189       (year + 4-digit sequence)
                  date-nn    -> EXP-2026-07-08-01   (date + 2-digit sequence within the day)
                  date       -> MTG-2026-07-08 / DAILY-2026-07-08 (date is the ID)
  folder        : relative directory where records are archived. experiment/daily use dynamic {year}/{date} subdirs.
  container     : "dir"  = one record is a folder (card.md + attachments); used for resource types;
                  "file" = one record is a single .md file.
  template      : name of templates/<template>.md.
  label         : display label (used only in docs/dashboards).
  is_resource   : whether this is a reusable resource (goes under lims/, appears in the lims.csv grouping).
  required      : required frontmatter fields (checked by validate).
  who_field     : which field records "who did it" (resource=created_by, experiment=operator);
                  validate uses it for required-field checks, dashboard uses it for display.
  status_field  : status field name (None if absent).
  allowed_status: controlled status vocabulary (empty = no restriction; validate only warns when non-empty).
  table_cols    : columns to extract into this type's dedicated CSV (index/<table>.csv).
  table         : dedicated CSV filename (without .csv). **Explicitly named to avoid plural-spelling bugs.**
"""
import os, csv

# tools/ lives at the repo root, so ROOT = tools/'s parent = repo root.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Top-level directories that hold no records — walkers must skip them.
# Substring match against the walked path (kept legacy pattern from earlier tools).
EXCLUDE_DIRS = (".git", "/index", "/templates", "/tools", "/wiki",
                "/raw", "/docs", "/references", "/inbox", "/node_modules")

def is_excluded(dp: str) -> bool:
    """True if a walked directory path should be skipped for record discovery."""
    return any(s in dp for s in EXCLUDE_DIRS)

# —— Schema version — bump when TYPES/prefixes change. Used by docs & tests to detect drift. ——
SCHEMA_VERSION = "5.0"  # Phase 5: eln/lims folder split (activities under eln/, inventory under lims/)

# —— Literature relation vocabulary (Phase 6) — how a paper connects to your research. ——
LIT_RELATIONS = {
    "supports",       # backs a hypothesis, method, or claim
    "contradicts",    # against a hypothesis or reported finding
    "method-from",    # paper is the source of a method/protocol used
    "background",     # general context / prior art
    "motivates",      # inspired a project or experiment
    "replicates",     # replicates or reproduces prior work
    "safety",         # safety, biosafety, or ethics reference
}

# —— Forward relation fields: "what I used / what I produced" on a record ——
FORWARD_REF_FIELDS = (
    "used_resources", "produced_resources", "produced_datasets", "derived_from",
    "protocols", "pipeline", "scripts", "produced_in", "instrument",
    "related", "related_experiments", "related_ideas", "inputs", "outputs",
    "experiments", "members",
)

# —— Backlink derivation rules: experiments declare forward links, and produced_in on the resource side is auto-filled from these ——
#    (src_field on source record) --> backfill source.id into the (dst_field) of the target record
BACKLINK_RULES = [
    ("produced_resources", "produced_in"),
    ("produced_datasets",  "produced_in"),
]

_R = "lims"   # inventory root: physical + biological + digital resources
_E = "eln"    # activity root: experiments, notes, ideas, projects, protocols, ...
TYPES = {
 # ---------------- LIMS resource types (container=dir, under lims/) ----------------
 "plasmid":   {"prefix":"PLA","id_style":"seq4","folder":f"{_R}/plasmids","container":"dir",
               "template":"plasmid","label":"plasmid","is_resource":True,
               "required":["id","type","name","created","created_by","backbone"],
               "who_field":"created_by","status_field":"status",
               "allowed_status":["available","depleted","archived"],
               "table":"plasmids",
               "table_cols":["backbone","resistance","insert","derived_from","produced_in","location","tags"]},
 "oligo":     {"prefix":"OLI","id_style":"seq4","folder":f"{_R}/oligos","container":"dir",
               "template":"oligo","label":"oligo","is_resource":True,
               "required":["id","type","name","created","created_by"],
               "who_field":"created_by","status_field":"status","allowed_status":["available","depleted","archived"],
               "table":"oligos","table_cols":["sequence","length","tm","purpose","location","tags"]},
 "dna":       {"prefix":"DNA","id_style":"seq4","folder":f"{_R}/dna","container":"dir",
               "template":"dna","label":"DNA sequence","is_resource":True,
               "required":["id","type","name","created","created_by"],
               "who_field":"created_by","status_field":"status","allowed_status":["available","depleted","archived"],
               "table":"dna","table_cols":["length","source","sequence_file","derived_from","location","tags"]},
 "reagent":   {"prefix":"RGT","id_style":"seq4","folder":f"{_R}/reagents","container":"dir",
               "template":"reagent","label":"reagent","is_resource":True,
               "required":["id","type","name","created","created_by"],
               "who_field":"created_by","status_field":"status","allowed_status":["available","depleted","archived","expired"],
               "table":"reagents","table_cols":["vendor","catalog","lot","expiry","conc","location","tags"]},
 "antibody":  {"prefix":"AB","id_style":"seq4","folder":f"{_R}/antibodies","container":"dir",
               "template":"antibody","label":"antibody","is_resource":True,
               "required":["id","type","name","created","created_by"],
               "who_field":"created_by","status_field":"status","allowed_status":["available","depleted","archived"],
               "table":"antibodies","table_cols":["target","host","clonality","vendor","catalog","applications","location"]},
 "sample":    {"prefix":"SMP","id_style":"year-seq4","folder":f"{_R}/samples","container":"dir",
               "template":"sample","label":"sample","is_resource":True,
               "required":["id","type","name","created","created_by","sample_type"],
               "who_field":"created_by","status_field":"status","allowed_status":["available","consumed","archived"],
               "table":"samples","table_cols":["sample_type","organism","derived_from","produced_in","location","tags"]},
 "mouse":     {"prefix":"MUS","id_style":"seq4","folder":f"{_R}/mice","container":"dir",
               "template":"mouse","label":"mouse","is_resource":True,
               "required":["id","type","name","created","created_by"],
               "who_field":"created_by","status_field":"status","allowed_status":["available","sacrificed","archived"],
               "table":"mice","table_cols":["strain","sex","genotype","cage","dob","status"]},
 "cell-line": {"prefix":"CL","id_style":"seq4","folder":f"{_R}/cell-lines","container":"dir",
               "template":"cell-line","label":"cell line","is_resource":True,
               "required":["id","type","name","created","created_by"],
               "who_field":"created_by","status_field":"status","allowed_status":["available","frozen","contaminated","archived"],
               "table":"cell_lines","table_cols":["organism","tissue","parental","mycoplasma","passage","location"]},
 "instrument":{"prefix":"INS","id_style":"seq4","folder":f"{_R}/instruments","container":"dir",
               "template":"instrument","label":"instrument","is_resource":True,
               "required":["id","type","name","created","created_by"],
               "who_field":"created_by","status_field":"status","allowed_status":["available","maintenance","retired"],
               "table":"instruments","table_cols":["vendor","model","location","booking","sop"]},
 "virus":     {"prefix":"VIR","id_style":"year-seq4","folder":f"{_R}/viruses","container":"dir",
               "template":"virus","label":"virus","is_resource":True,
               "required":["id","type","name","created","created_by"],
               "who_field":"created_by","status_field":"status","allowed_status":["available","depleted","archived"],
               "table":"viruses","table_cols":["virus_type","titer","transgene","derived_from","produced_in","biosafety","location"]},
 "dataset":   {"prefix":"DAT","id_style":"year-seq4","folder":f"{_R}/datasets","container":"dir",
               "template":"dataset","label":"dataset","is_resource":True,
               "required":["id","type","name","created","data_kind"],
               "who_field":"created_by","status_field":None,"allowed_status":[],
               "table":"datasets","table_cols":["data_kind","instrument","produced_in","n_files","total_size","manifest"]},
 "chemical":  {"prefix":"CHM","id_style":"seq4","folder":f"{_R}/chemicals","container":"dir",
               "template":"chemical","label":"chemical / drug / inhibitor","is_resource":True,
               "required":["id","type","name","created","created_by"],
               "who_field":"created_by","status_field":"status","allowed_status":["available","depleted","archived","expired"],
               "table":"chemicals","table_cols":["cas","smiles","target","vendor","catalog","lot","stock_conc","solvent","location","tags"]},
 "recipe":    {"prefix":"RCP","id_style":"seq4","folder":f"{_R}/recipes","container":"dir",
               "template":"recipe","label":"recipe (medium / buffer / solution)","is_resource":True,
               "required":["id","type","name","created","created_by"],
               "who_field":"created_by","status_field":"status","allowed_status":["active","deprecated","archived"],
               "table":"recipes","table_cols":["category","ph","sterilization","shelf_life","components","tags"]},
 "strain":    {"prefix":"STR","id_style":"seq4","folder":f"{_R}/strains","container":"dir",
               "template":"strain","label":"strain / competent cells","is_resource":True,
               "required":["id","type","name","created","created_by"],
               "who_field":"created_by","status_field":"status","allowed_status":["available","depleted","archived"],
               "table":"strains","table_cols":["organism","genotype","competent_type","transformation_efficiency","vendor","catalog","location","tags"]},
 "kit":       {"prefix":"KIT","id_style":"seq4","folder":f"{_R}/kits","container":"dir",
               "template":"kit","label":"commercial kit","is_resource":True,
               "required":["id","type","name","created","created_by"],
               "who_field":"created_by","status_field":"status","allowed_status":["available","depleted","archived","expired"],
               "table":"kits","table_cols":["vendor","catalog","lot","expiry","reactions_remaining","related_protocol","location","tags"]},
 "person":    {"prefix":"PER","id_style":"seq4","folder":f"{_R}/persons","container":"dir",
               "template":"person","label":"person","is_resource":True,
               "required":["id","type","name","created","created_by","role"],
               "who_field":"created_by","status_field":"status","allowed_status":["active","alumni","external"],
               "table":"persons","table_cols":["role","email","orcid","affiliation","tags"]},

 # ---------------- Process / knowledge types (container=file) ----------------
 "protocol":  {"prefix":"SOP","id_style":"seq4","folder":f"{_E}/protocols","container":"file",
               "template":"protocol","label":"SOP (protocol)","is_resource":False,
               "required":["id","type","name","created","created_by"],
               "who_field":"created_by","status_field":None,"allowed_status":[],
               "table":"protocols","table_cols":["version","category","est_time","tags"]},
 "pipeline":  {"prefix":"PIPE","id_style":"seq4","folder":f"{_E}/pipelines","container":"file",
               "template":"pipeline","label":"pipeline (analysis workflow)","is_resource":False,
               "required":["id","type","name","created","created_by"],
               "who_field":"created_by","status_field":None,"allowed_status":[],
               "table":"pipelines","table_cols":["version","language","env","entrypoint","tags"]},
 "script":    {"prefix":"SCR","id_style":"seq4","folder":f"{_E}/scripts","container":"file",
               "template":"script","label":"script","is_resource":False,
               "required":["id","type","name","created","created_by"],
               "who_field":"created_by","status_field":None,"allowed_status":[],
               "table":"scripts","table_cols":["language","entrypoint","purpose","tags"]},
 "skill":     {"prefix":"SKL","id_style":"seq4","folder":f"{_E}/skills","container":"file",
               "template":"skill","label":"AI skill","is_resource":False,
               "required":["id","type","name","created","created_by"],
               "who_field":"created_by","status_field":None,"allowed_status":[],
               "table":"skills","table_cols":["when_to_use","inputs","outputs","tags"]},
 "literature":{"prefix":"LIT","id_style":"seq4","folder":f"{_E}/literature","container":"file",
               "template":"literature","label":"literature","is_resource":False,
               "required":["id","type","title","doi","paper_type","created","created_by"],
               "who_field":"created_by","status_field":"status","allowed_status":["to-read","reading","read"],
               "table":"literature","table_cols":["title","authors","year","journal","doi","paper_type","status","wiki_link"]},
 "idea":      {"prefix":"IDEA","id_style":"seq4","folder":f"{_E}/ideas","container":"file",
               "template":"idea","label":"idea","is_resource":False,
               "required":["id","type","title","created","created_by"],
               "who_field":"created_by","status_field":"status","allowed_status":["open","testing","parked","done"],
               "table":"ideas","table_cols":["title","status","related","tags"]},
 "project":   {"prefix":"PRJ","id_style":"seq4","folder":f"{_E}/projects","container":"dir",
               "template":"project","label":"project","is_resource":False,
               "required":["id","type","name","created","created_by"],
               "who_field":"created_by","status_field":"status","allowed_status":["active","paused","done","dropped"],
               "table":"projects","table_cols":["lead","status","aims","members","tags"]},

 # ---------------- Timeline types (date-based ID, container=file) ----------------
 "experiment":{"prefix":"EXP","id_style":"date-nn","folder":f"{_E}/experiments","container":"file",
               "template":"experiment-wetlab","label":"experiment","is_resource":False,
               "required":["id","type","date","operator","title"],
               "who_field":"operator","status_field":"status","allowed_status":["planned","in-progress","complete","failed"],
               "table":"experiments","table_cols":["mode","operator","status","project","tags"]},
 "daily-summary":{"prefix":"DAILY","id_style":"date","folder":f"{_E}/experiments","container":"file",
               "template":"daily-summary","label":"daily summary","is_resource":False,
               "required":["id","type","date"],
               "who_field":"operator","status_field":None,"allowed_status":[],
               "table":None,"table_cols":[]},
 "meeting":   {"prefix":"MTG","id_style":"date","folder":f"{_E}/meetings","container":"file",
               "template":"meeting","label":"meeting","is_resource":False,
               "required":["id","type","date","title"],
               "who_field":None,"status_field":None,"allowed_status":[],
               "table":"meetings","table_cols":["title","attendees","related","tags"]},
}

# Allow new.py to be called with aliases (template name -> type name)
TEMPLATE_ALIAS = {
    "experiment-wetlab": "experiment",
    "experiment-drylab": "experiment",
}

# ---- Convenience queries ----
def by_prefix(prefix):
    for t, spec in TYPES.items():
        if spec["prefix"] == prefix:
            return t, spec
    return None, None

def resource_types():
    return [t for t, s in TYPES.items() if s.get("is_resource")]

def all_prefixes():
    return {s["prefix"] for s in TYPES.values()}

def id_regex(spec):
    """Match regex for a type's IDs (used to detect IDs of this type from text)."""
    import re
    p = re.escape(spec["prefix"])
    style = spec["id_style"]
    if style == "seq4":       return rf"{p}-(\d+)"
    if style == "year-seq4":  return rf"{p}-\d{{4}}-(\d+)"
    if style == "date-nn":    return rf"{p}-\d{{4}}-\d{{2}}-\d{{2}}-(\d+)"
    if style == "date":       return rf"{p}-\d{{4}}-\d{{2}}-\d{{2}}"
    return rf"{p}-(\d+)"

def prefix_of_id(rid):
    """Infer which prefix a specific ID belongs to (longest match, so AB does not collide with ABX)."""
    best = None
    for pfx in all_prefixes():
        if rid.startswith(pfx + "-"):
            if best is None or len(pfx) > len(best):
                best = pfx
    return best

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "table":
        # Print a markdown ID table (can be pasted into conventions.md)
        print("| Category | type | Prefix | ID style | Folder |")
        print("|---|---|---|---|---|")
        for t, s in TYPES.items():
            print(f"| {s['label']} | {t} | {s['prefix']} | {s['id_style']} | {s['folder']} |")
    else:
        print(f"registry: {len(TYPES)} types, prefixes: {', '.join(sorted(all_prefixes()))}")
