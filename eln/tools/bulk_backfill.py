#!/usr/bin/env python3
"""bulk_backfill.py — scan wiki/summaries/, build a matching LIT card for
each wiki summary that has a DOI, auto-fill wiki_link.

Usage:
  python tools/bulk_backfill.py --dry-run              # list candidates only, do not call Crossref
  python tools/bulk_backfill.py --limit 5              # process only first 5
  python tools/bulk_backfill.py --sleep 1.5            # Crossref request interval (seconds)
  python tools/bulk_backfill.py                        # full run

DOI extraction priority: frontmatter fields (paper_doi/doi/DOI) -> sources: list URL -> first 4000 chars of body.
arxiv.org/abs/<id> is recognized and converted to 10.48550/arXiv.<id>.

Skip conditions: (1) an existing LIT card's wiki_link points to this summary, (2) no DOI extractable.
"""
import os, sys, re, time, argparse, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import registry as R
import config as _cfg

ROOT = R.ROOT
REPO_ROOT = _cfg.REPO_ROOT
SUM_DIR = os.path.join(_cfg.WIKI_ROOT, "summaries")
LIT_DIR = os.path.join(ROOT, "literature")
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
ARXIV_URL_RE = re.compile(r"arxiv\.org/abs/(\d{4}\.\d{4,5})", re.I)

# Non-academic wiki summary slug patterns — skip during backfill.
# These are social-media commentary, not primary literature; any DOI in the
# body belongs to a paper being *discussed*, not the summary's subject.
NON_ACADEMIC_SLUGS = ("wechat-", "-wechat-", "xhs-", "-xhs-", "weibo-",
                      "-weibo-", "blog-", "-x-tweet")

# bioRxiv/medRxiv version suffixes are not part of the DOI.
VERSION_SUFFIX_RE = re.compile(r"v\d+$", re.I)


def clean_doi(doi):
    """Strip trailing version suffix like v1, v2 (bioRxiv/medRxiv)."""
    return VERSION_SUFFIX_RE.sub("", doi.rstrip(".,;)"))


def is_non_academic_slug(filename):
    stem = filename.lower().rstrip(".md")
    return any(pat in stem for pat in NON_ACADEMIC_SLUGS)


def extract_doi(fm_raw, body):
    """Extract DOI by priority. Returns (doi, source_tag) or (None, None)."""
    for key in ("paper_doi", "doi", "DOI"):
        km = re.search(rf'^{key}:\s*["\']?({DOI_RE.pattern})', fm_raw, re.M)
        if km:
            return clean_doi(km.group(1).rstrip('"\'')), f"frontmatter:{key}"
    srcm = DOI_RE.search(fm_raw)
    if srcm:
        return clean_doi(srcm.group(0)), "frontmatter:sources"
    srcm = DOI_RE.search(body[:4000])
    if srcm:
        return clean_doi(srcm.group(0)), "body-head"
    am = ARXIV_URL_RE.search(fm_raw + body[:2000])
    if am:
        return f"10.48550/arXiv.{am.group(1)}", "arxiv-url"
    return None, None


def existing_wiki_links():
    """Scan existing LIT cards, return set of wiki_link values (path before extension)."""
    seen = set()
    if not os.path.isdir(LIT_DIR):
        return seen
    for fn in os.listdir(LIT_DIR):
        if not fn.endswith(".md"):
            continue
        p = os.path.join(LIT_DIR, fn)
        with open(p, encoding="utf-8") as f:
            head = f.read(2000)
        m = re.search(r"^wiki_link:\s*(.+)$", head, re.M)
        if m:
            seen.add(m.group(1).strip())
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="list candidates only, do not actually create cards")
    ap.add_argument("--limit", type=int, default=0, help="process at most N items (0 = unlimited)")
    ap.add_argument("--sleep", type=float, default=1.0, help="sleep seconds after each call (rate-limit)")
    ap.add_argument("--by", default=os.environ.get("LABOS_USER") or os.environ.get("USER") or "me")
    ap.add_argument("--stub-only", action="store_true", help="always use stub mode (no external API calls)")
    args = ap.parse_args()

    if not os.path.isdir(SUM_DIR):
        print(f"❌ wiki summaries directory does not exist: {SUM_DIR}", file=sys.stderr)
        sys.exit(2)

    linked = existing_wiki_links()
    print(f"Existing LIT card wiki_link count: {len(linked)}")

    candidates = []
    skipped_already = 0
    skipped_non_academic = 0
    no_doi = []

    for fn in sorted(os.listdir(SUM_DIR)):
        if not fn.endswith(".md"):
            continue
        if is_non_academic_slug(fn):
            skipped_non_academic += 1
            continue
        p = os.path.join(SUM_DIR, fn)
        rel = os.path.relpath(p, REPO_ROOT)
        if rel in linked:
            skipped_already += 1
            continue
        with open(p, encoding="utf-8") as f:
            txt = f.read()
        m = re.match(r"^---\n(.*?)\n---\n(.*)", txt, re.DOTALL)
        if not m:
            continue
        fm_raw, body = m.group(1), m.group(2)
        doi, tag = extract_doi(fm_raw, body)
        if doi:
            candidates.append((rel, doi, tag))
        else:
            no_doi.append(fn)

    print(f"Skipped (existing card): {skipped_already}")
    print(f"Skipped (non-academic: wechat/xhs/blog): {skipped_non_academic}")
    print(f"Candidates to build: {len(candidates)}")
    print(f"No DOI (skipped): {len(no_doi)}")

    if args.dry_run:
        print("\n=== dry-run candidate list ===")
        for rel, doi, tag in candidates[: args.limit or 20]:
            print(f"  {doi:50s}  [{tag}]  <- {os.path.basename(rel)}")
        return

    if args.limit:
        candidates = candidates[: args.limit]

    ok = dup = fail = 0
    lit_from_doi = os.path.join(TOOLS_DIR, "lit_from_doi.py")

    for i, (rel, doi, tag) in enumerate(candidates, 1):
        cmd = [sys.executable, lit_from_doi, doi, "--by", args.by,
               "--wiki-link", rel, "--no-index"]
        if args.stub_only:
            cmd.append("--stub")
        print(f"[{i}/{len(candidates)}] {doi}  [{tag}]")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            out = r.stdout.strip()
            if "[dup]" in out:
                dup += 1
                print(f"    dup")
            elif "✅" in out:
                ok += 1
                print(f"    ok: {out.splitlines()[-2] if len(out.splitlines()) >= 2 else out}")
            else:
                fail += 1
                print(f"    fail: {out[:200]}")
                if r.stderr:
                    print(f"    stderr: {r.stderr[:200]}")
        except subprocess.TimeoutExpired:
            fail += 1
            print(f"    timeout")
        time.sleep(args.sleep)

    print(f"\n=== Results ===")
    print(f"Created: {ok}")
    print(f"Deduplicated: {dup}")
    print(f"Failed: {fail}")
    print(f"Total: {ok + dup + fail}")

    if ok > 0 and not args.dry_run:
        print("\nTriggering index.py + wiki_sync.py --fix ...")
        subprocess.run([sys.executable, os.path.join(TOOLS_DIR, "index.py")], check=False)
        subprocess.run([sys.executable, os.path.join(TOOLS_DIR, "wiki_sync.py"), "--fix"], check=False)


if __name__ == "__main__":
    main()
