#!/usr/bin/env python3
"""Scan a data folder, compute sha256 + size for each file, generate a manifest.csv skeleton.
You only need to fill in the experimental columns like sample_id / condition afterwards.
Usage: python tools/make_manifest.py /data/store/DAT-2026-0001/ [--ext .fastq.gz,.fcs]
Output: manifest.csv in the folder (if it exists, writes manifest.new.csv instead, no overwrite)."""
import os, sys, csv, hashlib, argparse

def sha256(path, buf=1<<20):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(buf), b""): h.update(chunk)
    return h.hexdigest()

ap=argparse.ArgumentParser()
ap.add_argument("folder")
ap.add_argument("--ext", default="", help="comma-separated suffix filter, e.g. .fastq.gz,.fcs; empty = all")
ap.add_argument("--no-hash", action="store_true", help="skip sha256 (emit skeleton first for large folders)")
a=ap.parse_args()
exts=tuple(e.strip() for e in a.ext.split(",") if e.strip())
rows=[]
for fn in sorted(os.listdir(a.folder)):
    p=os.path.join(a.folder,fn)
    if not os.path.isfile(p): continue
    if exts and not fn.endswith(exts): continue
    rows.append({"filename":fn,
                 "sample_id":"",         # <- you fill
                 "condition":"",         # <- you fill (treatment/concentration/time...)
                 "replicate":"",
                 "path":os.path.abspath(p),
                 "sha256":"" if a.no_hash else sha256(p),
                 "size_bytes":os.path.getsize(p)})
out=os.path.join(a.folder,"manifest.csv")
if os.path.exists(out): out=os.path.join(a.folder,"manifest.new.csv")
cols=["filename","sample_id","condition","replicate","path","sha256","size_bytes"]
with open(out,"w",newline="") as f:
    wr=csv.DictWriter(f,fieldnames=cols); wr.writeheader(); wr.writerows(rows)
print(f"-> {out}  ({len(rows)} files)")
print("Next step: open in a spreadsheet, fill the sample_id / condition columns, then create the DAT- card.")
