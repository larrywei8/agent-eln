#!/usr/bin/env python3
"""lit_from_doi.py — DOI -> Crossref metadata -> LIT card.

Phase 3 (2026-07-11). Behavior contract: references/scicrucible-borrowed.md § 1/4.

Usage:
  python tools/lit_from_doi.py 10.1038/s41586-026-XXXXX-Y
  python tools/lit_from_doi.py https://doi.org/10.1038/xxx --by me
  python tools/lit_from_doi.py 10.xxx/yyy --stub        # skip Crossref, build skeleton only

Flow:
  1) Normalize DOI (strip https://, doi: prefix, lowercase).
  2) Query index/data.duckdb: SELECT id FROM records WHERE doi = ? — on hit, print dup and exit.
  3) --stub or Crossref lookup fails -> build minimal skeleton card (title=DOI, paper_type=preprint fallback).
  4) Otherwise call Crossref REST (https://api.crossref.org/works/<doi>), fill title/authors/year/journal/paper_type.
  5) Write literature/LIT-XXXX-<slug>.md; raw JSON saved to raw/crossref/<doi>.json.
  6) Trigger index.py (incremental, Phase 1 is cheap).
"""
import os, sys, re, json, argparse, datetime, subprocess
from urllib import request as _urlreq
from urllib.error import URLError, HTTPError
sys.path.insert(0, os.path.dirname(__file__))
import registry as R
from fm import parse

ROOT = R.ROOT
LIT_DIR = os.path.join(ROOT, "literature")
RAW_DIR = os.path.join(ROOT, "raw", "crossref")
DUCK = os.path.join(ROOT, "index", "data.duckdb")
TPL = os.path.join(ROOT, "templates", "literature.md")

CROSSREF_TO_PAPER_TYPE = {
    "journal-article": "experimental",
    "proceedings-article": "experimental",
    "book-chapter": "review",
    "review-article": "review",
    "posted-content": "preprint",
    "report": "computational",
}

def normalize_doi(s):
    s = s.strip().lower()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s)
    s = re.sub(r"^doi:\s*", "", s)
    return s.rstrip("./ ")

def lookup_dup(doi):
    if not os.path.exists(DUCK):
        return None
    try:
        import duckdb
    except ImportError:
        return None
    con = duckdb.connect(DUCK, read_only=True)
    try:
        row = con.execute("SELECT id FROM records WHERE doi = ?", [doi]).fetchone()
        return row[0] if row else None
    finally:
        con.close()

def fetch_crossref(doi, timeout=15):
    import config as _cfg
    url = f"https://api.crossref.org/works/{doi}"
    req = _urlreq.Request(url, headers={"User-Agent": f"lab-os-lit-ingest/0.1 (mailto:{_cfg.CONTACT_EMAIL})"})
    with _urlreq.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def is_arxiv_doi(doi):
    return doi.lower().startswith("10.48550/arxiv.")

def fetch_arxiv(doi, timeout=15):
    """arxiv API returns Atom XML; extract minimal fields. DOI form: 10.48550/arxiv.2502.18864."""
    arxiv_id = doi.split("arxiv.", 1)[1] if "arxiv." in doi.lower() else doi.rsplit("/", 1)[-1]
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    req = _urlreq.Request(url, headers={"User-Agent": "ELN-lit-ingest/0.1"})
    with _urlreq.urlopen(req, timeout=timeout) as r:
        xml = r.read().decode("utf-8")
    import xml.etree.ElementTree as ET
    ns = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(xml)
    entry = root.find("a:entry", ns)
    if entry is None:
        return None
    title = (entry.findtext("a:title", "", ns) or "").strip().replace("\n", " ").replace("  ", " ")
    authors = [a.findtext("a:name", "", ns).strip() for a in entry.findall("a:author", ns)]
    published = entry.findtext("a:published", "", ns)
    year = int(published[:4]) if published[:4].isdigit() else None
    return {"title": title, "authors": [a for a in authors if a], "year": year,
            "journal": "arXiv", "paper_type": "preprint", "cr_type": "posted-content"}

def parse_crossref(js):
    msg = js.get("message", {})
    title = (msg.get("title") or [""])[0].strip()
    authors = []
    for a in msg.get("author", []) or []:
        parts = [a.get("given", ""), a.get("family", "")]
        authors.append(" ".join(p for p in parts if p).strip())
    year = None
    for k in ("published-print", "published-online", "issued", "created"):
        dp = msg.get(k, {}).get("date-parts") if isinstance(msg.get(k), dict) else None
        if dp and dp[0]:
            year = dp[0][0]
            break
    journal = (msg.get("container-title") or [""])[0]
    cr_type = msg.get("type", "")
    paper_type = CROSSREF_TO_PAPER_TYPE.get(cr_type, "experimental")
    return {"title": title, "authors": authors, "year": year,
            "journal": journal, "paper_type": paper_type, "cr_type": cr_type}

def next_lit_id():
    """Scan literature/ for LIT-XXXX, take max serial +1 (same semantics as new.py, but independent to avoid argparse dependency)."""
    max_n = 0
    if os.path.isdir(LIT_DIR):
        for fn in os.listdir(LIT_DIR):
            m = re.match(r"LIT-(\d+)", fn)
            if m:
                max_n = max(max_n, int(m.group(1)))
    return f"LIT-{max_n + 1:04d}"

def slugify(s, maxlen=40):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (s or "").lower()).strip("-")
    return s[:maxlen]

def render_wiki_link_md(wiki_link):
    if not wiki_link:
        return "_(Not yet studied in depth — create a wiki summary then run `tools/wiki_sync.py --fix`)_"
    import config as _cfg
    rel = wiki_link.lstrip("/")
    url = _cfg.wiki_url(rel)
    label = os.path.splitext(os.path.basename(wiki_link))[0]
    return f"[{label}]({url})"

def render_card(rid, doi, meta, by, stub):
    tpl = open(TPL, encoding="utf-8").read()
    date = datetime.date.today().isoformat()
    out = tpl.replace("{DATE}", date)
    out = re.sub(r"^id:.*$", f"id: {rid}", out, count=1, flags=re.M)

    def set_scalar(txt, key, val):
        val = "" if val is None else str(val)
        return re.sub(rf"^{re.escape(key)}:.*$", f"{key}: {val}", txt, count=1, flags=re.M)

    def set_list(txt, key, items):
        rendered = "[" + ", ".join(f'"{a}"' for a in items) + "]"
        return re.sub(rf"^{re.escape(key)}:.*$", f"{key}: {rendered}", txt, count=1, flags=re.M)

    if stub:
        title = f"DOI:{doi} (stub — fill metadata)"
        out = set_scalar(out, "title", title)
        out = set_scalar(out, "doi", doi)
        out = set_scalar(out, "paper_type", "preprint")
        out = set_scalar(out, "created_by", by)
    else:
        out = set_scalar(out, "title", meta["title"])
        out = set_list(out, "authors", meta["authors"] or [])
        out = set_scalar(out, "year", meta["year"] or "")
        out = set_scalar(out, "journal", meta["journal"] or "")
        out = set_scalar(out, "doi", doi)
        out = set_scalar(out, "paper_type", meta["paper_type"])
        out = set_scalar(out, "created_by", by)
    return out

def append_daylog(rid, doi, title):
    date = datetime.date.today().isoformat()
    year = date[:4]
    d = os.path.join(ROOT, "experiments", year, date)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "_daylog.md")
    header_needed = not os.path.exists(p)
    with open(p, "a", encoding="utf-8") as f:
        if header_needed:
            f.write(f"# Daily log {date}\n\n")
        f.write(f"- [LIT ingest] `{rid}` — {title[:80]} (doi:{doi})\n")

def main():
    ap = argparse.ArgumentParser(description="DOI → LIT card")
    ap.add_argument("doi", help="bare DOI or https://doi.org/... URL")
    ap.add_argument("--by", default=os.environ.get("LABOS_USER") or os.environ.get("USER") or "me")
    ap.add_argument("--stub", action="store_true", help="do not query Crossref, build skeleton only")
    ap.add_argument("--wiki-link", default="", help="wiki summary repo-relative path, e.g.: wiki/summaries/foo.md")
    ap.add_argument("--no-index", action="store_true", help="skip final index.py (for testing)")
    args = ap.parse_args()

    doi = normalize_doi(args.doi)
    if not doi or not re.match(r"^10\.\d{4,9}/", doi):
        print(f"❌ DOI looks invalid: {doi!r}", file=sys.stderr); sys.exit(2)

    dup = lookup_dup(doi)
    if dup:
        print(f"[dup] {doi} already ingested as {dup}"); sys.exit(0)

    meta = None
    if not args.stub:
        if is_arxiv_doi(doi):
            try:
                meta = fetch_arxiv(doi)
                if meta:
                    print(f"[arxiv-api] fetch succeeded: {meta['title'][:60]}")
                else:
                    print("⚠️  arxiv API returned no entry, falling back to --stub")
                    args.stub = True
            except (URLError, HTTPError, TimeoutError, Exception) as e:
                print(f"⚠️  arxiv API failed ({e}), falling back to --stub")
                args.stub = True
        else:
            try:
                js = fetch_crossref(doi)
                os.makedirs(RAW_DIR, exist_ok=True)
                with open(os.path.join(RAW_DIR, f"{doi.replace('/', '_')}.json"), "w") as f:
                    json.dump(js, f, indent=1)
                meta = parse_crossref(js)
            except (URLError, HTTPError, TimeoutError) as e:
                print(f"⚠️  Crossref fetch failed ({e}), falling back to --stub mode")
                args.stub = True

    rid = next_lit_id()
    slug = slugify(meta["title"] if meta and meta.get("title") else doi.replace("/", "-"))
    path = os.path.join(LIT_DIR, f"{rid}-{slug}.md" if slug else f"{rid}.md")
    if os.path.exists(path):
        print(f"❌ Target already exists: {path}"); sys.exit(1)
    os.makedirs(LIT_DIR, exist_ok=True)
    content = render_card(rid, doi, meta, args.by, args.stub)
    if args.wiki_link:
        content = re.sub(r"^wiki_link:.*$", f"wiki_link: {args.wiki_link}", content, count=1, flags=re.M)
    content = content.replace("{WIKI_LINK_MD}", render_wiki_link_md(args.wiki_link))
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    title = meta["title"] if meta else f"stub for {doi}"
    append_daylog(rid, doi, title)

    print(f"✅ Created {rid}  ({title[:60]})")
    print(f"   -> {os.path.relpath(path, ROOT)}")

    if not args.no_index:
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "index.py")], check=False)

if __name__ == "__main__":
    main()
