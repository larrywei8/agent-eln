#!/usr/bin/env python3
"""Scaffolding: allocate the next ID, create a record from a template, and **write directly to the correct directory**.

Usage:
  python tools/new.py plasmid --name "lentiCRISPRv2 sgTP53" --by alice
  python tools/new.py experiment-drylab --slug guide-rna-library-design --title "..." --by me
  python tools/new.py dataset --name "RNA-seq batch1"
  python tools/new.py meeting --date 2026-07-08 --title "group meeting"
  python tools/new.py plasmid --print        # Print content only, do not write to disk (old behavior)
  python tools/new.py experiment-drylab --slug foo --dry-run   # Print what would be created, do not write

For experiment types, in addition to the md card itself, it **automatically creates a same-named artifact folder skeleton**:
  {ID}-{SLUG}/{inputs, scripts, outputs, figures/exploratory, figures/final, runs}/
plus a README.md rendered from templates/exp-artifacts-readme.md.

Type information all comes from tools/registry.py (single source of truth). The next ID is computed from the actual
frontmatter of same-type records in the library, so it is not confused by IDs mentioned in body text.
"""
import os, sys, re, datetime, argparse
sys.path.insert(0, os.path.dirname(__file__))
import fm
from fm import parse
import registry as R
import records as record_api

ROOT = R.ROOT

EXP_FOLDER_SKELETON = [
    "inputs/",
    "scripts/",
    "outputs/",
    "figures/exploratory/",
    "figures/final/",
    "runs/",
]

def resolve_type(arg):
    if arg in R.TYPES: return arg, R.TYPES[arg], arg
    if arg in R.TEMPLATE_ALIAS:                      # experiment-wetlab / -drylab
        t = R.TEMPLATE_ALIAS[arg]; return t, R.TYPES[t], arg
    return None, None, None

def existing_ids_of(t):
    return record_api.existing_ids(t, ROOT)

def next_id(t, spec, date):
    style, year, pfx = spec["id_style"], date[:4], spec["prefix"]
    ids = existing_ids_of(t)
    if style in ("seq4", "year-seq4"):
        rgx = re.compile(R.id_regex(spec))
        n = max([int(m.group(1)) for i in ids for m in [rgx.search(i)] if m] + [0])
        nxt = n + 1
        if nxt >= 10000:
            sys.stderr.write(
                f"⚠️  {pfx}: sequence reached {nxt}, exceeds 4-digit padding "
                f"(will emit {pfx}-{nxt} rather than -0000-padded); consider migrating to seq5 in Phase 4\n"
            )
        return f"{pfx}-{nxt:04d}" if style == "seq4" else f"{pfx}-{year}-{nxt:04d}"
    if style == "date-nn":
        day = [i for i in ids if i.startswith(f"{pfx}-{date}-")]
        nn = max([int(i.rsplit("-", 1)[-1]) for i in day] + [0]) + 1
        return f"{pfx}-{date}-{nn:02d}"
    if style == "date":
        return f"{pfx}-{date}"
    return f"{pfx}-{date}"

def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:60]

def target_path(t, spec, rid, slug):
    folder, container = spec["folder"], spec["container"]
    if t in ("experiment", "daily-summary"):          # Archive by date
        date = rid.split("-", 1)[1][:10] if t == "experiment" else rid.split("-", 1)[1]
        d = os.path.join(ROOT, folder, date[:4], date)
        # experiment allows a slug suffix so you can see what was done at a glance; daily-summary stays flat (one per day)
        if t == "experiment" and slug:
            return os.path.join(d, f"{rid}-{slug}.md")
        return os.path.join(d, f"{rid}.md")
    if container == "dir":
        name = f"{rid}-{slug}" if slug else rid
        return os.path.join(ROOT, folder, name, "card.md")
    name = f"{rid}-{slug}" if slug else rid
    return os.path.join(ROOT, folder, f"{name}.md")

def exp_artifact_folder(md_path, rid, slug):
    """Given the md path, return the sibling artifact-folder path (same name minus .md)."""
    d = os.path.dirname(md_path)
    fname = f"{rid}-{slug}" if slug else rid
    return os.path.join(d, fname)

def render_exp_readme(rid, slug, title):
    tpl = os.path.join(ROOT, "templates", "exp-artifacts-readme.md")
    if not os.path.exists(tpl):
        return None
    body = open(tpl, encoding="utf-8").read()
    return (body
            .replace("{ID}", rid)
            .replace("{SLUG}", slug or "")
            .replace("{TITLE}", title or ""))

def set_field(txt, key, val):
    """Thin wrapper around fm.set_field (kept for backward-compat local use)."""
    return fm.set_field(txt, key, val)

ap = argparse.ArgumentParser()
ap.add_argument("type")
ap.add_argument("--name", default="")
ap.add_argument("--title", default="")
ap.add_argument("--slug", default="", help="Explicit short slug, appended to file/folder name (takes precedence over slugs derived from --name/--title)")
ap.add_argument("--by", default=os.environ.get("AGENT_ELN_USER") or os.environ.get("USER") or "me")
ap.add_argument("--date", default=datetime.date.today().isoformat())
ap.add_argument("--print", dest="just_print", action="store_true", help="Print md content only, do not write to disk")
ap.add_argument("--dry-run", dest="dry_run", action="store_true",
                help="Print the paths + skeleton that would be created, do not write; better than --print "
                     "for confirming the path/slug is correct")
ap.add_argument("--no-folder", dest="no_folder", action="store_true",
                help="experiment: do not auto-create the same-named artifact folder skeleton (created by default)")
a = ap.parse_args()

t, spec, tmpl_name = resolve_type(a.type)
if not spec:
    print("Unknown type:", a.type, "\nAvailable:", ", ".join(sorted(R.TYPES))); sys.exit(1)

tpl = os.path.join(ROOT, "templates", f"{spec['template'] if tmpl_name in R.TYPES else tmpl_name}.md")
if not os.path.exists(tpl):
    print("Missing template:", os.path.relpath(tpl, ROOT)); sys.exit(1)

rid = next_id(t, spec, a.date)
content = open(tpl, encoding="utf-8").read().replace("{DATE}", a.date)
content = re.sub(r"^id:.*$", f"id: {rid}", content, count=1, flags=re.M)
# Fill in name / title / who / created|date
if a.name and re.search(r"^name:\s*$", content, re.M):   content = set_field(content, "name", a.name)
if a.title and re.search(r"^title:\s*$", content, re.M): content = set_field(content, "title", a.title)
who = spec.get("who_field")
if who and a.by and re.search(rf"^{who}:\s*$", content, re.M): content = set_field(content, who, a.by)
if re.search(r"^created:\s*$", content, re.M):           content = set_field(content, "created", a.date)

if a.just_print:
    print(f"# New ID: {rid}\n"); print(content); sys.exit(0)

slug = slugify(a.slug or a.name or a.title)
path = target_path(t, spec, rid, slug)
folder_path = exp_artifact_folder(path, rid, slug) if t == "experiment" else None
create_folder = (t == "experiment") and (not a.no_folder)

if a.dry_run:
    print(f"[dry-run] would allocate ID:   {rid}")
    print(f"[dry-run] would create card: {os.path.relpath(path, ROOT)}")
    if create_folder:
        print(f"[dry-run] would create artifact folder: {os.path.relpath(folder_path, ROOT)}/")
        for sub in EXP_FOLDER_SKELETON:
            print(f"[dry-run]   └─ {sub}")
        print(f"[dry-run]   └─ README.md")
    print("[dry-run] Nothing written to disk. Add --slug/--title to adjust, or drop --dry-run to actually create.")
    sys.exit(0)

if os.path.exists(path):
    print("Target already exists, aborted:", os.path.relpath(path, ROOT)); sys.exit(1)
os.makedirs(os.path.dirname(path), exist_ok=True)
record_api.atomic_write(path, content)

print(f"✅ Created {rid}  ({spec['label']})")
print(f"   → {os.path.relpath(path, ROOT)}")

# experiment: also create the same-named artifact folder skeleton + README
if create_folder:
    if os.path.exists(folder_path):
        print(f"   ⚠️  Artifact folder already exists, skipping skeleton creation: {os.path.relpath(folder_path, ROOT)}/")
    else:
        for sub in EXP_FOLDER_SKELETON:
            os.makedirs(os.path.join(folder_path, sub), exist_ok=True)
        readme = render_exp_readme(rid, slug, a.title or a.name)
        if readme is not None:
            with open(os.path.join(folder_path, "README.md"), "w", encoding="utf-8") as f:
                f.write(readme)
        print(f"   → {os.path.relpath(folder_path, ROOT)}/  (inputs/ scripts/ outputs/ figures/ runs/ + README.md)")

print("   Next: fill in fields/body → python tools/index.py → python tools/validate.py")
