#!/usr/bin/env python3
"""Rename the slug of an existing experiment (the descriptive suffix after the ID in the file/folder name).

**The EXP ID never changes** (frontmatter `id` is the authoritative, validate-recognized stable reference).
This tool only changes the filesystem-level slug suffix so you can quickly see what an experiment did.

Usage:
  python tools/rename_experiment.py EXP-2026-07-12-01 crisproff-guide-library
  python tools/rename_experiment.py EXP-2026-07-12-01-old-slug new-slug
  python tools/rename_experiment.py EXP-2026-07-12-01 new-slug --dry-run

What it does:
  1. Locate the .md card and (optionally) same-named artifact folder for the ID
  2. Rename both to the new slug (preferring `git mv`, falling back to `os.rename`)
  3. In-place replace every `EXP-XXX-<oldslug>` with `EXP-XXX-<newslug>` in the two files
     (the card md + folder README.md; no other files are touched)
  4. Grep the whole library for the old name, list **references elsewhere**, and prompt for manual updates
     (not auto-changed, to avoid collateral damage)
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
import fm
from fm import parse
import registry as R

ROOT = R.ROOT
EXP_ID_RE = re.compile(r"^EXP-\d{4}-\d{2}-\d{2}-\d{2}")

def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:60]

def _try_git_mv(src, dst):
    """git mv if repo tracks src, else os.rename. Return True on success."""
    try:
        r = subprocess.run(["git", "mv", src, dst],
                           cwd=ROOT, capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            return "git"
    except Exception:  # noqa: BLE001
        pass
    os.rename(src, dst)
    return "os"

def _find_exp(id_or_full):
    """Find EXP by ID. Accepts either bare ID or full stem (ID-slug).

    Returns (rid, md_path, current_slug_or_empty, folder_path_or_None).
    """
    m = EXP_ID_RE.match(id_or_full)
    if not m:
        raise SystemExit(f"input doesn't look like an EXP ID: {id_or_full}")
    rid = m.group(0)

    # walk experiments/, find a .md whose frontmatter id == rid
    exp_root = os.path.join(ROOT, "experiments")
    md_path = None
    for dp, _, fs in os.walk(exp_root):
        for fn in fs:
            if not fn.endswith(".md") or not fn.startswith(rid):
                continue
            p = os.path.join(dp, fn)
            meta, _ = parse(p)
            if meta.get("id") == rid:
                if md_path is not None:
                    raise SystemExit(f"multiple md files match id={rid} -- please investigate manually:\n  {md_path}\n  {p}")
                md_path = p
    if md_path is None:
        raise SystemExit(f"can't find any md with frontmatter id={rid} under experiments/")

    stem = os.path.splitext(os.path.basename(md_path))[0]      # EXP-XXX-<slug>
    current_slug = stem[len(rid):].lstrip("-") if stem != rid else ""
    folder_candidate = os.path.join(os.path.dirname(md_path), stem)
    folder_path = folder_candidate if os.path.isdir(folder_candidate) else None
    return rid, md_path, current_slug, folder_path

def _grep_references(needle, exclude_paths):
    """Return list of files (relative to ROOT) that mention `needle`.
    Excludes the given paths + `index/`, `.git/`, `tools/`, `templates/`.
    """
    hits = []
    exclude_dirs = {".git", "index", "tools", "templates"}
    exclude_paths = {os.path.abspath(p) for p in exclude_paths}
    for dp, dnames, fs in os.walk(ROOT):
        dnames[:] = [d for d in dnames if d not in exclude_dirs]
        for fn in fs:
            p = os.path.join(dp, fn)
            if os.path.abspath(p) in exclude_paths:
                continue
            # only scan text-ish files to avoid binary noise
            if not fn.endswith((".md", ".tsv", ".csv", ".txt", ".yaml", ".yml", ".json", ".py")):
                continue
            try:
                with open(p, encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if needle in line:
                            hits.append((os.path.relpath(p, ROOT), i, line.rstrip("\n")))
                            break  # only need to know it hits
            except Exception:  # noqa: BLE001
                pass
    return hits

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id_or_stem", help="EXP-YYYY-MM-DD-NN or EXP-YYYY-MM-DD-NN-<old-slug>")
    ap.add_argument("new_slug", help="New slug (will be auto-slugified, length <= 60)")
    ap.add_argument("--dry-run", dest="dry_run", action="store_true",
                    help="Print what would be done, do not write to disk")
    a = ap.parse_args()

    rid, md_path, current_slug, folder_path = _find_exp(a.id_or_stem)
    new_slug = slugify(a.new_slug)
    if not new_slug:
        raise SystemExit("new-slug is empty after slugify, refusing (to clear the slug, edit manually)")
    if new_slug == current_slug:
        print(f"New slug is identical to old slug ({new_slug!r}), nothing to do")
        return

    old_stem = f"{rid}-{current_slug}" if current_slug else rid
    new_stem = f"{rid}-{new_slug}"
    new_md_path = os.path.join(os.path.dirname(md_path), f"{new_stem}.md")
    new_folder_path = (os.path.join(os.path.dirname(md_path), new_stem)
                       if folder_path else None)

    print(f"EXP: {rid}")
    print(f"  Current: {os.path.relpath(md_path, ROOT)}")
    if folder_path:
        print(f"           {os.path.relpath(folder_path, ROOT)}/")
    print(f"  Rename to: {os.path.relpath(new_md_path, ROOT)}")
    if folder_path:
        print(f"             {os.path.relpath(new_folder_path, ROOT)}/")

    # Check for conflicts
    if os.path.exists(new_md_path):
        raise SystemExit(f"❌ Target md already exists: {new_md_path}")
    if new_folder_path and os.path.exists(new_folder_path):
        raise SystemExit(f"❌ Target folder already exists: {new_folder_path}")

    # Grep the whole library for the old name (excluding the two files being changed) and report references elsewhere
    other_refs = _grep_references(
        old_stem, exclude_paths=[md_path] + ([os.path.join(folder_path, "README.md")] if folder_path else [])
    )

    if a.dry_run:
        print()
        print("[dry-run] Will replace every EXP-XXX-<old> -> EXP-XXX-<new> in these two files:")
        print(f"[dry-run]   {os.path.relpath(new_md_path, ROOT)}")
        if new_folder_path:
            print(f"[dry-run]   {os.path.relpath(new_folder_path, ROOT)}/README.md")
        if other_refs:
            print()
            print(f"[dry-run] ⚠️  {len(other_refs)} other files mention {old_stem!r} (not auto-changed, please review):")
            for p, ln, line in other_refs[:20]:
                print(f"[dry-run]   {p}:{ln}  {line[:100]}")
            if len(other_refs) > 20:
                print(f"[dry-run]   ...({len(other_refs) - 20} more omitted)")
        print()
        print("[dry-run] Nothing written. Drop --dry-run to actually rename.")
        return

    # Perform the rename
    mv_kind = _try_git_mv(md_path, new_md_path)
    print(f"✓ mv md   ({mv_kind})")
    if folder_path:
        mv_kind = _try_git_mv(folder_path, new_folder_path)
        print(f"✓ mv folder ({mv_kind})")

    # In-place replace old_stem -> new_stem in the two files
    for p in [new_md_path,
              os.path.join(new_folder_path, "README.md") if new_folder_path else None]:
        if p and os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                body = f.read()
            new_body = body.replace(old_stem, new_stem)
            if new_body != body:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(new_body)
                print(f"✓ In-place replaced {os.path.relpath(p, ROOT)}")

    if other_refs:
        print()
        print(f"⚠️  {len(other_refs)} other files mention old name {old_stem!r}; this tool did **not** change them:")
        for p, ln, line in other_refs[:20]:
            print(f"   {p}:{ln}  {line[:100]}")
        if len(other_refs) > 20:
            print(f"   ...({len(other_refs) - 20} more omitted)")
        print()
        print("If you want a one-shot replace (use with care):")
        print(f"   grep -rl --include='*.md' --include='*.tsv' --include='*.py' \\")
        print(f"        -e {old_stem!r} {os.path.relpath(ROOT, os.getcwd())} \\")
        print(f"        | xargs sed -i 's|{old_stem}|{new_stem}|g'")

    print()
    print("Next: python tools/index.py → python tools/validate.py")


if __name__ == "__main__":
    main()
