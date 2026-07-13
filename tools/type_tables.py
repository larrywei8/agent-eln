#!/usr/bin/env python3
"""Emit a per-type CSV of type-specific fields (better than the generic records.csv for column-based filtering).
Both column definitions and filenames come from table_cols / table in registry.py (explicitly named, no plural-suffix guessing,
eliminating bugs like viruss.csv). Usage: python tools/type_tables.py
"""
import os, sys, csv
sys.path.insert(0, os.path.dirname(__file__))
from fm import parse
import registry as R

ROOT = R.ROOT
buckets = {t: [] for t, s in R.TYPES.items() if s.get("table")}
for dp, _, fs in os.walk(ROOT):
    if any(s in dp for s in (".git", "/index", "/templates", "/tools", "/wiki", "/raw", "/docs", "/references", "/inbox")): continue
    for fn in fs:
        if not fn.endswith(".md"): continue
        meta, _ = parse(os.path.join(dp, fn))
        t = meta.get("type"); rid = meta.get("id", "")
        if t in buckets and rid and not any(x in rid for x in ("XXXX", "YYYY", "-NN")):
            row = {"id": rid, "name": meta.get("name") or meta.get("title", "")}
            for c in R.TYPES[t]["table_cols"]:
                v = meta.get(c, "")
                row[c] = "; ".join(map(str, v)) if isinstance(v, list) else v
            buckets[t].append(row)

os.makedirs(os.path.join(ROOT, "index"), exist_ok=True)
made = []
for t, rows in buckets.items():
    if not rows: continue
    spec = R.TYPES[t]; cols = ["id", "name"] + spec["table_cols"]
    out = os.path.join(ROOT, "index", f"{spec['table']}.csv")
    with open(out, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=cols); wr.writeheader(); wr.writerows(rows)
    made.append(f"{spec['table']}.csv({len(rows)})")
print("Generated type tables:", ", ".join(made) if made else "(no data)")
