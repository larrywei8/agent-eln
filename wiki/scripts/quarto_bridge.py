#!/usr/bin/env python3
"""Quarto <-> wiki bridge helpers.

The bridge is intentionally one-way for writes:
- Quarto may cite/export stable wiki snapshots.
- Durable Quarto findings are staged into raw/inbox/project-notes/.
- Only the normal ingest operation writes wiki pages.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/home/workspace/knowledge")
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\((<[^>]+>|[^)\s]+)(?:\s+\"[^\"]*\")?\)")
PROMOTE_RE = re.compile(r"<!--\s*wiki-promote:\s*start\s*-->(.*?)<!--\s*wiki-promote:\s*end\s*-->", re.DOTALL | re.I)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def today() -> str:
    return utc_now().strftime("%Y%m%d")


def iso_now() -> str:
    return utc_now().isoformat(timespec="seconds").replace("+00:00", "Z")


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return slug[:90] or "quarto-finding"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def sha256_12(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def parse_frontmatter(text: str) -> dict[str, object]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    data: dict[str, object] = {}
    current = None
    for raw in text[4:end].strip().splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("  - ") and current:
            data.setdefault(current, [])
            if isinstance(data[current], list):
                data[current].append(line[4:].strip().strip('"').strip("'"))
            continue
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            current = key
            if not value:
                data[key] = []
            elif value.startswith("[") and value.endswith("]"):
                data[key] = [v.strip().strip('"').strip("'") for v in value[1:-1].split(",") if v.strip()]
            else:
                data[key] = value.strip('"').strip("'")
    return data


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---", 4)
    if end == -1:
        return text
    return text[end + 4:].lstrip("\n")


def extract_title(path: Path, text: str) -> str:
    fm = parse_frontmatter(text)
    title = fm.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    m = re.search(r"^#\s+(.+)$", strip_frontmatter(text), re.MULTILINE)
    if m:
        return m.group(1).strip()
    return path.stem.replace("-", " ").replace("_", " ").title()


def resolve_wiki_href(qmd_path: Path, root: Path, href: str) -> str | None:
    href = href.strip()
    if href.startswith("<") and href.endswith(">"):
        href = href[1:-1].strip()
    href = href.split("#", 1)[0]
    if not href or re.match(r"^[a-z][a-z0-9+.-]*:", href, re.I):
        return None
    root_resolved = root.resolve()
    wiki_dir = (root / "wiki").resolve()
    candidates: list[Path] = []
    if href.startswith("wiki/"):
        candidates.append(root / href)
    else:
        raw_path = Path(href)
        if raw_path.is_absolute():
            candidates.append(raw_path)
        else:
            candidates.append((qmd_path.parent / raw_path).resolve())
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        try:
            rel_wiki = resolved.relative_to(wiki_dir)
            return f"wiki/{rel_wiki.as_posix()}"
        except ValueError:
            pass
        try:
            rel_root = resolved.relative_to(root_resolved)
            if rel_root.as_posix().startswith("wiki/"):
                return rel_root.as_posix()
        except ValueError:
            pass
    return None


def cited_pages(qmd_path: Path, root: Path) -> list[str]:
    text = qmd_path.read_text(encoding="utf-8")
    found = []
    seen = set()
    for match in LINK_RE.finditer(text):
        rel = resolve_wiki_href(qmd_path, root, match.group(1))
        if rel and rel not in seen and (root / rel).exists():
            seen.add(rel)
            found.append(rel)
    return found


def cite_key(rel: str) -> str:
    return "wiki-" + slugify(Path(rel).stem)


def export_citations(root: Path, qmd: Path) -> Path:
    qmd = qmd.resolve()
    out_dir = root / "outputs/quarto-bridge" / slugify(qmd.stem)
    snapshot_dir = out_dir / "cited-pages"
    pages = cited_pages(qmd, root)
    manifest = {
        "schema": 1,
        "generated_at": iso_now(),
        "qmd_path": str(qmd),
        "qmd_sha256_12": sha256_12(qmd),
        "cited_pages": [],
    }
    bib_entries = []
    for rel in pages:
        page_path = root / rel
        text = page_path.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)
        title = extract_title(page_path, text)
        key = cite_key(rel)
        snapshot_name = f"{key}.md"
        snapshot_text = "\n".join([
            "---",
            f"source_wiki_path: {rel}",
            f"source_sha256_12: {sha256_12(page_path)}",
            f"exported_at: {iso_now()}",
            "---",
            "",
            text.rstrip(),
            "",
        ])
        atomic_write(snapshot_dir / snapshot_name, snapshot_text)
        manifest["cited_pages"].append({
            "cite_key": key,
            "title": title,
            "wiki_path": rel,
            "snapshot": f"cited-pages/{snapshot_name}",
            "updated": fm.get("updated", ""),
            "confidence": fm.get("confidence", ""),
            "sha256_12": sha256_12(page_path),
        })
        safe_title = title.replace("{", "").replace("}", "")
        bib_entries.append("\n".join([
            f"@misc{{{key},",
            f"  title = {{{safe_title}}},",
            f"  howpublished = {{{rel}}},",
            f"  note = {{the wiki snapshot exported {today()}; source hash {sha256_12(page_path)}}},",
            "}",
            "",
        ]))
    atomic_write(out_dir / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    atomic_write(out_dir / "wiki-citations.bib", "\n".join(bib_entries))
    report_lines = [
        f"# Quarto Wiki Citation Export - {qmd.name}",
        "",
        f"- QMD: `{qmd}`",
        f"- Cited wiki pages: {len(pages)}",
        f"- Manifest: `{(out_dir / 'manifest.json').relative_to(root).as_posix()}`",
        f"- BibTeX: `{(out_dir / 'wiki-citations.bib').relative_to(root).as_posix()}`",
        "",
        "## Pages",
        "",
    ]
    report_lines.extend(
        f"- `{item['cite_key']}` -> [{item['title']}]({item['wiki_path']})"
        for item in manifest["cited_pages"]
    )
    if not pages:
        report_lines.append("- none")
    atomic_write(out_dir / "README.md", "\n".join(report_lines) + "\n")
    print(f"Exported {len(pages)} cited wiki page(s) to {out_dir}")
    return out_dir


def extract_promote_block(qmd: Path) -> str:
    text = qmd.read_text(encoding="utf-8")
    m = PROMOTE_RE.search(text)
    if m:
        return re.sub(r"\n{3,}", "\n\n", m.group(1).strip())
    heading = re.search(r"^##+\s+Durable Finding.*?$([\s\S]+?)(?:^##+\s+|\Z)", text, re.MULTILINE | re.I)
    if heading:
        return heading.group(1).strip()
    raise SystemExit("No durable finding block found. Add <!-- wiki-promote: start --> ... <!-- wiki-promote: end -->.")


def promote_finding(root: Path, qmd: Path, title: str | None) -> Path:
    qmd = qmd.resolve()
    export_dir = export_citations(root, qmd)
    finding = extract_promote_block(qmd)
    qmd_text = qmd.read_text(encoding="utf-8")
    qmd_title = title or extract_title(qmd, qmd_text)
    slug = slugify(qmd_title)
    out = root / "raw/inbox/project-notes" / f"{today()}-{slug}.md"
    if out.exists():
        existing = parse_frontmatter(out.read_text(encoding="utf-8", errors="replace"))
        if str(existing.get("status", "")).strip().lower() == "ingested":
            print(f"Promoted finding already ingested; leaving inbox note unchanged: {out}")
            return out
    qmd_rel = os.path.relpath(qmd, root)
    summary_base = slug if slug.startswith("quarto-") else f"quarto-{slug}"
    summary_slug = f"{summary_base}-{today()}.md"
    body = "\n".join([
        "---",
        f"title: {qmd_title}",
        "source_type: quarto-finding",
        "status: inbox",
        "ingest_priority: normal",
        f"source_qmd: {qmd}",
        f"source_qmd_rel: {qmd_rel}",
        f"source_qmd_sha256_12: {sha256_12(qmd)}",
        f"citation_export: {(export_dir / 'manifest.json').relative_to(root).as_posix()}",
        f"suggested_summary: wiki/summaries/{summary_slug}",
        f"created: {utc_now().date().isoformat()}",
        "---",
        "",
        f"# {qmd_title}",
        "",
        "## Provenance",
        "",
        f"- Source QMD: `{qmd}`",
        f"- Source digest: `{sha256_12(qmd)}`",
        f"- Citation export: `{(export_dir / 'manifest.json').relative_to(root).as_posix()}`",
        "- Promotion rule: staged from Quarto into `raw/inbox/project-notes/`; an agent must ingest before any wiki page is written.",
        "",
        "## Durable conclusion",
        "",
        finding,
        "",
    ])
    atomic_write(out, body)
    print(f"Promoted durable finding to inbox: {out}")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Export cited wiki pages and stage Quarto findings for wiki ingest.")
    parser.add_argument("--root", default=str(ROOT))
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export-citations")
    export.add_argument("qmd")
    promote = sub.add_parser("promote-finding")
    promote.add_argument("qmd")
    promote.add_argument("--title")
    args = parser.parse_args()
    root = Path(args.root)
    qmd = Path(args.qmd)
    if args.command == "export-citations":
        export_citations(root, qmd)
        return
    if args.command == "promote-finding":
        promote_finding(root, qmd, args.title)
        return
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
