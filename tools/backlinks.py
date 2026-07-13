#!/usr/bin/env python3
"""Automatically backfill reverse links so you **only need to write forward links once, in the experiment**.

Rule (see registry.BACKLINK_RULES): if an experiment lists resource X in its produced_resources / produced_datasets,
write the experiment's ID into X's produced_in field.

Usage:
  python tools/backlinks.py            # dry-run, only report what would change
  python tools/backlinks.py --write    # actually write back to resource/dataset cards (idempotent)

Idempotent: if produced_in is already correct, skip; if empty, fill it in; if there is a different existing value,
**warn only, do not overwrite** (leave the decision to you).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import fm
import registry as R

ROOT = R.ROOT
WRITE = "--write" in sys.argv

# 1) Collect all record paths in the library
paths = {}
for dp, _, fs in os.walk(ROOT):
    if any(s in dp for s in (".git", "/index", "/templates", "/tools", "/wiki", "/raw", "/docs", "/references", "/inbox")): continue
    for fn in fs:
        if not fn.endswith(".md"): continue
        p = os.path.join(dp, fn); meta, _ = fm.parse(p)
        if meta.get("id") and "XXXX" not in meta["id"]: paths[meta["id"]] = p

# 2) Compute the expected produced_in for each resource from experiments
want = {}   # resource_id -> exp_id
for rid, p in paths.items():
    meta, _ = fm.parse(p)
    for src_field, dst_field in R.BACKLINK_RULES:
        for tgt in (meta.get(src_field) or []):
            if tgt in paths:
                want.setdefault(tgt, rid)

changed, conflicts, skipped = [], [], 0
for res_id, exp_id in want.items():
    p = paths[res_id]
    with open(p, encoding="utf-8") as f:
        txt = f.read()
    cur = fm.get_field(txt, "produced_in")
    # Normalize: empty list / empty str / None all count as unfilled
    if cur in (None, "", []):
        cur = None
    if cur == exp_id: skipped += 1; continue
    if cur is not None:
        conflicts.append(f"{res_id}: produced_in is already '{cur}', but experiment declares '{exp_id}' -> please review manually")
        continue
    new = fm.set_field(txt, "produced_in", exp_id)
    changed.append((res_id, exp_id))
    if WRITE:
        with open(p, "w", encoding="utf-8") as f:
            f.write(new)

for c in conflicts: print("⚠️ ", c)
for res_id, exp_id in changed:
    print(("✅ wrote" if WRITE else "would write"), f"{res_id}.produced_in = {exp_id}")
print(f"\n{'Wrote back' if WRITE else 'Dry-run'}: added {len(changed)}, conflicts {len(conflicts)}, already-consistent {skipped}")
if not WRITE and changed: print("Add --write to actually persist, then run index.py + validate.py.")
