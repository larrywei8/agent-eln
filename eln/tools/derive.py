#!/usr/bin/env python3
"""derive.py — create a derived record with a compound ID.

Usage:
  python tools/derive.py <parent-id> <CODE> <instance> [--type sample] [--name "..."]
                                                       [--by <user>] [--date YYYY-MM-DD]
                                                       [--dry-run]

Examples:
  python tools/derive.py MUS-0042 BR 1                       # tissue from a mouse
  python tools/derive.py MUS-0042-BR1 RNA 1                  # RNA from that tissue
  python tools/derive.py PLA-0031 RE 1 --type dna            # restriction digest from a plasmid

What it does:
  1. Verifies the parent record exists.
  2. Verifies the resulting compound-ID depth <= 2 (per hierarchy.md).
  3. Warns if CODE is not registered in vocab.md.
  4. Copies the template for --type (default: sample), sets id/created/created_by/derived_from.
  5. Infers sample_type/source_tissue from the segment code where possible
     (e.g. BR -> sample_type: tissue, source_tissue: brain; RNA -> sample_type: total_RNA).
  6. Inherits organism / source_tissue from the parent when the child does not
     override them (RNA prepared from brain tissue keeps source_tissue: brain).
  7. Writes card.md into the correct folder (same layout as new.py).
"""
import argparse
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import fm
from fm import parse as parse_fm
import registry as R
import hierarchy as H
import vocab as V

ROOT = R.ROOT


# ---- Segment-code -> field-value inference ------------------------------------
# Tissues: CODE -> source_tissue (implies sample_type: tissue)
TISSUE_CODES = {
    "TA":  "tail",
    "EAR": "ear",
    "BR":  "brain",
    "HR":  "heart",
    "LI":  "liver",
    "KD":  "kidney",
    "LU":  "lung",
    "SP":  "spleen",
    "MU":  "muscle",
    "BM":  "bone_marrow",
    "TU":  "tumor",
    "BL":  "blood",
    "SR":  "serum",
    "IN":  "intestine",
    "SK":  "skin",
    "TH":  "thymus",
    "PA":  "pancreas",
    "LN":  "lymph_node",
    "EM":  "embryo",
}
# Nucleic-acid / protein preparations: CODE -> sample_type
PREP_CODES = {
    "RNA":  "total_RNA",
    "MRNA": "mRNA",
    "GDNA": "gDNA",
    "CDNA": "cDNA",
    "PROT": "protein",
    "LIB":  "library",
    "AMP":  "amplicon",
    "GENO": "amplicon",
}
# Anatomical subdivisions (contextual under a tissue parent): CODE -> anatomical_region
ANATOMICAL_CODES = {
    "LV": "left_ventricle",
    "RV": "right_ventricle",
    "AT": "atrium",
}


def find_record(rid):
    """Return absolute path of the .md file whose frontmatter id == rid, else None."""
    for dp, dnames, fs in os.walk(ROOT):
        dnames.sort()
        if any(s in dp for s in (".git", "/index", "/templates", "/tools")):
            continue
        for fn in fs:
            if not fn.endswith(".md"):
                continue
            p = os.path.join(dp, fn)
            try:
                meta, _ = parse_fm(p)
            except Exception:
                continue
            if meta.get("id") == rid:
                return p, meta
    return None, None


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:60]


def target_path(spec, rid, slug):
    """Same layout logic as new.py for resource/file container types (no exp/daily here)."""
    folder = spec["folder"]
    container = spec["container"]
    if container == "dir":
        name = f"{rid}-{slug}" if slug else rid
        return os.path.join(ROOT, folder, name, "card.md")
    name = f"{rid}-{slug}" if slug else rid
    return os.path.join(ROOT, folder, f"{name}.md")


def apply_inference(content, code, parent_meta, target_type):
    """Fill in sample_type / source_tissue / organism based on the segment code
    and inherited parent fields. Never overwrites an explicit non-empty value."""
    # Helper: set a field only if the template currently has it empty.
    def set_if_empty(txt, key, value):
        current = fm.get_field(txt, key)
        if current in (None, "", []):
            return fm.set_field(txt, key, value)
        return txt

    # Tissue codes: sample_type=tissue + source_tissue=<mapped>
    if code in TISSUE_CODES and target_type == "sample":
        content = set_if_empty(content, "sample_type", "tissue")
        content = set_if_empty(content, "source_tissue", TISSUE_CODES[code])

    # Preparation codes: sample_type=<mapped>, inherit source_tissue from parent
    if code in PREP_CODES and target_type == "sample":
        content = set_if_empty(content, "sample_type", PREP_CODES[code])
        inherited_tissue = parent_meta.get("source_tissue")
        if inherited_tissue:
            content = set_if_empty(content, "source_tissue", inherited_tissue)

    # Anatomical subdivision codes: anatomical_region=<mapped>, inherit source_tissue
    if code in ANATOMICAL_CODES and target_type == "sample":
        content = set_if_empty(content, "anatomical_region", ANATOMICAL_CODES[code])
        inherited_tissue = parent_meta.get("source_tissue")
        if inherited_tissue:
            content = set_if_empty(content, "source_tissue", inherited_tissue)

    # Inherit organism from parent (common case: MUS -> SMP).
    # For a MUS parent with no explicit organism, fall back to the Latin binomial.
    parent_organism = parent_meta.get("organism")
    if parent_organism:
        content = set_if_empty(content, "organism", parent_organism)
    elif parent_meta.get("type") == "mouse":
        content = set_if_empty(content, "organism", "Mus musculus")

    return content


def main():
    ap = argparse.ArgumentParser(
        description="Create a derived compound-ID record from a parent.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("parent_id", help="Direct parent record ID (L1 or L2).")
    ap.add_argument("code", help="Segment CODE (2-4 uppercase letters, see vocab.md).")
    ap.add_argument("instance", nargs="?", default="1",
                    help="Instance number for the segment (default: 1).")
    ap.add_argument("--type", default="sample",
                    help="Type of the derived record (default: sample). Must be a "
                         "registry type; the derived-record folder + template follow this.")
    ap.add_argument("--name", default="",
                    help="Optional name for the new record; also used as slug.")
    ap.add_argument("--by", default=os.environ.get("USER", ""),
                    help="created_by / operator (default: $USER).")
    ap.add_argument("--date", default=datetime.date.today().isoformat(),
                    help="created date (default: today).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print planned ID + path without writing.")
    a = ap.parse_args()

    # 1) Parent must exist.
    parent_path, parent_meta = find_record(a.parent_id)
    if parent_path is None:
        print(f"❌ parent record not found: {a.parent_id}")
        sys.exit(1)

    # 2) Validate CODE shape + registration.
    code = a.code.upper()
    if not re.match(r"^[A-Z]{2,4}$", code):
        print(f"❌ CODE '{a.code}' invalid: must be 2-4 uppercase letters.")
        sys.exit(1)
    if V.SEGMENT_CODES and code not in V.SEGMENT_CODES:
        print(f"⚠️  CODE '{code}' is not registered in vocab.md — consider adding it under the appropriate group.")

    # 3) Depth check: derived_id = parent + '-' + CODE + instance, ≤ 2 segments after anchor.
    instance = a.instance
    if instance and not re.match(r"^\d+$", instance):
        print(f"❌ instance '{instance}' invalid: must be digits.")
        sys.exit(1)
    derived_id = f"{a.parent_id}-{code}{instance}"

    parsed = H.parse(derived_id)
    if parsed is None:
        print(f"❌ derived ID '{derived_id}' is not a valid compound ID (does it match a known prefix?).")
        sys.exit(1)
    if parsed["depth"] > 2:
        print(f"❌ derived ID '{derived_id}' would be depth {parsed['depth']} "
              f"(hierarchy.md caps at 2 segments after the anchor). "
              f"Mint a fresh L1 anchor instead, and record all parents in derived_from.")
        sys.exit(1)

    # 4) Resolve target type + spec + template.
    target_type = a.type
    spec = R.TYPES.get(target_type)
    if not spec:
        print(f"❌ unknown --type '{target_type}'. Known: {', '.join(sorted(R.TYPES))}")
        sys.exit(1)
    tpl = os.path.join(ROOT, "templates", f"{spec['template']}.md")
    if not os.path.exists(tpl):
        print(f"❌ missing template: {os.path.relpath(tpl, ROOT)}")
        sys.exit(1)

    # 5) Build content: set id / created / created_by / derived_from + inferred fields.
    content = open(tpl, encoding="utf-8").read().replace("{DATE}", a.date)
    content = re.sub(r"^id:.*$", f"id: {derived_id}", content, count=1, flags=re.M)
    if a.name and re.search(r"^name:\s*$", content, re.M):
        content = fm.set_field(content, "name", a.name)
    who = spec.get("who_field")
    if who and a.by and re.search(rf"^{who}:\s*$", content, re.M):
        content = fm.set_field(content, who, a.by)
    if re.search(r"^created:\s*$", content, re.M):
        content = fm.set_field(content, "created", a.date)
    content = fm.set_field(content, "derived_from", [a.parent_id])
    content = apply_inference(content, code, parent_meta or {}, target_type)

    slug = slugify(a.name)
    path = target_path(spec, derived_id, slug)

    if a.dry_run:
        print(f"[dry-run] parent      : {a.parent_id}  ({os.path.relpath(parent_path, ROOT)})")
        print(f"[dry-run] derived ID  : {derived_id}   (depth={parsed['depth']})")
        print(f"[dry-run] target file : {os.path.relpath(path, ROOT)}")
        print(f"[dry-run] type/template: {target_type} -> templates/{spec['template']}.md")
        return

    if os.path.exists(path):
        print(f"❌ target already exists: {os.path.relpath(path, ROOT)}")
        sys.exit(1)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(content)

    print(f"✅ Created {derived_id}  (parent={a.parent_id}, type={target_type})")
    print(f"   → {os.path.relpath(path, ROOT)}")
    print("   Next: fill in body → python tools/index.py → python tools/validate.py")


if __name__ == "__main__":
    main()
