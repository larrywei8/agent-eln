#!/usr/bin/env python3
"""Validate whole-library consistency:
  1) IDs are unique.
  2) Every ID referenced in frontmatter actually exists.
  3) Required fields present (per registry.py 'required' for each type).
  4) [warn] status values within the controlled vocabulary.
  5) [warn] backlink consistency: the experiment that a resource's produced_in points to
           should declare this resource in produced_resources/produced_datasets
           (the reverse is filled in automatically by backlinks.py).
  6) Compound-ID structural integrity (per hierarchy.md):
       - anchor record must exist
       - direct parent must exist
       - frontmatter derived_from must contain the direct parent
       - depth must be <= 2
     [warn] segment CODE is registered in vocab.md
  7) [warn] sample_type / source_tissue / organism / preservation values are in
     the vocab.md controlled vocabulary (only when vocab.md defines the set).

Errors (1-3, 6-structure) return a non-zero exit code and block commit;
warnings only report, do not block.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from fm import parse
import registry as R
import hierarchy as H
import vocab as V

ROOT = R.ROOT
ids, refs, records, errors, warnings = {}, [], {}, [], []
dois = {}  # doi -> first record id/path — used to enforce LIT DOI uniqueness
REF_FIELDS = R.FORWARD_REF_FIELDS

for dp, _, fs in os.walk(ROOT):
    if any(s in dp for s in (".git", "/index", "/templates", "/tools")): continue
    for fn in fs:
        if not fn.endswith(".md"): continue
        p = os.path.join(dp, fn); meta, _ = parse(p); rel = os.path.relpath(p, ROOT)
        if "id" not in meta: continue
        rid = meta["id"]
        if any(x in rid for x in ("XXXX", "YYYY", "YYYY-MM-DD", "-NN")): continue  # template
        if rid in ids: errors.append(f"Duplicate ID {rid}: {rel} and {ids[rid]}")
        ids[rid] = rel; records[rid] = meta

        t = meta.get("type"); spec = R.TYPES.get(t)
        if not spec:
            warnings.append(f"{rid}: unknown type='{t}' (not in registry)  ({rel})");
        else:
            for f in spec["required"]:
                v = meta.get(f)
                if v in (None, "", []): errors.append(f"{rid}: missing required field '{f}'  ({rel})")
            sf = spec.get("status_field"); allowed = spec.get("allowed_status") or []
            if sf and allowed:
                sv = meta.get(sf)
                if sv and sv not in allowed:
                    warnings.append(f"{rid}: {sf}='{sv}' not in controlled vocabulary {allowed}  ({rel})")

        # Phase 6: LIT DOI uniqueness. Bare DOIs only — health.py already warns on URL prefixes.
        if t == "literature":
            doi = (meta.get("doi") or "").strip().lower()
            if doi:
                if doi in dois:
                    errors.append(f"{rid}: duplicate DOI '{doi}' — already used by {dois[doi][0]}  "
                                  f"({rel} vs {dois[doi][1]})")
                else:
                    dois[doi] = (rid, rel)
            # Phase 6: relation vocabulary — warn only, don't block.
            rel_v = meta.get("relation")
            if rel_v and rel_v not in R.LIT_RELATIONS:
                warnings.append(f"{rid}: relation='{rel_v}' not in vocabulary {sorted(R.LIT_RELATIONS)}  ({rel})")

        # Phase 5: reproducibility gate — completed experiments must record
        # what was actually run. Wetlab needs a protocol_version snapshot;
        # drylab needs the code commit + env lockfile that produced its results.
        if t == "experiment" and (meta.get("status") or "").strip() in ("complete", "finalized"):
            mode = (meta.get("mode") or "").strip()
            if mode == "wetlab":
                if not (meta.get("protocol_version") or "").strip():
                    warnings.append(f"{rid}: complete wetlab experiment missing protocol_version  ({rel})")
            elif mode == "drylab":
                if not (meta.get("code_commit") or "").strip():
                    warnings.append(f"{rid}: complete drylab experiment missing code_commit  ({rel})")
                if not (meta.get("env_lockfile") or "").strip():
                    warnings.append(f"{rid}: complete drylab experiment missing env_lockfile  ({rel})")

        # 7) Controlled-vocab checks (only warn if vocab.md defined the set).
        if V.SAMPLE_TYPES and meta.get("sample_type"):
            if meta["sample_type"] not in V.SAMPLE_TYPES:
                warnings.append(f"{rid}: sample_type='{meta['sample_type']}' not in vocab.md  ({rel})")
        if V.SOURCE_TISSUES and meta.get("source_tissue"):
            if meta["source_tissue"] not in V.SOURCE_TISSUES:
                warnings.append(f"{rid}: source_tissue='{meta['source_tissue']}' not in vocab.md  ({rel})")
        if V.ORGANISMS and meta.get("organism"):
            if meta["organism"] not in V.ORGANISMS:
                warnings.append(f"{rid}: organism='{meta['organism']}' not in vocab.md  ({rel})")
        if V.PRESERVATIONS and meta.get("preservation"):
            if meta["preservation"] not in V.PRESERVATIONS:
                warnings.append(f"{rid}: preservation='{meta['preservation']}' not in vocab.md  ({rel})")

        for field in REF_FIELDS:
            v = meta.get(field)
            for tgt in ([v] if isinstance(v, str) else (v or [])):
                if isinstance(tgt, str) and R.prefix_of_id(tgt): refs.append((rid, field, tgt, rel))

# 2) reference existence
for src, field, tgt, rel in refs:
    if tgt not in ids:
        errors.append(f"{src}'s {field} references non-existent ID: {tgt}  ({rel})")

# 5) backlink consistency (warn)
for rid, meta in records.items():
    pin = meta.get("produced_in")
    pin = pin if isinstance(pin, str) else (pin[0] if pin else None)
    if pin and pin in records:
        exp = records[pin]
        declared = set((exp.get("produced_resources") or []) + (exp.get("produced_datasets") or []))
        if rid not in declared:
            warnings.append(f"{rid}.produced_in={pin} but {pin} does not declare {rid} in produced_resources/"
                            f"produced_datasets -> run `python tools/backlinks.py --write` to fill in")

# 6) Compound-ID structural integrity + segment-code registration.
for rid, meta in records.items():
    rel = ids[rid]
    parsed = H.parse(rid)
    if parsed is None:
        continue  # not a compound ID — skip
    depth = parsed["depth"]
    anchor = parsed["anchor"]
    parent = parsed["direct_parent"]

    if depth > 2:
        errors.append(f"{rid}: compound-ID depth {depth} exceeds cap of 2 (hierarchy.md)  ({rel})")

    if anchor not in ids:
        errors.append(f"{rid}: anchor record {anchor} does not exist  ({rel})")

    if parent not in ids:
        errors.append(f"{rid}: direct parent {parent} does not exist  ({rel})")

    # derived_from must contain the direct parent
    df = meta.get("derived_from")
    df_list = [df] if isinstance(df, str) else (df or [])
    if parent not in df_list:
        errors.append(f"{rid}: compound-ID ↔ derived_from mismatch — derived_from={df_list} "
                      f"does not contain direct parent {parent}  ({rel})")

    # Warn on unregistered segment codes.
    if V.SEGMENT_CODES:
        for seg in parsed["segments"]:
            if seg["code"] not in V.SEGMENT_CODES:
                warnings.append(f"{rid}: segment code '{seg['code']}' not registered in vocab.md  ({rel})")

if warnings:
    print("⚠️  Warnings:"); [print("  -", w) for w in warnings]
if errors:
    print("❌ Validation failed:"); [print("  -", e) for e in errors]; sys.exit(1)
print(f"✅ Validation passed: {len(ids)} records, {len(refs)} references all valid"
      + (f" ({len(warnings)} warnings)" if warnings else ""))
