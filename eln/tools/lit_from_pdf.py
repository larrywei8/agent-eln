#!/usr/bin/env python3
"""lit_from_pdf.py — PDF -> text (markitdown) -> DOI regex -> delegate to lit_from_doi.py.

Phase 3 (2026-07-11).

Usage:
  python tools/lit_from_pdf.py inbox/paper.pdf
  python tools/lit_from_pdf.py inbox/paper.pdf --by me
  python tools/lit_from_pdf.py inbox/paper.pdf --extractor markitdown|zo

Flow:
  1) markitdown <pdf> extracts full text (preferred); if unavailable, fall back to --text-file (for testing).
  2) First 2 pages regex (10\.\d{4,9}/[-._;()/:A-Za-z0-9]+) to catch DOI.
  3) Found -> call lit_from_doi.py <doi> --by ...
  4) Not found -> print first 400 chars, prompt to pass DOI manually.
  5) Extracted text is saved to literature/LIT-XXXX-<slug>.txt (optional in next index step).
"""
import os, sys, re, argparse, subprocess, shutil, tempfile

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
ARXIV_ID_RE = re.compile(r"(?:arxiv[-_:]?|arXiv:)?(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE)
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))

def find_arxiv_id_in_filename(pdf_path):
    """Extract arxiv id from filename, e.g. 2502.18864 or arxiv-2502.18864.pdf."""
    base = os.path.basename(pdf_path)
    m = ARXIV_ID_RE.search(base)
    if m:
        return m.group(1)
    return None

def extract_text(pdf, extractor):
    """Return (text_or_None, method_used)."""
    if extractor == "markitdown":
        exe = shutil.which("markitdown")
        if exe:
            try:
                r = subprocess.run([exe, pdf], capture_output=True, text=True, timeout=120)
                if r.returncode == 0:
                    return r.stdout, "markitdown"
            except (subprocess.TimeoutExpired, OSError):
                pass
        try:
            r = subprocess.run([sys.executable, "-m", "markitdown", pdf],
                               capture_output=True, text=True, timeout=120)
            if r.returncode == 0:
                return r.stdout, "markitdown-module"
        except (subprocess.TimeoutExpired, OSError):
            pass
    return None, None

def find_doi(text):
    if not text:
        return None
    head = text[:8000]
    m = DOI_RE.search(head)
    if not m:
        return None
    doi = m.group(0).rstrip(".,;)")
    return doi.lower()

def main():
    ap = argparse.ArgumentParser(description="PDF → LIT card via DOI regex + Crossref")
    ap.add_argument("pdf", help="PDF path")
    ap.add_argument("--by", default=os.environ.get("LABOS_USER") or os.environ.get("USER") or "me")
    ap.add_argument("--extractor", default="markitdown", choices=["markitdown"])
    ap.add_argument("--doi", help="manually specify DOI (skip extraction)")
    ap.add_argument("--text-file", help="for testing: directly read a .txt/.md as extraction result")
    ap.add_argument("--no-index", action="store_true")
    ap.add_argument("--stub", action="store_true", help="pass to lit_from_doi: skip Crossref")
    ap.add_argument("--wiki-link", help="passthrough: pre-fill frontmatter wiki_link field")
    args = ap.parse_args()

    if not (args.pdf.endswith(".pdf") or args.text_file):
        print("⚠️  Expected .pdf extension; continuing anyway.", file=sys.stderr)

    text = None
    method = None
    if args.doi:
        method = "manual"
    elif args.text_file:
        with open(args.text_file, encoding="utf-8", errors="replace") as f:
            text = f.read()
        method = "text-file"
    elif os.path.exists(args.pdf):
        text, method = extract_text(args.pdf, args.extractor)
        if text is None:
            print(f"❌ Extraction failed (markitdown not installed?). Try `pip install markitdown` or specify --doi manually.", file=sys.stderr)
            sys.exit(3)
    else:
        print(f"❌ File does not exist: {args.pdf}", file=sys.stderr); sys.exit(2)

    doi = args.doi or find_doi(text)
    if not doi:
        arxiv_id = find_arxiv_id_in_filename(args.pdf)
        if arxiv_id:
            doi = f"10.48550/arXiv.{arxiv_id}"
            print(f"[arxiv] filename matched arXiv id={arxiv_id} -> constructed DOI={doi}")
        else:
            preview = (text or "")[:400].strip()
            print("❌ No DOI pattern found in header, and filename did not match arXiv id. First 400 chars preview:", file=sys.stderr)
            print("---", file=sys.stderr); print(preview, file=sys.stderr); print("---", file=sys.stderr)
            sys.exit(4)

    print(f"[extract] method={method} doi={doi}")

    cmd = [sys.executable, os.path.join(TOOLS_DIR, "lit_from_doi.py"), doi, "--by", args.by]
    if args.no_index:
        cmd.append("--no-index")
    if args.stub:
        cmd.append("--stub")
    if args.wiki_link:
        cmd.extend(["--wiki-link", args.wiki_link])
    r = subprocess.run(cmd)
    sys.exit(r.returncode)

if __name__ == "__main__":
    main()
