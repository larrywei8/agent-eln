#!/usr/bin/env python3
"""health.py — soft-quality checkup (report-only, does not block commit).

Phase 3 (2026-07-11). Behavior contract: references/scicrucible-borrowed.md § 3.
Phase 2 (2026-07-13): added completeness/lab-readiness checks (10, 11).

Usage:
  python tools/health.py                # print report to stdout
  python tools/health.py --write        # also write to reports/health-YYYYMMDD.md
  python tools/health.py --json         # machine-readable

Checks (all warn, never exit 1):
  1) Structural integrity (missing required frontmatter fields, [TBD] markers)
  2) Content quality ([TBD] markers, outline-only detection)
  3) Knowledge gaps (high-frequency keywords mentioned in LIT but not in wiki)  <- placeholder only
  4) Consistency (LLM semantic comparison)                                       <- placeholder, not enabled
  5) Literature quality (paper_type coverage)
  6) DOI field consistency (missing rate / format)
  7) LIT index cache consistency (DuckDB ↔ files)
  8) LIT card health score
  9) Cross-repo sync consistency (LIT wiki_link ↔ wiki/summaries)
 10) Lab-readiness completeness (Phase 2 — reagent/chemical/kit/cell-line/instrument)
 11) Literature linkage (Phase 2 — LIT cards with no incoming or outgoing EXP/IDEA/PRJ link)
"""
import os, sys, re, json, datetime, argparse
sys.path.insert(0, os.path.dirname(__file__))
from fm import parse
import registry as R
import config as _cfg

ROOT = R.ROOT
REPO_ROOT = _cfg.REPO_ROOT
WIKI_ROOT = _cfg.WIKI_ROOT
LIT_DIR = os.path.join(ROOT, "literature")
DUCK = os.path.join(ROOT, "index", "data.duckdb")
DOI_FORMAT_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")

def walk_md():
    for dp, _, fs in os.walk(ROOT):
        if any(s in dp for s in (".git", "/index", "/templates", "/tools", "/reports")):
            continue
        for fn in fs:
            if fn.endswith(".md"):
                yield os.path.join(dp, fn)

def lit_files():
    if not os.path.isdir(LIT_DIR): return []
    return [os.path.join(LIT_DIR, fn) for fn in sorted(os.listdir(LIT_DIR)) if fn.endswith(".md")]

def prose_paragraph_count(body):
    """Consecutive narrative paragraph = at least two non-empty lines, not starting with '- '/'|'/'#'."""
    n = 0
    for para in re.split(r"\n\s*\n", body):
        para = para.strip()
        if not para: continue
        lines = [l for l in para.splitlines() if l.strip()]
        if not lines: continue
        if any(l.lstrip().startswith(("- ", "* ", "|", "#")) for l in lines): continue
        if len(lines) >= 2 or len(para) >= 200:
            n += 1
    return n

def check_1_structural(all_files):
    issues = []
    for p in all_files:
        meta, body = parse(p)
        rid = meta.get("id", "")
        if not rid or any(x in rid for x in ("XXXX", "YYYY", "-NN")): continue
        spec = R.TYPES.get(meta.get("type"))
        if not spec: continue
        for f in spec["required"]:
            v = meta.get(f)
            if v in (None, "", []):
                issues.append((rid, f"missing required {f}", os.path.relpath(p, ROOT)))
        if "[TBD]" in body:
            issues.append((rid, "contains [TBD] marker", os.path.relpath(p, ROOT)))
    return issues

def check_2_content(all_files):
    issues = []
    for p in all_files:
        meta, body = parse(p)
        rid = meta.get("id", "")
        if not rid or any(x in rid for x in ("XXXX", "YYYY", "-NN")): continue
        if "[TBD]" in body:
            issues.append((rid, "contains [TBD] marker", os.path.relpath(p, ROOT)))
        if len(body) > 800 and prose_paragraph_count(body) < 3:
            issues.append((rid, "outline-only (narrative paragraphs < 3)", os.path.relpath(p, ROOT)))
    return issues

def check_5_lit_quality(lits):
    issues = []
    for p in lits:
        meta, _ = parse(p)
        rid = meta.get("id", "")
        if not rid.startswith("LIT-"): continue
        pt = meta.get("paper_type", "")
        if not pt:
            issues.append((rid, "paper_type not filled", os.path.relpath(p, ROOT)))
        elif pt not in ("experimental", "computational", "review", "clinical_trial", "preprint", "clinical"):
            issues.append((rid, f"paper_type non-standard: {pt}", os.path.relpath(p, ROOT)))
    return issues

def check_6_doi(lits):
    issues = []
    total = 0
    missing = 0
    for p in lits:
        meta, _ = parse(p)
        rid = meta.get("id", "")
        if not rid.startswith("LIT-"): continue
        total += 1
        doi = meta.get("doi", "")
        if not doi:
            missing += 1
            issues.append((rid, "DOI missing", os.path.relpath(p, ROOT)))
            continue
        if not DOI_FORMAT_RE.match(doi):
            issues.append((rid, f"DOI format abnormal: {doi}", os.path.relpath(p, ROOT)))
        if doi.startswith(("http://", "https://")) or "doi.org" in doi:
            issues.append((rid, "DOI contains URL prefix, should be bare DOI", os.path.relpath(p, ROOT)))
    summary = f"DOI coverage: {total - missing}/{total} = {(1 - missing/total)*100:.0f}%" if total else "no LIT cards"
    return issues, summary

def check_7_cache(lits):
    issues = []
    if not os.path.exists(DUCK):
        return [(None, "index/data.duckdb missing (install duckdb or run tools/index.py)", "")]
    try:
        import duckdb
    except ImportError:
        return [(None, "duckdb not installed, skipping cache consistency", "")]
    con = duckdb.connect(DUCK, read_only=True)
    try:
        db_ids = {r[0]: r[1] for r in con.execute("SELECT id, path FROM records WHERE type='literature'").fetchall()}
        db_dois = con.execute("SELECT doi, count(*) FROM records WHERE doi IS NOT NULL GROUP BY doi HAVING count(*) > 1").fetchall()
    finally:
        con.close()
    fs_ids = {}
    for p in lits:
        meta, _ = parse(p)
        rid = meta.get("id", "")
        if rid.startswith("LIT-"):
            fs_ids[rid] = os.path.relpath(p, ROOT)
    for rid in fs_ids.keys() - db_ids.keys():
        issues.append((rid, "file exists but not in DB -> run index.py", fs_ids[rid]))
    for rid in db_ids.keys() - fs_ids.keys():
        issues.append((rid, "in DB but file deleted -> dangling", db_ids.get(rid, "")))
    for doi, n in db_dois:
        issues.append((None, f"duplicate DOI ({n} records): {doi}", ""))
    return issues

def health_score(path, meta, body, refs_from_edges):
    score = 100
    reasons = []
    n_lines = body.count("\n") + 1
    if n_lines > 300: score -= 15; reasons.append("lines>300")
    if n_lines > 500: score -= 15; reasons.append("lines>500")
    linked = len((meta.get("related_experiments") or []) + (meta.get("related_ideas") or [])) + refs_from_edges
    if linked == 0: score -= 20; reasons.append("island (no EXP/IDEA link)")
    try:
        mtime = os.path.getmtime(path)
        age_days = (datetime.datetime.now().timestamp() - mtime) / 86400
        if age_days > 180: score -= 10; reasons.append(">6 months untouched")
        if age_days > 365: score -= 10; reasons.append(">12 months untouched")
    except OSError:
        pass
    if prose_paragraph_count(body) < 3: score -= 20; reasons.append("outline-only")
    if body.count("not reported") >= 4: score -= 30; reasons.append("many 'not reported' fields")
    return score, reasons

def check_8_scoring(lits):
    scores = []
    edge_count = {}
    if os.path.exists(DUCK):
        try:
            import duckdb
            con = duckdb.connect(DUCK, read_only=True)
            for row in con.execute("SELECT dst, count(*) FROM edges WHERE dst LIKE 'LIT-%' GROUP BY dst").fetchall():
                edge_count[row[0]] = row[1]
            con.close()
        except Exception:
            pass
    for p in lits:
        meta, body = parse(p)
        rid = meta.get("id", "")
        if not rid.startswith("LIT-"): continue
        s, r = health_score(p, meta, body, edge_count.get(rid, 0))
        scores.append((s, rid, os.path.relpath(p, ROOT), r))
    scores.sort()
    return scores

def check_9_wiki_sync(lits):
    issues = []
    for p in lits:
        meta, _ = parse(p)
        rid = meta.get("id", "")
        if not rid.startswith("LIT-"): continue
        wl = meta.get("wiki_link", "")
        if not wl:
            issues.append((rid, "wiki_link not filled", os.path.relpath(p, ROOT)))
            continue
        target = os.path.join(REPO_ROOT, wl)
        if not os.path.exists(target):
            issues.append((rid, f"wiki_link dead: {wl}", os.path.relpath(p, ROOT)))
            continue
        lit_rel = os.path.relpath(p, REPO_ROOT)
        with open(target, encoding="utf-8") as f:
            head = f.read()
        if lit_rel not in head:
            issues.append((rid, f"wiki summary does not back-link LIT: suggest running wiki_sync.py --fix", os.path.relpath(p, ROOT)))
    return issues

def _empty(meta, field):
    """Treat missing / empty / 'unknown' / 'TBD' / '?' as unfilled."""
    v = meta.get(field)
    if v in (None, "", []):
        return True
    if isinstance(v, str) and v.strip().lower() in ("unknown", "tbd", "?", "n/a"):
        return True
    return False

def check_10_lab_readiness(all_files):
    """Warning: records that are structurally valid but not lab-ready.

    Reagent/chemical/kit -> location/lot/expiry (consumables need traceability).
    Cell-line            -> passage/mycoplasma (safety-critical biological QC).
    Instrument           -> sop (operational reference).
    """
    issues = []
    for p in all_files:
        meta, _ = parse(p)
        rid = meta.get("id", "")
        if not rid or any(x in rid for x in ("XXXX", "YYYY", "-NN")):
            continue
        t = meta.get("type")
        rel = os.path.relpath(p, ROOT)
        if t in ("reagent", "chemical", "kit"):
            # location is satisfied by EITHER the freeform 'location' field
            # OR the structured storage_unit + container pair.
            has_location = (not _empty(meta, "location")) or (
                (not _empty(meta, "storage_unit")) and (not _empty(meta, "container"))
            )
            if not has_location:
                issues.append((rid, "missing operational field 'location'", rel))
            for f in ("lot", "expiry"):
                if _empty(meta, f):
                    issues.append((rid, f"missing operational field '{f}'", rel))
        elif t == "cell-line":
            for f in ("passage", "mycoplasma"):
                if _empty(meta, f):
                    issues.append((rid, f"missing biological QC field '{f}'", rel))
        elif t == "instrument":
            if _empty(meta, "sop"):
                issues.append((rid, "no associated SOP", rel))
    return issues

def check_11_lit_linkage(lits, all_files):
    """Warning: LIT cards with no incoming OR outgoing link to EXP/IDEA/PRJ.

    An 'unlinked' LIT card is a paper the corpus catalogs but has not yet
    connected to any hypothesis, experiment, or project — a signal that the
    reader captured metadata but has not yet closed the literature-to-decision
    loop.
    """
    referenced = set()
    for p in all_files:
        meta, _ = parse(p)
        for field in R.FORWARD_REF_FIELDS:
            v = meta.get(field)
            for tgt in ([v] if isinstance(v, str) else (v or [])):
                if isinstance(tgt, str) and tgt.startswith("LIT-"):
                    referenced.add(tgt)

    issues = []
    for p in lits:
        meta, _ = parse(p)
        rid = meta.get("id", "")
        if not rid.startswith("LIT-"):
            continue
        out_links = set()
        for field in ("related_experiments", "related_ideas", "related",
                      "project", "related_projects", "experiments"):
            v = meta.get(field)
            for tgt in ([v] if isinstance(v, str) else (v or [])):
                if isinstance(tgt, str) and any(
                    tgt.startswith(pfx + "-") for pfx in ("EXP", "IDEA", "PRJ")
                ):
                    out_links.add(tgt)
        if rid not in referenced and not out_links:
            issues.append((rid, "unlinked (no EXP/IDEA/PRJ reference either way)",
                           os.path.relpath(p, ROOT)))
    return issues

def render_md(sections):
    date = datetime.date.today().isoformat()
    out = [f"# ELN Health Check — {date}\n"]
    for title, items in sections:
        out.append(f"## {title}\n")
        if not items:
            out.append("- ✅ no issues\n"); continue
        for it in items:
            if isinstance(it, tuple) and len(it) == 4:  # score row
                s, rid, path, reasons = it
                out.append(f"- **{s:3d}** {rid} ({path}) — {', '.join(reasons) if reasons else 'ok'}")
            elif isinstance(it, tuple):
                rid, msg, path = it
                out.append(f"- {rid or '-'}: {msg}" + (f"  `{path}`" if path else ""))
            else:
                out.append(f"- {it}")
        out.append("")
    return "\n".join(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    all_files = list(walk_md())
    lits = lit_files()

    d1 = check_1_structural(all_files)
    d2 = check_2_content(all_files)
    d5 = check_5_lit_quality(lits)
    d6, d6_summary = check_6_doi(lits)
    d7 = check_7_cache(lits)
    d8 = check_8_scoring(lits)
    d9 = check_9_wiki_sync(lits)
    d10 = check_10_lab_readiness(all_files)
    d11 = check_11_lit_linkage(lits, all_files)

    sections = [
        ("1. Structural integrity (frontmatter/placeholders)", d1),
        ("2. Content quality ([TBD]/outline-only)", d2),
        ("3. Knowledge gaps (not enabled)", []),
        ("4. Consistency (not enabled)", []),
        (f"5. Literature quality (paper_type)", d5),
        (f"6. DOI field — {d6_summary}", d6),
        ("7. Cache consistency (DB ↔ FS)", d7),
        ("8. LIT health score (lowest first)", d8[:10]),  # show only worst 10
        ("9. Cross-repo sync (LIT ↔ wiki)", d9),
        (f"10. Lab-readiness completeness ({len(d10)} gaps)", d10),
        (f"11. LIT linkage — {len(d11)}/{len(lits)} unlinked to EXP/IDEA/PRJ",
         d11[:15]),  # cap to worst 15
    ]

    if args.json:
        print(json.dumps({t: len(items) for t, items in sections}, ensure_ascii=False))
        return

    md = render_md(sections)
    print(md)
    if args.write:
        date = datetime.date.today().isoformat()
        reports_dir = os.path.join(ROOT, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        with open(os.path.join(reports_dir, f"health-{date.replace('-','')}.md"), "w", encoding="utf-8") as f:
            f.write(md)
        print(f"\n📄 saved: reports/health-{date.replace('-','')}.md")

if __name__ == "__main__":
    main()
