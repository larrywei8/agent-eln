#!/usr/bin/env python3
"""Verify that every file in a manifest still exists and its sha256 has not changed (data integrity check).
Usage: python tools/verify_data.py lims/datasets/DAT-2026-0001-*/manifest.csv"""
import sys, csv, hashlib, os
def sha256(p, buf=1<<20):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(buf),b""): h.update(c)
    return h.hexdigest()
mf=sys.argv[1]; ok=miss=bad=0
for r in csv.DictReader(open(mf)):
    p=r.get("path",""); want=r.get("sha256","")
    if not p or not os.path.exists(p): print("missing:",r["filename"]); miss+=1; continue
    if want and want not in ("<sha>","") and sha256(p)!=want: print("hash mismatch:",r["filename"]); bad+=1
    else: ok+=1
print(f"OK={ok} missing={miss} corrupted={bad}")
sys.exit(1 if (miss or bad) else 0)
