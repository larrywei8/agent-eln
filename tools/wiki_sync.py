#!/usr/bin/env python3
"""wiki_sync.py — maintain bidirectional links between ELN LIT cards and wiki summaries.

Phase 3 (2026-07-11).

Usage:
  python tools/wiki_sync.py           # check (--check), print drift without modifying files
  python tools/wiki_sync.py --fix     # fix: append LIT card path to wiki summary's sources

Contract (see docs/history/SPEC-phase3.md § B):
  * LIT card has wiki_link: <path relative to repo root>
  * Target summary must exist
  * summary's sources: array contains the LIT card's repo-relative path

  What it does NOT do:
    - Does not create wiki summaries (that's the llm-wiki-anygen skill's job)
    - Does not touch concept pages
    - Does not use fuzzy matching for wiki_link; a dead link is a dead link
"""
import os, sys, argparse
sys.path.insert(0, os.path.dirname(__file__))
import fm
from fm import parse
import registry as R
import config as _cfg

ROOT = R.ROOT
REPO_ROOT = _cfg.REPO_ROOT  # repo root (contains eln/, lims/, wiki/, tools/)
WORKSPACE = REPO_ROOT       # legacy alias — kept so downstream helpers still resolve
LIT_DIR = os.path.join(_cfg.ELN_ROOT, "literature")

def collect_lit_cards():
    if not os.path.isdir(LIT_DIR):
        return []
    out = []
    for fn in sorted(os.listdir(LIT_DIR)):
        if not fn.endswith(".md"): continue
        p = os.path.join(LIT_DIR, fn)
        meta, _ = parse(p)
        if not meta.get("id", "").startswith("LIT-"): continue
        out.append((meta["id"], p, meta.get("wiki_link", "")))
    return out

def resolve_wiki_target(wiki_link):
    """wiki_link is a repo-relative path, e.g. 'wiki/summaries/foo.md'."""
    if not wiki_link: return None
    p = os.path.join(WORKSPACE, wiki_link)
    return p if os.path.exists(p) else None

def rel_workspace(path):
    return os.path.relpath(path, WORKSPACE)

def append_source_if_missing(summary_path, lit_rel):
    """Append an entry to the summary's frontmatter sources: array (if missing).
    Uses fm.set_field, handling block/inline/missing-field cases uniformly.
    Returns True if a modification was made.
    """
    with open(summary_path, encoding="utf-8") as f:
        txt = f.read()
    if not txt.startswith("---"):
        return False

    cur = fm.get_field(txt, "sources")
    if isinstance(cur, list):
        if lit_rel in cur:
            return False
        new_sources = cur + [lit_rel]
    elif cur in (None, "", []):
        new_sources = [lit_rel]
    else:
        # single scalar value — treat as one existing entry, preserve it and append
        if str(cur) == lit_rel:
            return False
        new_sources = [str(cur), lit_rel]

    new_txt = fm.set_field(txt, "sources", new_sources)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(new_txt)
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="fix missing back-links (append LIT path to summary)")
    args = ap.parse_args()

    problems = []
    fixed = 0
    lits = collect_lit_cards()

    for rid, path, wl in lits:
        if not wl:
            problems.append(f"[warn] {rid} has no wiki_link (can be added later)")
            continue
        target = resolve_wiki_target(wl)
        if not target:
            problems.append(f"[error] {rid} wiki_link dead link: {wl}")
            continue
        lit_rel = rel_workspace(path)
        # check reverse sources
        with open(target, encoding="utf-8") as f:
            head = f.read()
        if lit_rel in head:
            continue  # back-link already present
        if args.fix:
            if append_source_if_missing(target, lit_rel):
                fixed += 1
                print(f"[fix] {rid} -> appended to sources of {os.path.relpath(target, WORKSPACE)}")
        else:
            problems.append(f"[drift] {rid}: {os.path.relpath(target, WORKSPACE)} does not list {lit_rel} in sources")

    print(f"scanned {len(lits)} LIT cards; issues={len(problems)}; fixed={fixed}")
    for p in problems:
        print("  ", p)
    sys.exit(0 if not problems or args.fix else 0)

if __name__ == "__main__":
    main()
