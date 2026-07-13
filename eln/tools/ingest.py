#!/usr/bin/env python3
"""Break down a whole instrument/vendor delivery folder and register it, without manual copy-paste.

Usage:
  python tools/ingest.py inbox/2026-07-09_novogene_delivery --kind fastq --exp EXP-2026-07-09-01

It does four things:
  1) Allocate a DAT- ID and create a dataset card under resources/datasets/;
  2) Scan the folder, compute sha256/size, generate a manifest.csv skeleton (sample_id/condition left blank);
  3) Keep large files in place (by default no move, only register path); small files (e.g. gel) can be --copy'd into the library;
  4) Append a "what arrived today" entry to that day's experiments/<date>/_daylog.md, linked to the DAT.

Result: files are physically archived by type (resource library), while "what came in today" is tracked
by _daylog.md plus experiment-entry links.
"""
import os, sys, csv, hashlib, argparse, datetime, re, shutil
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def sha256(p, buf=1<<20):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(buf),b""): h.update(c)
    return h.hexdigest()

def next_dat(year):
    n=0
    for dp,_,fs in os.walk(ROOT):
        for fn in fs:
            if fn.endswith(".md"):
                for m in re.findall(r"DAT-\d{4}-(\d+)", open(os.path.join(dp,fn),errors="ignore").read()):
                    n=max(n,int(m))
    return f"DAT-{year}-{n+1:04d}"

ap=argparse.ArgumentParser()
ap.add_argument("folder"); ap.add_argument("--kind", default="unknown")
ap.add_argument("--exp", default=""); ap.add_argument("--instrument", default="")
ap.add_argument("--name", default=""); ap.add_argument("--copy", action="store_true",
                help="copy files into the DAT folder (suitable for small files like gel); default only registers path")
ap.add_argument("--no-hash", action="store_true")
a=ap.parse_args()

today=datetime.date.today().isoformat(); year=today[:4]
dat=next_dat(year)
slug=(a.name or os.path.basename(a.folder.rstrip("/"))).lower()
slug=re.sub(r"[^a-z0-9]+","-",slug).strip("-")[:40]
dat_dir=os.path.join(ROOT,"resources","datasets",f"{dat}-{slug}")
os.makedirs(dat_dir, exist_ok=True)

# scan + manifest
files=[f for f in sorted(os.listdir(a.folder)) if os.path.isfile(os.path.join(a.folder,f))]
N=len(files); rows=[]; total=0; hashed_bytes=0
def _mb(n): return f"{n/1024/1024:.1f} MB"
if not a.no_hash and N:
    print(f"[ingest] hashing {N} files from {a.folder} ...", file=sys.stderr, flush=True)
for i,fn in enumerate(files,1):
    src=os.path.join(a.folder,fn); size=os.path.getsize(src); total+=size
    if a.copy:
        shutil.copy2(src, os.path.join(dat_dir,fn)); path=os.path.join(dat_dir,fn)
    else:
        path=os.path.abspath(src)
    if a.no_hash:
        digest=""
    else:
        print(f"[ingest] [{i}/{N}] {fn} ({_mb(size)}) ...", file=sys.stderr, flush=True)
        digest=sha256(src); hashed_bytes+=size
        print(f"[ingest] [{i}/{N}] done — cumulative {_mb(hashed_bytes)}", file=sys.stderr, flush=True)
    rows.append({"filename":fn,"sample_id":"","condition":"","replicate":"",
                 "path":path,"sha256":digest,"size_bytes":size})
cols=["filename","sample_id","condition","replicate","path","sha256","size_bytes"]
with open(os.path.join(dat_dir,"manifest.csv"),"w",newline="") as f:
    wr=csv.DictWriter(f,fieldnames=cols); wr.writeheader(); wr.writerows(rows)

def human(n):
    for u in ["B","KB","MB","GB","TB"]:
        if n<1024: return f"{n:.1f} {u}"
        n/=1024
    return f"{n:.1f} PB"

# dataset card
with open(os.path.join(dat_dir,"card.md"),"w") as f:
    f.write(f"""---
id: {dat}
type: dataset
name: {a.name or slug}
created: {today}
created_by:
instrument: {a.instrument}
data_kind: {a.kind}
produced_in: {a.exp}
storage:
  location: {"./" if a.copy else os.path.abspath(a.folder)}
  in_git: {str(a.copy).lower()}
n_files: {len(rows)}
total_size: {human(total)}
manifest: manifest.csv
derived_from: []
tags: []
---
## Description
Auto-registered by tools/ingest.py ({today}). Original source: {os.path.abspath(a.folder)}
## Manifest notes
One file per row; please fill in the sample_id / condition columns.
## TODO
- [ ] fill sample_id / condition in manifest.csv
- [ ] add {dat} to produced_datasets of experiment {a.exp or 'EXP-...'}
""")

# append to today's inbox log
inbox_md=os.path.join(ROOT,"experiments",year,today,"_daylog.md")
os.makedirs(os.path.dirname(inbox_md), exist_ok=True)
new = not os.path.exists(inbox_md)
with open(inbox_md,"a") as f:
    if new: f.write(f"# {today} Inbox (what arrived today)\n\n")
    rel=os.path.relpath(os.path.join(dat_dir,"card.md"), os.path.dirname(inbox_md))
    f.write(f"- **{dat}** {a.name or slug} — {len(rows)} files, {human(total)}, kind={a.kind} "
            f"-> [{dat}]({rel})  (exp: {a.exp or 'TODO'})\n")

print(f"✅ Registered {dat}: {len(rows)} files, {human(total)}")
print(f"   dataset card: {os.path.relpath(dat_dir,ROOT)}/card.md")
print(f"   today's inbox: {os.path.relpath(inbox_md,ROOT)}")
print(f"   next: fill sample_id/condition in manifest; run index.py + validate.py")
