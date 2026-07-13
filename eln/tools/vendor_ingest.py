#!/usr/bin/env python3
"""Recognize common sequencing vendor delivery directory structures, recursively collect fastq,
and verify with vendor-supplied MD5 files.
Supported: Novogene / BGI / generic (recursive search for *.fq.gz|*.fastq.gz + MD5.txt / *.md5 / MD5.txt).
Dependency: standard library only.

Usage:
  python tools/vendor_ingest.py inbox/X22001 --exp EXP-2026-07-09-01 --instrument INS-0005 [--vendor auto]

It does: (1) auto-detect vendor layout, recursively find all fastq (no matter how deep);
(2) find the delivery's own MD5 manifest, recompute md5 for each file and compare, report OK/mismatch/missing;
(3) generate a manifest with relative path + md5 + verified status; (4) create DAT- card + today's
_daylog.md entry. sample_id/condition remain empty to be filled in.
"""
import os, sys, re, csv, hashlib, argparse, datetime, glob
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def md5(p, buf=1<<20):
    h=hashlib.md5()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(buf),b""): h.update(c)
    return h.hexdigest()

FQ=(".fq.gz",".fastq.gz",".fq",".fastq")

def find_fastqs(root):
    out=[]
    for dp,_,fs in os.walk(root):
        for fn in fs:
            if fn.endswith(FQ): out.append(os.path.join(dp,fn))
    return sorted(out)

def find_md5_manifests(root):
    """Collect all md5 manifests in the delivery, parse into {basename: md5}.
    Handles both 'MD5  file' and 'file  MD5' column orders."""
    table={}
    for dp,_,fs in os.walk(root):
        for fn in fs:
            if fn.lower() in ("md5.txt","md5sum.txt") or fn.lower().endswith(".md5"):
                for line in open(os.path.join(dp,fn),errors="ignore"):
                    parts=line.split()
                    if len(parts)>=2:
                        a,b=parts[0],parts[-1]
                        h,name=(a,b) if re.fullmatch(r"[0-9a-fA-F]{32}",a) else (b,a)
                        if re.fullmatch(r"[0-9a-fA-F]{32}",h):
                            table[os.path.basename(name)]=h.lower()
    return table

def detect_vendor(root):
    names=" ".join(os.listdir(root)).lower()
    if "novogene" in names or glob.glob(os.path.join(root,"**/*.md5"),recursive=True) and glob.glob(os.path.join(root,"**/raw_data"),recursive=True):
        return "novogene"
    if any(os.path.isdir(os.path.join(root,d)) and d.lower().startswith("clean") for d in os.listdir(root)):
        return "bgi"
    return "generic"

def next_dat(year):
    n=0
    for dp,_,fs in os.walk(ROOT):
        for fn in fs:
            if fn.endswith(".md"):
                for m in re.findall(r"DAT-\d{4}-(\d+)", open(os.path.join(dp,fn),errors="ignore").read()):
                    n=max(n,int(m))
    return f"DAT-{year}-{n+1:04d}"

def human(n):
    for u in ["B","KB","MB","GB","TB"]:
        if n<1024: return f"{n:.1f} {u}"
        n/=1024
    return f"{n:.1f} PB"

ap=argparse.ArgumentParser()
ap.add_argument("folder"); ap.add_argument("--exp", default=""); ap.add_argument("--instrument", default="")
ap.add_argument("--vendor", default="auto"); ap.add_argument("--name", default="")
ap.add_argument("--no-verify", action="store_true", help="skip md5 validation (emit skeleton first)")
a=ap.parse_args()

vendor = detect_vendor(a.folder) if a.vendor=="auto" else a.vendor
fqs = find_fastqs(a.folder)
md5table = {} if a.no_verify else find_md5_manifests(a.folder)
print(f"vendor layout: {vendor} | found {len(fqs)} fastq | md5 manifest entries: {len(md5table)}")

rows=[]; ok=miss=bad=0; total=0
for p in fqs:
    base=os.path.basename(p); size=os.path.getsize(p); total+=size
    status="not-checked"
    if not a.no_verify:
        want=md5table.get(base)
        if want is None: status="no-md5-listed"; miss+=1
        else:
            got=md5(p)
            if got==want: status="verified"; ok+=1
            else: status="MISMATCH"; bad+=1
    rows.append({"filename":base,"sample_id":"","condition":"","replicate":"",
                 "rel_path":os.path.relpath(p,a.folder),"path":os.path.abspath(p),
                 "md5":md5table.get(base,""),"md5_status":status,"size_bytes":size})

if not a.no_verify:
    print(f"MD5 validation: verified={ok}  not-listed={miss}  mismatch={bad}")
    if bad: print("⚠️ Some files have md5 mismatch, delivery may be corrupted / transfer error, please re-download!")

today=datetime.date.today().isoformat(); year=today[:4]; dat=next_dat(year)
slug=(a.name or f"{vendor}-delivery").lower(); slug=re.sub(r"[^a-z0-9]+","-",slug).strip("-")[:40]
dat_dir=os.path.join(ROOT,"resources","datasets",f"{dat}-{slug}"); os.makedirs(dat_dir,exist_ok=True)
cols=["filename","sample_id","condition","replicate","rel_path","path","md5","md5_status","size_bytes"]
with open(os.path.join(dat_dir,"manifest.csv"),"w",newline="") as f:
    wr=csv.DictWriter(f,fieldnames=cols); wr.writeheader(); wr.writerows(rows)
with open(os.path.join(dat_dir,"card.md"),"w") as f:
    f.write(f"""---
id: {dat}
type: dataset
name: {a.name or slug}
created: {today}
created_by:
instrument: {a.instrument}
data_kind: fastq
vendor: {vendor}
produced_in: {a.exp}
storage:
  location: {os.path.abspath(a.folder)}
  in_git: false
n_files: {len(rows)}
total_size: {human(total)}
md5_verified: {ok}/{len(rows)}
manifest: manifest.csv
derived_from: []
tags: []
---
## Description
{vendor} sequencing delivery, auto-registered by vendor_ingest.py ({today}).
## MD5 Validation
verified={ok}  not-listed={miss}  mismatch={bad}{"  ⚠️ needs re-download" if bad else ""}
## TODO
- [ ] fill sample_id / condition in manifest.csv
- [ ] add {dat} to produced_datasets of experiment {a.exp or 'EXP-...'}
""")
inbox=os.path.join(ROOT,"experiments",year,today,"_daylog.md"); os.makedirs(os.path.dirname(inbox),exist_ok=True)
new=not os.path.exists(inbox)
with open(inbox,"a") as f:
    if new: f.write(f"# {today} Inbox (what arrived today)\n\n")
    rel=os.path.relpath(os.path.join(dat_dir,"card.md"),os.path.dirname(inbox))
    flag=" ⚠️MD5 mismatch" if bad else (f" ✓{ok} verified" if ok else "")
    f.write(f"- **{dat}** {a.name or slug} — {len(rows)} fastq, {human(total)}, {vendor}{flag} → [{dat}]({rel})\n")
print(f"✅ Registered {dat} ({len(rows)} files, {human(total)}) -> {os.path.relpath(dat_dir,ROOT)}/")
