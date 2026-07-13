#!/usr/bin/env python3
"""Rebuild index/: records.csv, grouped csvs, per-type csvs, graph.json, backlinks.csv.

Phase 1 enhancements (2026-07-11):
  * Incremental index: uses (mtime_ns, size) as fingerprint; unchanged files skip re-parse, only changed files are rescanned.
    Cache file index/.cache.json; changes to registry.py or a CACHE_VERSION bump trigger a full rebuild.
  * DuckDB query layer: also emits index/data.duckdb (optional dependency; skipped if not installed).
    The two extra columns who / created_date live only in DuckDB and do not change the CSV schema.
  * CSV / graph.json output is byte-for-byte identical to Phase 0 (guaranteed by golden-diff).

Usage:
  python tools/index.py            # incremental
  python tools/index.py --force    # ignore cache, full rebuild
  python tools/index.py --stats    # print parsed/cached/dropped statistics
"""
import os, csv, json, sys, glob, subprocess
sys.path.insert(0, os.path.dirname(__file__))
from fm import parse
import registry as R

ROOT = R.ROOT
IDX = os.path.join(ROOT, "index")
CACHE_PATH = os.path.join(IDX, ".cache.json")
DUCKDB_PATH = os.path.join(IDX, "data.duckdb")
CACHE_VERSION = 2

FORCE = "--force" in sys.argv
STATS = "--stats" in sys.argv

os.makedirs(IDX, exist_ok=True)

# ---- Cache loading --------------------------------------------------------------
def _load_cache():
    if FORCE or not os.path.exists(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH) as f:
            data = json.load(f)
    except Exception:
        return {}
    if data.get("version") != CACHE_VERSION:
        return {}
    reg_path = os.path.abspath(R.__file__)
    if data.get("registry_mtime") != os.path.getmtime(reg_path):
        return {}
    return data.get("entries", {})

cache = _load_cache()
parsed_n = cached_n = 0
new_entries = {}   # Full replacement on write-back; deleted files drop out naturally
records, edges = [], []

def _extract(meta, rel):
    """Extract record + edges + DuckDB extra fields from frontmatter. Returns (rec_or_None, edges, who, created_date, tags)."""
    rid = meta.get("id")
    if not rid or "type" not in meta:
        return None, [], None, None, None, None, None
    if any(x in rid for x in ("XXXX", "YYYY", "-NN")):
        return None, [], None, None, None, None, None
    rec = {"id": rid, "type": meta["type"],
           "name": meta.get("name") or meta.get("title", ""),
           "status": meta.get("status", ""),
           "project": meta.get("project", ""),
           "path": rel}
    e_list = []
    for field in R.FORWARD_REF_FIELDS:
        v = meta.get(field)
        for tgt in ([v] if isinstance(v, str) else (v or [])):
            if isinstance(tgt, str) and R.prefix_of_id(tgt):
                e_list.append({"src": rid, "dst": tgt, "rel": field})
    spec = R.TYPES.get(meta["type"], {})
    who_field = spec.get("who_field")
    who = meta.get(who_field) if who_field else None
    created_date = meta.get("created") or meta.get("date")
    tags = meta.get("tags") if isinstance(meta.get("tags"), list) else None
    doi = meta.get("doi") if isinstance(meta.get("doi"), str) else None
    paper_type = meta.get("paper_type") if isinstance(meta.get("paper_type"), str) else None
    return rec, e_list, who, created_date, tags, doi, paper_type

# ---- Walk (sorted walk for CSV row order stable across machines and runs) -------------------
for dirpath, dnames, files in os.walk(ROOT):
    dnames.sort()  # in-place, affects subsequent descent order
    if any(s in dirpath for s in (".git", "/index", "/templates", "/tools", "/wiki", "/raw", "/docs", "/references", "/inbox")):
        continue
    for fn in sorted(files):
        if not fn.endswith(".md"):
            continue
        p = os.path.join(dirpath, fn)
        rel = os.path.relpath(p, ROOT)
        try:
            st = os.stat(p)
        except OSError:
            continue
        mtime_ns, size = st.st_mtime_ns, st.st_size
        hit = cache.get(rel)
        if hit and hit.get("mtime_ns") == mtime_ns and hit.get("size") == size:
            new_entries[rel] = hit
            cached_n += 1
            rec = hit.get("record")
            if rec is not None:
                records.append(rec)
                edges.extend(hit.get("edges", []))
            continue
        meta, _ = parse(p)
        rec, e_list, who, created_date, tags, doi, paper_type = _extract(meta, rel)
        entry = {"mtime_ns": mtime_ns, "size": size,
                 "record": rec, "edges": e_list,
                 "who": who, "created_date": created_date, "tags": tags,
                 "doi": doi, "paper_type": paper_type}
        new_entries[rel] = entry
        parsed_n += 1
        if rec is not None:
            records.append(rec)
            edges.extend(e_list)

# ---- Backlinks: experiments declare forward links -> target resource's produced_in is auto-filled ------------
known = {r["id"] for r in records}
rev_rows = []
for e in list(edges):
    for src_field, dst_field in R.BACKLINK_RULES:
        if e["rel"] == src_field and e["dst"] in known:
            edges.append({"src": e["dst"], "dst": e["src"], "rel": f"{dst_field}(auto)"})
            rev_rows.append({"id": e["dst"], "backlink": dst_field, "value": e["src"]})

# ---- Clear old artifacts (leaves .cache.json / data.duckdb alone) -------------------------
for f in glob.glob(os.path.join(IDX, "*.csv")) + glob.glob(os.path.join(IDX, "*.json")):
    try:
        os.remove(f)
    except OSError as e:
        print(f"[warn] cannot delete stale file {os.path.basename(f)}: {e}")

# ---- Write CSV / graph.json (byte-for-byte equivalent to the old version) --------------------------------
def write_csv(name, rows, cols):
    with open(os.path.join(IDX, name), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=cols); wr.writeheader(); wr.writerows(rows)

RCOLS = ["id", "type", "name", "status", "project", "path"]
write_csv("records.csv", records, RCOLS)
groups = {"lims": [t for t in R.resource_types() if t != "dataset"],
          "datasets": ["dataset"], "experiments": ["experiment"]}
for group, types in groups.items():
    write_csv(f"{group}.csv", [r for r in records if r["type"] in types], RCOLS)
write_csv("backlinks.csv", rev_rows, ["id", "backlink", "value"])
with open(os.path.join(IDX, "graph.json"), "w") as f:
    json.dump({"nodes": records, "edges": edges}, f, indent=1, ensure_ascii=False)

# ---- Write cache (atomic replace) ------------------------------------------------------
_out = {"version": CACHE_VERSION,
        "registry_mtime": os.path.getmtime(os.path.abspath(R.__file__)),
        "entries": new_entries}
_tmp = CACHE_PATH + ".tmp"
with open(_tmp, "w") as f:
    json.dump(_out, f)
os.replace(_tmp, CACHE_PATH)

# ---- DuckDB (optional dependency) -----------------------------------------------------
try:
    import duckdb
    _HAS_DUCK = True
except ImportError:
    _HAS_DUCK = False

if _HAS_DUCK:
    if os.path.exists(DUCKDB_PATH):
        os.remove(DUCKDB_PATH)
    con = duckdb.connect(DUCKDB_PATH)
    con.execute("""CREATE TABLE records (
        id VARCHAR PRIMARY KEY, type VARCHAR, name VARCHAR,
        status VARCHAR, project VARCHAR, path VARCHAR,
        who VARCHAR, created_date VARCHAR, tags VARCHAR[],
        doi VARCHAR, paper_type VARCHAR
    )""")
    con.execute("CREATE TABLE edges (src VARCHAR, dst VARCHAR, rel VARCHAR)")
    con.execute("CREATE TABLE backlinks (id VARCHAR, backlink VARCHAR, value VARCHAR)")
    rec_rows = []
    for entry in new_entries.values():
        rec = entry.get("record")
        if not rec: continue
        rec_rows.append((rec["id"], rec["type"], rec["name"], rec["status"],
                         rec["project"], rec["path"],
                         entry.get("who"), entry.get("created_date"), entry.get("tags"),
                         entry.get("doi"), entry.get("paper_type")))
    if rec_rows:
        con.executemany("INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?)", rec_rows)
    edge_rows = [(e["src"], e["dst"], e["rel"]) for e in edges]
    if edge_rows:
        con.executemany("INSERT INTO edges VALUES (?,?,?)", edge_rows)
    bl_rows = [(r["id"], r["backlink"], r["value"]) for r in rev_rows]
    if bl_rows:
        con.executemany("INSERT INTO backlinks VALUES (?,?,?)", bl_rows)
    con.execute("CREATE INDEX edges_src ON edges(src)")
    con.execute("CREATE INDEX edges_dst ON edges(dst)")
    con.execute("CREATE INDEX records_doi ON records(doi)")
    con.close()

# ---- Per-type tables (using the existing script; independent of this one) ----------------------------------
subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "type_tables.py")])

if STATS:
    dropped = max(0, len(cache) - cached_n)
    duck_state = "duckdb=on" if _HAS_DUCK else "duckdb=off"
    print(f"[stats] parsed={parsed_n} cached={cached_n} dropped={dropped} {duck_state}")
print(f"indexed {len(records)} records, {len(edges)} edges, {len(rev_rows)} backlinks")
