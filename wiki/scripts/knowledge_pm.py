#!/usr/bin/env python3
import argparse
import fnmatch
import json
import math
import re
import shutil
import subprocess
import sys
import tarfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from textwrap import shorten


# Default to the wiki module inside agent-eln (this script lives at wiki/scripts/).
# Override with --root when running against a different wiki repo.
ROOT = Path(__file__).resolve().parent.parent
# Override with $LLM_WIKI_ANYGEN_LINT if the llm-wiki-anygen skill lives elsewhere.
import os as _os
LINT = Path(_os.environ.get(
    "LLM_WIKI_ANYGEN_LINT",
    str(Path.home() / "Skills/llm-wiki-anygen/scripts/lint_wiki.py"),
))
INBOX_BUCKETS = {
    "authored": ("author-produced material", "known known"),
    "unread-papers": ("unread papers for AI reading", "known unknown"),
    "web-saves": ("saved web articles and social captures", "known unknown"),
    "books-highlights": ("book highlights and reading screenshots", "known known / unknown known"),
    "talks-workshops": ("talks, workshops, and teaching material", "known known"),
    "project-notes": ("active project notes", "known known"),
    "lab-protocols": ("protocols, manuals, SOPs, and vendor docs", "known unknown"),
}
GENERIC_TAGS = {
    "person", "paper", "nature", "science", "cell", "wechat", "xiaohongshu", "github",
    "source", "summary", "article", "repository", "tool", "method", "note",
}


def parse_frontmatter(text):
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    block = text[4:end].strip().splitlines()
    data = {}
    current = None
    for raw in block:
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("  - ") and current:
            data.setdefault(current, []).append(line[4:].strip().strip('"'))
            continue
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            current = key
            if value:
                data[key] = value.strip('"')
            else:
                data[key] = []
    return data


def wiki_target(raw):
    if not isinstance(raw, str):
        return None
    target = raw.strip()
    target = target.strip('"').strip("'")
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if target.startswith("wiki/"):
        return target
    return None


def wiki_targets(raw):
    if isinstance(raw, list):
        values = raw
    elif isinstance(raw, str):
        stripped = raw.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            values = [part.strip() for part in stripped[1:-1].split(",")]
        elif stripped:
            values = [stripped]
        else:
            values = []
    else:
        values = []
    return [target for value in values if (target := wiki_target(str(value)))]


SEMANTIC_EDGE_TYPES = {
    "extends",
    "alternative_to",
    "depends_on",
    "avoids",
    "outperforms",
    "limited_by",
    "safety_concern",
    "enables",
}
SEMANTIC_EDGE_RE = re.compile(r"<!--\s*edge:\s*([a-z_]+)\s*->\s*(.+?)(?:\s*\|\s*(.*?))?\s*-->", re.DOTALL)


def extract_semantic_edges(text):
    edges = []
    for match in SEMANTIC_EDGE_RE.finditer(text):
        kind = match.group(1).strip()
        target = wiki_target(match.group(2).strip())
        evidence = re.sub(r"\s+", " ", (match.group(3) or "semantic-edge-comment").strip())
        if kind in SEMANTIC_EDGE_TYPES and target:
            edges.append({"kind": kind, "target": target, "evidence": evidence.replace("\t", " ")})
    return edges


def load_pages(root):
    pages = []
    for path in sorted((root / "wiki").rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        title = fm.get("title") or (title_match.group(1).strip() if title_match else path.stem)
        links = []
        for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
            target = wiki_target(match.group(1))
            if target:
                links.append(target)
        tags = fm.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        sources = fm.get("sources", [])
        if isinstance(sources, str):
            sources = [sources]
        aliases = fm.get("aliases", [])
        if isinstance(aliases, str):
            aliases = [aliases]
        pages.append({
            "path": rel,
            "title": title,
            "type": fm.get("type", infer_type(rel)),
            "created": fm.get("created", ""),
            "updated": fm.get("updated", ""),
            "last_reviewed": fm.get("last_reviewed", ""),
            "confidence": fm.get("confidence", ""),
            "tags": [tag for tag in tags if tag],
            "sources": [source for source in sources if source],
            "aliases": [a for a in aliases if a],
            "supersedes": wiki_targets(fm.get("supersedes")),
            "superseded_by": wiki_target(fm.get("superseded_by", "")),
            "semantic_edges": extract_semantic_edges(text),
            "links": links,
            "words": len(re.findall(r"\w+", text)),
        })
    return pages


def infer_type(rel):
    if rel.startswith("wiki/concepts/"):
        return "concept"
    if rel.startswith("wiki/entities/"):
        return "entity"
    if rel.startswith("wiki/summaries/"):
        return "summary"
    return "page"


def load_graph_stats(root):
    path = root / "graph/stats.graph"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def collect_questions(root):
    questions = []
    for path in [root / "AGENTS.md", root / "wiki/index.md"]:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped.startswith("- ") and "?" in stripped:
                questions.append(stripped[2:])
            elif stripped.startswith("- [ ]") and len(stripped) > 5:
                questions.append(stripped[5:].strip())
    seen = set()
    out = []
    for q in questions:
        key = re.sub(r"\s+", " ", q).strip()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def collect_research_gaps(root):
    path = root / "AGENTS.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^## Research gaps\s*$([\s\S]+?)(?:^## |\Z)", text, re.MULTILINE)
    if not match:
        return []
    gaps = []
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if stripped.startswith("- [ ]"):
            gaps.append(stripped[5:].strip())
        elif stripped.startswith("- "):
            gaps.append(stripped[2:].strip())
    return [gap for gap in gaps if gap]


def collect_lint_issues(root):
    issues_path = root / "graph/issues.graph"
    if not issues_path.exists():
        return {}
    try:
        return json.loads(issues_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def run_lint(root):
    proc = subprocess.run(
        ["python3", str(LINT), str(root)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode, proc.stdout


def recent_logs(root, limit=10):
    logs = sorted((root / "log").glob("*.md"), reverse=True)
    rows = []
    for path in logs[:limit]:
        text = path.read_text(encoding="utf-8", errors="replace")
        headings = [line.strip("# ").strip() for line in text.splitlines() if line.startswith("## ")]
        rows.append((path.name, headings[:5]))
    return rows


def read_small_text(path, max_chars=2400):
    if path.stat().st_size > max_chars * 4:
        return ""
    if path.suffix.lower() not in {".md", ".txt", ".csv", ".tsv", ".json", ".yaml", ".yml"}:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except OSError:
        return ""


def collect_inbox_items(root):
    inbox = root / "raw/inbox"
    items = []
    if not inbox.exists():
        return items
    for path in sorted(inbox.rglob("*")):
        if not path.is_file() or path.name in {".gitkeep", "README.md"}:
            continue
        rel = path.relative_to(root).as_posix()
        parts = path.relative_to(inbox).parts
        bucket = parts[0] if parts else "uncategorized"
        text = read_small_text(path)
        fm = parse_frontmatter(text) if text else {}
        headings = re.findall(r"^#{1,3}\s+(.+)$", text, re.MULTILINE)[:5] if text else []
        try:
            attempts = int(str(fm.get("attempts", "0")).strip() or "0")
        except ValueError:
            attempts = 0
        items.append({
            "path": rel,
            "bucket": bucket,
            "bucket_label": INBOX_BUCKETS.get(bucket, ("uncategorized source", "uncategorized"))[0],
            "rumsfeld": INBOX_BUCKETS.get(bucket, ("uncategorized source", "uncategorized"))[1],
            "suffix": path.suffix.lower() or "(none)",
            "size": path.stat().st_size,
            "source_type": fm.get("source_type", bucket),
            "priority": fm.get("ingest_priority", "normal"),
            "source_date": fm.get("source_date", ""),
            "status": str(fm.get("status", "inbox")).strip().lower() or "inbox",
            "attempts": attempts,
            "last_error": str(fm.get("last_error", "")).strip(),
            "headings": headings,
            "title_hint": title_hint(path, fm, headings),
        })
    return items


def title_hint(path, fm, headings):
    if fm.get("title"):
        return str(fm["title"])
    if headings:
        return headings[0]
    return path.stem.replace("-", " ").replace("_", " ").strip().title()


def slugify(value):
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return value[:80] or "source"


def format_size(num):
    for unit in ["B", "KB", "MB", "GB"]:
        if num < 1024 or unit == "GB":
            return f"{num:.1f} {unit}" if unit != "B" else f"{num} B"
        num /= 1024


def write_discovery(root, pages, stamp):
    tag_counts = Counter(tag for page in pages for tag in page["tags"])
    tag_pages = defaultdict(list)
    co = Counter()
    for page in pages:
        for tag in page["tags"]:
            tag_pages[tag].append(page)
        tags = sorted(set(page["tags"]))
        for i, a in enumerate(tags):
            for b in tags[i + 1:]:
                co[(a, b)] += 1

    lines = [
        f"# Discovery Report — {stamp}",
        "",
        "This report surfaces repeated themes and cross-domain connections already present in the wiki.",
        "",
        "## Strongest Themes",
        "",
    ]
    for tag, count in tag_counts.most_common(20):
        sample = ", ".join(f"[{p['title']}]({p['path']})" for p in tag_pages[tag][:4])
        lines.append(f"- **{tag}** ({count} pages): {sample}")

    lines.extend(["", "## Repeated Cross-Tag Links", ""])
    for (a, b), count in co.most_common(25):
        if count >= 2:
            lines.append(f"- **{a} + {b}** appears together on {count} pages")

    hub_pages = sorted(pages, key=lambda p: len(p["links"]), reverse=True)[:15]
    lines.extend(["", "## Current Hubs", ""])
    for page in hub_pages:
        lines.append(f"- [{page['title']}]({page['path']}) — {len(page['links'])} outgoing wiki links")

    path = root / f"outputs/discovery/{stamp}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_hidden_patterns(root, pages, stamp):
    tag_pages = defaultdict(list)
    title_terms = Counter()
    bridge_examples = defaultdict(list)
    co = Counter()

    categories = {
        "AI/agent infrastructure": ("ai", "agent", "rag", "llm", "memory", "skill", "automation", "coding", "knowledge"),
        "biology and genomics": ("bio", "genom", "single-cell", "gene", "protein", "perturb", "rna", "cell"),
        "genome editing": ("editing", "crispr", "prime", "base-editing", "recombinase", "delivery"),
        "wet-lab protocols": ("lab", "protocol", "facs", "nuclei", "antibody", "rna-extraction", "vendor"),
        "research tooling": ("benchmark", "workflow", "tool", "github", "reproduc", "evaluation", "harness"),
    }

    for page in pages:
        tags = set(page["tags"])
        for tag in tags:
            tag_pages[tag].append(page)
        useful_tags = sorted(tag for tag in tags if tag not in GENERIC_TAGS)
        for i, a in enumerate(useful_tags):
            for b in useful_tags[i + 1:]:
                co[(a, b)] += 1
        for term in re.findall(r"[A-Za-z][A-Za-z0-9-]{3,}", page["title"].lower()):
            if term not in {"with", "from", "using", "into", "research", "analysis"}:
                title_terms[term] += 1
        matched = []
        for label, needles in categories.items():
            if any(any(needle in tag for needle in needles) for tag in tags):
                matched.append(label)
        for i, a in enumerate(sorted(set(matched))):
            for b in sorted(set(matched))[i + 1:]:
                bridge_examples[(a, b)].append(page)

    lines = [
        f"# Hidden-Pattern Report — {stamp}",
        "",
        "This report is the weekly `unknown known` layer: recurring interests that are already visible in the wiki but may not be obvious from single-page reading.",
        "",
        "## Pattern Hypotheses",
        "",
    ]
    if bridge_examples:
        for (a, b), examples in sorted(bridge_examples.items(), key=lambda x: len(x[1]), reverse=True)[:12]:
            sample = ", ".join(f"[{p['title']}]({p['path']})" for p in examples[:3])
            lines.append(f"- **{a} x {b}** — {len(examples)} pages. Examples: {sample}")
    else:
        lines.append("- No cross-domain pattern passed the current conservative heuristic.")

    lines.extend(["", "## Strong Repeated Tag Bridges", ""])
    for (a, b), count in co.most_common(20):
        if count >= 2:
            lines.append(f"- **{a} + {b}** appears together on {count} pages.")

    lines.extend(["", "## Repeated Vocabulary In Page Titles", ""])
    for term, count in title_terms.most_common(25):
        if count >= 2:
            lines.append(f"- **{term}** appears in {count} page titles.")

    lines.extend(["", "## Tags That Span Multiple Page Types", ""])
    for tag, linked_pages in sorted(tag_pages.items(), key=lambda x: len(x[1]), reverse=True)[:30]:
        types = sorted({p["type"] for p in linked_pages})
        if len(types) >= 2:
            lines.append(f"- **{tag}** spans {len(types)} page types ({', '.join(types)}) across {len(linked_pages)} pages.")

    lines.extend(["", "## Suggested Human Reflection Prompts", ""])
    lines.append("- Which recurring theme is actually central to current work, and which is just recent-input bias?")
    lines.append("- Which high-frequency theme should become a project, Skill, or deeper literature track?")
    lines.append("- Which bridge pattern is surprising enough to ask the wiki agent a follow-up query about?")

    path = root / f"outputs/hidden-patterns/{stamp}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_ingest_plan(root, inbox_items, stamp):
    lines = [
        f"# Ingest Plan — {stamp}",
        "",
        "This is the weekly source-intake plan for the wiki agent. It does not ingest by itself; it turns `raw/inbox/` into an ordered work queue with suggested wiki artifacts.",
        "",
        "## Queue Summary",
        "",
    ]
    # A file marked status: ingested is done but not yet archived out of inbox; it is
    # not part of the active work queue. Everything else (inbox / processing / failed /
    # blocked / deferred) still needs attention.
    active = [item for item in inbox_items if item["status"] != "ingested"]
    done_not_archived = [item for item in inbox_items if item["status"] == "ingested"]
    failed = [item for item in active if item["status"] in {"failed", "blocked"}]
    by_bucket = Counter(item["bucket"] for item in active)
    by_priority = Counter(item["priority"] for item in active)
    by_status = Counter(item["status"] for item in inbox_items)
    if active:
        lines.append(f"- Inbox files needing action: {len(active)}")
        for bucket, count in by_bucket.most_common():
            label, mode = INBOX_BUCKETS.get(bucket, ("uncategorized source", "uncategorized"))
            lines.append(f"- `{bucket}` ({mode}): {count} files — {label}")
        lines.append(f"- Priority distribution: {', '.join(f'{k}={v}' for k, v in sorted(by_priority.items()))}")
        lines.append(f"- Status distribution: {', '.join(f'{k}={v}' for k, v in sorted(by_status.items()))}")
    else:
        lines.append("- No inbox files are waiting for ingest.")
    if done_not_archived:
        lines.append(f"- {len(done_not_archived)} file(s) marked `ingested` still sitting in inbox — archive them into `raw/<format>/` per AGENTS.md.")

    if failed:
        lines.extend(["", "## Failed / blocked (needs a human decision)", "",
                      "These were attempted but did not complete. Resolve the blocker or retire the item; do not let them silently age out.", ""])
        for item in sorted(failed, key=lambda i: (-i["attempts"], i["path"])):
            err = item["last_error"] or "no error note recorded"
            lines.append(f"- `{item['path']}` — status `{item['status']}`, {item['attempts']} attempt(s): {shorten(err, width=200, placeholder='...')}")

    lines.extend(["", "## Recommended Ingest Order", ""])
    priority_rank = {"high": 0, "normal": 1, "low": 2}
    # Failed/blocked items drop to the bottom of the order; resolve them explicitly above.
    status_rank = {"failed": 1, "blocked": 1}
    ordered = sorted(active, key=lambda item: (status_rank.get(item["status"], 0), priority_rank.get(str(item["priority"]), 1), item["bucket"], item["path"]))
    for idx, item in enumerate(ordered[:100], start=1):
        summary_slug = slugify(item["title_hint"])
        headings = "; ".join(item["headings"][:3]) if item["headings"] else "no headings detected"
        status_note = "" if item["status"] == "inbox" else f" — status `{item['status']}`" + (f", {item['attempts']} attempt(s)" if item["attempts"] else "")
        lines.append(f"{idx}. `{item['path']}`{status_note}")
        lines.append(f"   - Type: {item['source_type']} / {item['rumsfeld']} / {format_size(item['size'])}")
        lines.append(f"   - Title hint: {item['title_hint']}")
        lines.append(f"   - Suggested summary: `wiki/summaries/{summary_slug}.md`")
        lines.append(f"   - Headings: {shorten(headings, width=180, placeholder='...')}")
        lines.append("   - wiki-agent action: read source, create/update summary, then link or create relevant concept/entity pages with confidence metadata.")
    if not ordered:
        lines.append("- No queued source files.")

    lines.extend(["", "## Reusable Ingest Prompt", ""])
    lines.append("```text")
    lines.append("Ingest the queued source from raw/inbox into the wiki using llm-wiki-anygen conventions. Read AGENTS.md and wiki/index.md first. Preserve the raw source, create or update a wiki/summaries page, update relevant concept/entity pages, update wiki/index.md, append log/YYYYMMDD.md, and run lint. Use standard wiki/ links and confidence metadata.")
    lines.append("```")

    path = root / f"outputs/ingest-plans/{stamp}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_literature_seeds(root, questions, gaps, pages, stamp):
    tag_counts = Counter(tag for page in pages for tag in page["tags"])
    seeds = []
    for text in gaps[:25] + questions[:20]:
        cleaned = re.sub(r"\[[^\]]+\]\([^)]+\)", "", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")
        if cleaned:
            seeds.append(cleaned)

    lines = [
        f"# Literature Seeds — {stamp}",
        "",
        "This report turns wiki gaps into search-ready literature prompts. It deliberately does not fabricate citations; use these as PubMed/Google Scholar/web_research queries before ingesting sources.",
        "",
        "## Search Queries From Explicit Gaps",
        "",
    ]
    seen = set()
    count = 0
    for seed in seeds:
        key = seed.lower()
        if key in seen:
            continue
        seen.add(key)
        count += 1
        lines.append(f"- {seed}")
        if count >= 35:
            break

    lines.extend(["", "## High-Frequency Themes Worth Literature Refresh", ""])
    useful_tags = [(tag, n) for tag, n in tag_counts.most_common() if tag not in GENERIC_TAGS]
    for tag, n in useful_tags[:20]:
        lines.append(f"- `{tag}` ({n} pages): search for recent review, benchmark, replication, or method-comparison papers.")

    lines.extend(["", "## Search Templates", ""])
    lines.append("- PubMed: `<topic> review 2024 2025 2026`")
    lines.append("- Google Scholar: `<method> benchmark comparison limitation`")
    lines.append("- BioRxiv/MedRxiv: `<topic> site:biorxiv.org 2026`")
    lines.append("- GitHub/tools: `<method> github documentation benchmark`")

    path = root / f"outputs/literature-seeds/{stamp}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_gap(root, pages, questions, lint_issues, stamp):
    no_conf = [p for p in pages if p["type"] in {"concept", "entity", "summary"} and not str(p["confidence"]).strip()]
    inbox_files = [
        p for p in (root / "raw/inbox").rglob("*")
        if p.is_file() and p.name not in {".gitkeep", "README.md"}
    ]

    lines = [
        f"# Gap Report — {stamp}",
        "",
        "This report converts open questions, weak provenance, and structural drift into a work queue.",
        "",
        "## Highest-Signal Open Questions",
        "",
    ]
    for q in questions[:35]:
        lines.append(f"- {q}")

    lines.extend(["", "## Intake Queue", ""])
    if inbox_files:
        now = datetime.now().timestamp()
        stale_items = []
        fresh_items = []
        for item in inbox_files[:50]:
            age_days = int((now - item.stat().st_mtime) / 86400)
            line = f"- `{item.relative_to(root).as_posix()}` ({age_days}d)"
            if age_days > 14:
                stale_items.append(line + " **STALE**")
            else:
                fresh_items.append(line)
        if stale_items:
            lines.append("### Stale (>14 days — triage or discard)")
            lines.append("")
            lines.extend(stale_items)
            lines.append("")
        if fresh_items:
            lines.append("### Fresh")
            lines.append("")
            lines.extend(fresh_items)
    else:
        lines.append("- No non-placeholder files currently in `raw/inbox/`.")

    lines.extend(["", "## Structural Gaps", ""])
    orphans = lint_issues.get("orphans", []) if lint_issues else []
    dead_links = lint_issues.get("deadLinks", []) if lint_issues else []
    missing_index = lint_issues.get("missingIndexEntries", []) if lint_issues else []
    if orphans or dead_links or missing_index:
        for item in orphans[:25]:
            lines.append(f"- Orphan page: `{item}`")
        for item in dead_links[:25]:
            lines.append(f"- Dead link: `{item}`")
        for item in missing_index[:25]:
            lines.append(f"- Missing index entry: `{item}`")
    else:
        lines.append("- No orphan, dead-link, or missing-index issues recorded by lint.")

    lines.extend(["", "## Missing Confidence Metadata", ""])
    if no_conf:
        for page in no_conf[:25]:
            lines.append(f"- [{page['title']}]({page['path']})")
    else:
        lines.append("- All generated pages checked here have confidence metadata.")

    lines.extend(["", "## Lint Snapshot", ""])
    has_lint_issue = False
    if lint_issues:
        for key, value in lint_issues.items():
            if value:
                has_lint_issue = True
                lines.append(f"- `{key}`: {len(value)}")
    if not has_lint_issue:
        lines.append("- No lint issues recorded in `graph/issues.graph`.")

    path = root / f"outputs/gaps/{stamp}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def parse_iso_date(value):
    if not value:
        return None
    text = str(value).strip().strip('"')
    if not text:
        return None
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def build_review_decay(pages):
    today = datetime.now(timezone.utc).date()
    review_pages = [p for p in pages if p["type"] in {"concept", "entity", "summary"}]
    stale_trusted = []
    review_priority = []
    never_reviewed = []
    for p in review_pages:
        last = parse_iso_date(p.get("last_reviewed"))
        try:
            conf = int(str(p.get("confidence", "")).strip())
        except (TypeError, ValueError):
            conf = None
        if last is None:
            never_reviewed.append((p, conf))
            continue
        age = (today - last).days
        if age >= 90 and conf is not None and conf >= 7:
            stale_trusted.append((p, conf, age))
        if age >= 30 and conf is not None and conf <= 5:
            review_priority.append((p, conf, age))
    out = []
    out.append("")
    out.append("### Stale-trusted (≥90 days, confidence ≥7)")
    out.append("")
    if stale_trusted:
        for p, conf, age in sorted(stale_trusted, key=lambda x: -x[2])[:25]:
            out.append(f"- [{p['title']}]({p['path']}) — conf {conf}, {age}d since review")
    else:
        out.append("- No trusted pages overdue for re-verification.")
    out.append("")
    out.append("### Review-priority-1 (≥30 days, confidence ≤5)")
    out.append("")
    if review_priority:
        for p, conf, age in sorted(review_priority, key=lambda x: -x[2])[:25]:
            out.append(f"- [{p['title']}]({p['path']}) — conf {conf}, {age}d since review")
    else:
        out.append("- No low-confidence pages overdue for review.")
    out.append("")
    out.append(f"### No review record yet ({len(never_reviewed)} pages)")
    out.append("")
    if never_reviewed:
        out.append("Bootstrap `last_reviewed: YYYY-MM-DD` on these pages as you re-touch them. Sample (oldest by `updated`):")
        sample = sorted(never_reviewed, key=lambda x: x[0].get("updated") or "")[:15]
        for p, conf in sample:
            updated = p.get("updated") or "?"
            conf_str = "?" if conf is None else str(conf)
            out.append(f"- [{p['title']}]({p['path']}) — conf {conf_str}, last updated {updated}")
    else:
        out.append("- Every reviewable page has a `last_reviewed` date.")
    return out


def archive_old_outputs(root, keep=8):
    archive_dir = root / "outputs/_archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    categories = {
        "discovery": ("md",),
        "gaps": ("md",),
        "evolution": ("md",),
        "typed-edges": ("tsv",),
        "ingest-plans": ("md",),
        "hidden-patterns": ("md",),
        "literature-seeds": ("md",),
    }
    dated_pattern = re.compile(r"^(\d{4})(\d{2})\d{2}\.")
    pending = defaultdict(list)
    for category, suffixes in categories.items():
        cat_dir = root / "outputs" / category
        if not cat_dir.exists():
            continue
        dated = []
        for path in cat_dir.iterdir():
            if not path.is_file():
                continue
            if not any(path.name.endswith("." + s) for s in suffixes):
                continue
            m = dated_pattern.match(path.name)
            if not m:
                continue
            dated.append(path)
        dated.sort(key=lambda p: p.name, reverse=True)
        for path in dated[keep:]:
            m = dated_pattern.match(path.name)
            month_key = f"{m.group(1)}-{m.group(2)}"
            pending[month_key].append((category, path))
    archived_count = 0
    for month_key, items in pending.items():
        tar_path = archive_dir / f"{month_key}.tar.gz"
        extract_dir = archive_dir / f".extract-{month_key}"
        if tar_path.exists():
            extract_dir.mkdir(parents=True, exist_ok=True)
            with tarfile.open(tar_path, "r:gz") as old_tar:
                old_tar.extractall(extract_dir)
        with tarfile.open(tar_path, "w:gz") as new_tar:
            if extract_dir.exists():
                for entry in sorted(extract_dir.rglob("*")):
                    if entry.is_file():
                        new_tar.add(entry, arcname=entry.relative_to(extract_dir).as_posix())
            for category, path in items:
                new_tar.add(path, arcname=f"{category}/{path.name}")
                path.unlink()
                archived_count += 1
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
    return archived_count, sorted(pending.keys())


def write_evolution(root, pages, graph_stats, stamp):
    by_type = Counter(page["type"] for page in pages)
    by_month = Counter((page["created"] or "unknown")[:7] for page in pages)
    confidence = Counter(str(page["confidence"]) if str(page["confidence"]).strip() else "missing" for page in pages)
    raw_count = sum(1 for p in (root / "raw").rglob("*") if p.is_file())
    file_count = sum(1 for p in (root / "files").rglob("*") if p.is_file()) if (root / "files").exists() else 0

    lines = [
        f"# Evolution Report — {stamp}",
        "",
        "This report tracks the wiki as a changing knowledge state.",
        "",
        "## Current Size",
        "",
        f"- Wiki pages: {len(pages)}",
        f"- Raw source files: {raw_count}",
        f"- Preserved file artifacts: {file_count}",
        f"- Graph pages: {graph_stats.get('pages', 'n/a')}",
        f"- Graph edges: {graph_stats.get('edges', 'n/a')}",
        f"- Dead links: {graph_stats.get('deadLinks', 'n/a')}",
        f"- Orphans: {graph_stats.get('orphans', 'n/a')}",
        "",
        "## Page Types",
        "",
    ]
    for kind, count in by_type.most_common():
        lines.append(f"- {kind}: {count}")

    lines.extend(["", "## Created-By-Month Distribution", ""])
    for month, count in sorted(by_month.items(), reverse=True):
        lines.append(f"- {month}: {count}")

    lines.extend(["", "## Confidence Distribution", ""])
    for score, count in sorted(confidence.items(), key=lambda x: x[0]):
        lines.append(f"- {score}: {count}")

    lines.extend(["", "## Review Decay", ""])
    review_lines = build_review_decay(pages)
    lines.extend(review_lines)

    lines.extend(["", "## Recent Log Activity", ""])
    for name, headings in recent_logs(root):
        compact = "; ".join(headings) if headings else "no operation headings"
        lines.append(f"- `{name}`: {compact}")

    path = root / f"outputs/evolution/{stamp}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_typed_edges(root, pages, stamp):
    path = root / "outputs/typed-edges/edges.tsv"
    lines = ["source\tedge_type\ttarget\tevidence"]
    seen_supersession_edges = set()
    for page in pages:
        for link in sorted(set(page["links"])):
            lines.append(f"{page['path']}\tlinks_to\t{link}\tmarkdown-link")
        for source in page["sources"]:
            lines.append(f"{source}\tsource_for\t{page['path']}\tfrontmatter")
        for superseded in page["supersedes"]:
            edge = (page["path"], superseded)
            if edge not in seen_supersession_edges:
                lines.append(f"{page['path']}\tsupersedes\t{superseded}\tfrontmatter")
                seen_supersession_edges.add(edge)
        if page["superseded_by"]:
            edge = (page["superseded_by"], page["path"])
            if edge not in seen_supersession_edges:
                lines.append(f"{page['superseded_by']}\tsupersedes\t{page['path']}\tfrontmatter")
                seen_supersession_edges.add(edge)
        for edge in page["semantic_edges"]:
            lines.append(f"{page['path']}\t{edge['kind']}\t{edge['target']}\t{edge['evidence']}")
        for tag in page["tags"]:
            lines.append(f"{page['path']}\thas_tag\t{tag}\tfrontmatter")
        lines.append(f"{page['path']}\thas_type\t{page['type']}\tfrontmatter")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    dated = root / f"outputs/typed-edges/{stamp}.tsv"
    dated.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return path, dated


def write_dashboard(root, discovery, gap, evolution, edges, lint_code, extra_paths=None, mode="pm", archived_count=0, archived_months=None):
    extra_paths = extra_paths or {}
    archived_months = archived_months or []
    archive_line = (
        f"- Retention: archived {archived_count} file(s) into {', '.join(archived_months)}"
        if archived_count
        else "- Retention: nothing to archive this run"
    )
    text = "\n".join([
        "# Knowledge PM Dashboard",
        "",
        f"Mode: `{mode}`",
        "",
        "Latest generated reports:",
        "",
        f"- Discovery: [{discovery.name}]({discovery.relative_to(root).as_posix()})",
        f"- Gap: [{gap.name}]({gap.relative_to(root).as_posix()})",
        f"- Evolution: [{evolution.name}]({evolution.relative_to(root).as_posix()})",
        f"- Typed edges: [{edges.name}]({edges.relative_to(root).as_posix()})",
        *[f"- {label}: [{path.name}]({path.relative_to(root).as_posix()})" for label, path in extra_paths.items()],
        f"- Last lint exit code: `{lint_code}`",
        archive_line,
        "",
        "Run again with:",
        "",
        "```bash",
        "python3 knowledge/scripts/knowledge_pm.py --mode agent",
        "```",
        "",
    ])
    path = root / "outputs/dashboard.md"
    path.write_text(text, encoding="utf-8")
    return path


def append_log(root, stamp, paths, lint_code, mode="pm"):
    log_path = root / f"log/{stamp}.md"
    if log_path.exists():
        text = log_path.read_text(encoding="utf-8")
    else:
        text = f"# {stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}\n"
    now = datetime.now(timezone.utc).strftime("%H:%M")
    entry = [
        "",
        f"## [{now}] knowledge-pm | weekly second-brain reports ({mode})",
        "",
        "Generated discovery, gap, evolution, typed-edge, and optional agent-control reports for the wiki PM loop.",
        "",
    ]
    for label, path in paths.items():
        entry.append(f"- {label}: `{path.relative_to(root).as_posix()}`")
    entry.append(f"- lint exit code: `{lint_code}`")
    entry.append("")
    log_path.write_text(text.rstrip() + "\n" + "\n".join(entry), encoding="utf-8")
    return log_path


TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*")
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is",
    "are", "was", "were", "be", "been", "being", "by", "from", "as", "at",
    "this", "that", "these", "those", "it", "its", "into", "via", "vs",
    "if", "but", "not", "no", "yes", "we", "you", "they", "i",
}


def tokenize(text):
    return [t.lower() for t in TOKEN_RE.findall(text) if t.lower() not in STOPWORDS and len(t) > 1]


def page_text(root, page):
    path = root / page["path"]
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)


def build_bm25_index(root, pages):
    docs = []
    for page in pages:
        body = page_text(root, page)
        tokens = tokenize(page["title"] + " " + " ".join(page.get("tags", [])) + " " + body)
        docs.append({"path": page["path"], "title": page["title"], "type": page["type"], "tokens": tokens, "len": len(tokens)})
    n = len(docs)
    if n == 0:
        return None
    avgdl = sum(d["len"] for d in docs) / n
    df = Counter()
    for d in docs:
        for term in set(d["tokens"]):
            df[term] += 1
    idf = {term: math.log(1 + (n - dfreq + 0.5) / (dfreq + 0.5)) for term, dfreq in df.items()}
    tf = []
    for d in docs:
        tf.append(Counter(d["tokens"]))
    return {"docs": docs, "avgdl": avgdl, "idf": idf, "tf": tf}


def bm25_search(index, query, limit=10, k1=1.5, b=0.75):
    if index is None:
        return []
    q_terms = tokenize(query)
    if not q_terms:
        return []
    scores = []
    for i, d in enumerate(index["docs"]):
        score = 0.0
        for term in q_terms:
            if term not in index["idf"]:
                continue
            freq = index["tf"][i].get(term, 0)
            if freq == 0:
                continue
            num = freq * (k1 + 1)
            den = freq + k1 * (1 - b + b * d["len"] / index["avgdl"])
            score += index["idf"][term] * num / den
        if score > 0:
            scores.append((score, d))
    scores.sort(key=lambda x: -x[0])
    return scores[:limit]


def run_search(root, pages, query, limit):
    index = build_bm25_index(root, pages)
    hits = bm25_search(index, query, limit=limit)
    if not hits:
        print(f"No results for: {query}")
        return
    print(f"Top {len(hits)} BM25 results for: {query}")
    print("-" * 60)
    for score, d in hits:
        print(f"{score:6.2f}  [{d['type']:7s}]  {d['title']}")
        print(f"        {d['path']}")


def load_typed_edges(root):
    path = root / "outputs/typed-edges/edges.tsv"
    if not path.exists():
        return []
    edges = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if i == 0 or not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        edges.append({"source": parts[0], "kind": parts[1], "target": parts[2], "evidence": parts[3]})
    return edges


PREPRINT_PREFIXES = {
    "10.1101": "bioRxiv/medRxiv",
    "10.64898": "bioRxiv (new prefix)",
    "10.21203": "Research Square",
    "10.31219": "OSF Preprints",
    "10.20944": "Preprints.org",
    "10.48550": "arXiv",
}
BIORXIV_SUFFIX = re.compile(r"^\d{4}\.\d{2}\.\d{2}\.\d+$")


def scan_preprint_refs(root):
    refs_dir = root / "raw/refs"
    items = []
    if not refs_dir.exists():
        return items
    for path in sorted(refs_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)
        doi = str(fm.get("doi", "") or "").strip().strip('"')
        if not doi:
            continue
        prefix, _, suffix = doi.partition("/")
        venue = PREPRINT_PREFIXES.get(prefix)
        if not venue and suffix and BIORXIV_SUFFIX.match(suffix):
            venue = "bioRxiv/medRxiv (date-suffix)"
        if not venue:
            continue
        items.append({
            "path": path.relative_to(root).as_posix(),
            "doi": doi,
            "venue": venue,
            "title": str(fm.get("title", "") or "").strip().strip('"'),
            "published_doi": str(fm.get("published_doi", "") or "").strip().strip('"'),
            "last_checked": str(fm.get("last_checked", "") or "").strip().strip('"'),
        })
    return items


def crossref_check_published(doi, timeout=8):
    import urllib.request
    import urllib.error
    url = f"https://api.crossref.org/works/{doi}"
    _contact = os.environ.get("AGENT_ELN_CONTACT_EMAIL", "agent-eln@example.org")
    req = urllib.request.Request(url, headers={"User-Agent": f"knowledge-pm/1.0 (mailto:{_contact})"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        return {"error": str(exc)}
    msg = data.get("message", {})
    relations = msg.get("relation", {}) or {}
    published_of = relations.get("is-preprint-of", []) or []
    retracted = msg.get("update-to", []) or []
    return {
        "published_dois": [r.get("id") for r in published_of if r.get("id")],
        "retracted": [u.get("type") == "retraction" for u in retracted],
        "title": (msg.get("title") or [""])[0],
    }


def run_preprint_status(root, check_online, limit):
    items = scan_preprint_refs(root)
    out_path = root / f"outputs/audits/preprint-status-{datetime.now(timezone.utc).strftime('%Y%m%d')}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Preprint Status — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "",
        f"Scanned `raw/refs/*.md` for preprint DOIs. Found {len(items)} preprint pointer file(s).",
        "",
    ]
    if not items:
        lines.append("- No preprint references with parseable `doi:` frontmatter found.")
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Preprint status: {out_path} (no preprints)")
        return
    lines.append("## Inventory")
    lines.append("")
    for item in items:
        title = item["title"] or "(no title)"
        lines.append(f"- **{title}** — {item['venue']}, DOI `{item['doi']}`")
        lines.append(f"  - ref: `{item['path']}`")
        if item["published_doi"]:
            lines.append(f"  - already recorded as published: `{item['published_doi']}`")
        if item["last_checked"]:
            lines.append(f"  - last checked: {item['last_checked']}")
    if check_online:
        lines.extend(["", "## Crossref check results", ""])
        published = []
        errors = []
        print(f"Querying Crossref for {min(len(items), limit)} preprint DOI(s)...")
        for item in items[:limit]:
            if item["published_doi"]:
                continue
            res = crossref_check_published(item["doi"])
            if "error" in res:
                errors.append((item, res["error"]))
                lines.append(f"- `{item['doi']}` — Crossref error: {res['error']}")
                continue
            if res.get("published_dois"):
                published.append((item, res["published_dois"]))
                lines.append(f"- **PUBLISHED**: `{item['doi']}` → {', '.join(res['published_dois'])} (was: {item['title'][:60]})")
                lines.append(f"  - Action: update `{item['path']}` with `published_doi:` and `last_checked:` fields; re-check confidence on related wiki pages.")
            else:
                lines.append(f"- `{item['doi']}` — still preprint per Crossref")
        if not published:
            lines.append("- No newly-published preprints detected.")
        print(f"  Published transitions detected: {len(published)}")
        print(f"  Crossref errors: {len(errors)}")
    else:
        lines.extend(["", "## How to check for publication", "",
                      "Run `python3 knowledge/scripts/knowledge_pm.py --mode preprint-status --check-online` to query Crossref for `is-preprint-of` relations on each DOI. Network call, rate-limited; pass `--limit N` to cap.",
                      ""])
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Preprint status: {out_path}")
    print(f"  Preprints catalogued: {len(items)}")


def _normalize_entity_key(s):
    s = s.lower()
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^\w一-鿿]+", "", s)
    return s.strip()


def _find_similar_entities(entities):
    """Group entities whose normalized title or any alias collides.

    Policy: only highly-similar pairs are real merge candidates.
    Thin/low-inlink alone is NOT grounds for merging — the full entity roster is preserved by design.
    """
    buckets = {}
    for p in entities:
        keys = {_normalize_entity_key(p["title"])}
        for alias in p.get("aliases", []) or []:
            k = _normalize_entity_key(alias)
            if k:
                keys.add(k)
        for k in keys:
            if not k:
                continue
            buckets.setdefault(k, []).append(p)
    groups = [v for v in buckets.values() if len(v) > 1]
    seen = set()
    unique = []
    for g in groups:
        sig = tuple(sorted(p["path"] for p in g))
        if sig in seen:
            continue
        seen.add(sig)
        unique.append(g)
    return unique


def run_entity_audit(root, pages, thin_words, limit):
    edges = load_typed_edges(root)
    inlinks = Counter()
    for e in edges:
        if e["kind"] == "links_to":
            inlinks[e["target"]] += 1
    entities = [p for p in pages if p["type"] == "entity"]
    thin = [(p, inlinks.get(p["path"], 0)) for p in entities if p["words"] < thin_words]
    enrich_candidates = sorted(thin, key=lambda x: (-x[1], x[0]["words"]))
    similar_groups = _find_similar_entities(entities)
    out_path = root / f"outputs/audits/entity-audit-{datetime.now(timezone.utc).strftime('%Y%m%d')}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Entity Audit — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "",
        f"Threshold: entities with < {thin_words} words are 'thin'.",
        f"Total entities: {len(entities)}",
        f"Thin entities (enrich candidates): {len(thin)} ({len(thin) * 100 // max(len(entities), 1)}%)",
        f"Highly-similar entity groups (merge candidates): {len(similar_groups)}",
        "",
        "**Policy:** the full entity roster is preserved. Thin or low-inlink entities are NEVER merge candidates — only highly-similar duplicates (same subject, alias collision) are. Thin entities should be enriched or left as-is.",
        "",
        "## Merge candidates (highly-similar entities only)",
        "",
        "Each group below shares a normalized title or alias. Decide which page to keep canonical and redirect the others.",
        "",
    ]
    if similar_groups:
        for g in similar_groups:
            lines.append(f"- Group:")
            for p in g:
                lines.append(f"  - [{p['title']}]({p['path']}) — {p['words']} words, {inlinks.get(p['path'], 0)} inlinks")
    else:
        lines.append("- (none — no alias or title collisions detected)")
    lines.extend(["", "## Enrich candidates (thin entities, keep all)", "",
                  "These pages are short. Consider expanding when convenient; do NOT merge or delete based on thinness alone.",
                  ""])
    for p, n in enrich_candidates:
        lines.append(f"- [{p['title']}]({p['path']}) — {p['words']} words, {n} inlinks")
    if not enrich_candidates:
        lines.append("- (none)")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Entity audit: {out_path}")
    print(f"  Total entities: {len(entities)}")
    print(f"  Thin (< {thin_words} words, enrich candidates): {len(thin)}")
    print(f"  Highly-similar groups (merge candidates): {len(similar_groups)}")
    if limit and similar_groups:
        print("\nTop merge candidates:")
        for g in similar_groups[:limit]:
            titles = " | ".join(p["title"] for p in g)
            print(f"  - {titles}")


def run_ask(root, pages, query, seed_limit, neighbor_limit, include_semantic=False):
    index = build_bm25_index(root, pages)
    hits = bm25_search(index, query, limit=seed_limit)
    if not hits:
        print(f"No wiki pages match: {query}")
        return
    edges = load_typed_edges(root)
    out_neighbors = defaultdict(set)
    in_neighbors = defaultdict(set)
    semantic_edges = defaultdict(list)
    for e in edges:
        if e["kind"] == "links_to":
            out_neighbors[e["source"]].add(e["target"])
            in_neighbors[e["target"]].add(e["source"])
        elif e["kind"] in SEMANTIC_EDGE_TYPES:
            semantic_edges[e["source"]].append(e)
    page_by_path = {p["path"]: p for p in pages}
    print(f"Based on these pages you should read for: {query}")
    print("=" * 70)
    for rank, (score, d) in enumerate(hits, start=1):
        page = page_by_path.get(d["path"], {})
        conf = page.get("confidence") or "?"
        print(f"\n{rank}. [{d['type']:7s}] {d['title']}  (BM25 {score:.2f}, conf {conf})")
        print(f"   path: {d['path']}")
        sem = semantic_edges.get(d["path"], []) if include_semantic else []
        if sem:
            print(f"   semantic edges ({len(sem)}):")
            for e in sem[:neighbor_limit]:
                n_page = page_by_path.get(e["target"])
                title = n_page["title"] if n_page else e["target"]
                print(f"     - {e['kind']} -> {title}  ({e['target']}) — {e['evidence']}")
        neighbors = sorted(out_neighbors.get(d["path"], set()) | in_neighbors.get(d["path"], set()))
        if neighbors:
            print(f"   neighbors ({min(len(neighbors), neighbor_limit)} of {len(neighbors)}):")
            for n in neighbors[:neighbor_limit]:
                n_page = page_by_path.get(n)
                title = n_page["title"] if n_page else n
                print(f"     - {title}  ({n})")
        else:
            print("   neighbors: none recorded in typed-edges")


def run_query(root, edge_kind, source, target, limit):
    edges = load_typed_edges(root)
    if not edges:
        print("No typed-edges yet. Run --mode agent first to generate them.", file=sys.stderr)
        return
    results = []
    for e in edges:
        if edge_kind and not fnmatch.fnmatchcase(e["kind"], edge_kind):
            continue
        if source and not fnmatch.fnmatchcase(e["source"], source):
            continue
        if target and not fnmatch.fnmatchcase(e["target"], target):
            continue
        results.append(e)
    if not results:
        print("No edges match the filter.")
        return
    print(f"{len(results)} edge(s) match. Showing first {min(limit, len(results))}:")
    print("-" * 60)
    for e in results[:limit]:
        print(f"[{e['kind']:11s}]  {e['source']}  ->  {e['target']}  ({e['evidence']})")
    if len(results) > limit:
        print(f"... and {len(results) - limit} more. Use --limit to show more.")


REQUIRED_FRONTMATTER = ["title", "type", "created", "updated", "confidence", "confidence_rationale", "sources", "tags"]


def extract_link_targets(text):
    """Markdown link targets, correctly handling angle-bracket targets that contain
    ')' — e.g. [..](<wiki/entities/Foo (Bar 2026).md>). The naive \\(([^)]+)\\)
    regex truncates those at the inner paren; this does not."""
    targets = []
    for match in re.finditer(r"\]\(\s*(<[^>]*>|[^)\s]+)", text):
        target = wiki_target(match.group(1))
        if target:
            targets.append(target)
    return targets


def _index_link_targets(root):
    """Return the list of wiki/ link targets found in wiki/index.md (with duplicates)."""
    index = root / "wiki/index.md"
    if not index.exists():
        return None
    return extract_link_targets(index.read_text(encoding="utf-8", errors="replace"))


def run_health(root):
    """Fast, side-effect-free preflight. Catches the cheap structural problems
    (empty pages, index drift, broken/indented frontmatter, duplicate titles, log
    drift) before paying for a full lint + graph compile. Exit code 1 on any FAIL."""
    fails = []   # (check, [details]) — block; lint would also reject these
    warns = []   # (check, [details]) — surface, don't block

    wiki_dir = root / "wiki"
    md_paths = sorted(wiki_dir.rglob("*.md"))
    index_rel = "wiki/index.md"

    # 1. Empty / unreadable pages
    empty = []
    for path in md_paths:
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            empty.append(f"{rel} (unreadable: {exc})")
            continue
        body = re.sub(r"^---\n.*?\n---", "", text, count=1, flags=re.DOTALL)
        if len(re.findall(r"\w+", body)) == 0:
            empty.append(rel)
    if empty:
        fails.append(("Empty pages", empty))

    # 2. Frontmatter: must start at byte 0 with '---' and have a closing fence.
    #    Indented or missing-close frontmatter is the exact failure AGENTS.md warns about.
    broken_fm = []
    missing_keys = []
    no_fm = []
    for path in md_paths:
        rel = path.relative_to(root).as_posix()
        if rel == index_rel:
            continue  # index.md is generated and carries no YAML frontmatter
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.startswith("---\n"):
            if re.match(r"^\s+---", text) or re.search(r"\n\s+---\s*\n", text[:200]):
                broken_fm.append(f"{rel} (indented frontmatter fence)")
            else:
                no_fm.append(rel)
            continue
        if text.find("\n---", 4) == -1:
            broken_fm.append(f"{rel} (no closing '---' fence)")
            continue
        fm = parse_frontmatter(text)
        absent = [k for k in REQUIRED_FRONTMATTER if not fm.get(k)]
        if absent:
            missing_keys.append(f"{rel} (missing: {', '.join(absent)})")
    if broken_fm:
        fails.append(("Malformed frontmatter", broken_fm))
    if no_fm:
        warns.append(("Pages with no frontmatter", no_fm))
    if missing_keys:
        warns.append(("Pages missing required frontmatter keys", missing_keys))

    # 3. Index sync — mirror lint: every page linked at least once (no orphans),
    #    and every index link resolves (no dead links). Pages are intentionally
    #    listed from several sections (catalog + chronological + open questions),
    #    so multiple listings are NOT an error.
    targets = _index_link_targets(root)
    page_rels = {p.relative_to(root).as_posix() for p in md_paths} - {index_rel}
    if targets is None:
        fails.append(("Index", ["wiki/index.md is missing"]))
    else:
        listed = {t for t in targets if t != index_rel}
        not_in_index = sorted(page_rels - listed)
        dangling = sorted(t for t in listed if not (root / t).exists())
        if not_in_index:
            fails.append(("Pages not listed in index (orphans)", not_in_index))
        if dangling:
            fails.append(("Index links to nonexistent pages", dangling))

    # 4. Duplicate titles within the same page type (case-insensitive,
    #    whitespace-normalized). Cross-type pairs (a summary + its entity) are
    #    expected in this wiki and deliberately not flagged.
    by_title = defaultdict(list)
    for path in md_paths:
        rel = path.relative_to(root).as_posix()
        if rel == index_rel:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)
        m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        title = (fm.get("title") or (m.group(1).strip() if m else path.stem)).strip().lower()
        title = re.sub(r"\s+", " ", title)
        by_title[(infer_type(rel), title)].append(rel)
    dup_titles = [f"[{typ}] {t!r}: {', '.join(sorted(paths))}"
                  for (typ, t), paths in sorted(by_title.items()) if len(paths) > 1]
    if dup_titles:
        warns.append(("Duplicate page titles (same type)", dup_titles))

    # 5. Log coverage — flag stale logging and edits made after the last log entry.
    log_files = sorted((root / "log").glob("20*.md"))
    today = datetime.now(timezone.utc).date()
    if not log_files:
        warns.append(("Log coverage", ["no log/ entries found"]))
    else:
        newest = log_files[-1].stem
        newest_date = parse_iso_date(newest.replace("-", ""))
        if newest_date:
            age = (today - newest_date.date()).days
            if age > 21:
                warns.append(("Log coverage", [f"newest log is {newest} ({age} days old) — logging may have lapsed"]))
            unlogged = []
            for path in md_paths:
                fm = parse_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
                upd = parse_iso_date(str(fm.get("updated", "")).replace("-", "")[:8])
                if upd and upd.date() > newest_date.date():
                    unlogged.append(f"{path.relative_to(root).as_posix()} (updated {fm.get('updated')})")
            if unlogged:
                warns.append(("Pages updated after the last log entry (possibly unlogged)", unlogged))

    # Report
    print(f"Health preflight — {today.isoformat()}  ({len(md_paths)} wiki pages)")
    print("=" * 70)
    if not fails and not warns:
        print("PASS — no structural issues. Safe to run full lint.")
        return 0
    for label, details in fails:
        print(f"\nFAIL · {label} ({len(details)})")
        for d in details[:25]:
            print(f"  - {d}")
        if len(details) > 25:
            print(f"  ... and {len(details) - 25} more")
    for label, details in warns:
        print(f"\nWARN · {label} ({len(details)})")
        for d in details[:25]:
            print(f"  - {d}")
        if len(details) > 25:
            print(f"  ... and {len(details) - 25} more")
    print("\n" + "=" * 70)
    if fails:
        print(f"RESULT: FAIL ({len(fails)} blocking, {len(warns)} warnings). Fix blockers before running lint.")
        return 1
    print(f"RESULT: PASS with {len(warns)} warning(s). Safe to run full lint.")
    return 0


def _read_fm_body(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(text)
    body = re.sub(r"^---\n.*?\n---", "", text, count=1, flags=re.DOTALL)
    return fm, body


def run_quality(root, pages):
    """A6: non-blocking quality report. Flags thin / uncited / structure-poor pages.
    Never edits, never blocks. Writes outputs/audits/quality-YYYYMMDD.md."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    META = {"wiki/index.md"}
    rows = []
    for p in pages:
        if p["path"] in META:
            continue
        issues = []
        if not p["sources"]:
            issues.append("no-sources")
        if p["words"] < 120:
            issues.append(f"thin({p['words']}w)")
        if not p["links"]:
            issues.append("no-outbound-links")
        _, body = _read_fm_body(root / p["path"])
        if not re.search(r"^#{2,6}\s+", body, re.MULTILINE):
            issues.append("no-subheadings")
        if issues:
            rows.append((p["path"], p["type"], ", ".join(issues)))
    out_dir = root / "outputs/audits"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"quality-{stamp}.md"
    rows.sort(key=lambda r: r[0])
    lines = [f"# Wiki Quality Report — {stamp}", "",
             f"Non-blocking. {len(rows)} page(s) flagged of {len(pages)}. "
             "Feeds the human/agent `audit/` loop; pages are never auto-rewritten.", ""]
    if rows:
        lines += ["| Page | Type | Flags |", "|---|---|---|"]
        lines += [f"| `{path}` | {typ} | {iss} |" for path, typ, iss in rows]
    else:
        lines.append("No quality flags. ✅")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Quality report: {out.relative_to(root)}  ({len(rows)} flagged / {len(pages)} pages)")
    for path, _typ, iss in rows[:25]:
        print(f"  - {path}: {iss}")
    return 0


def run_supersession_check(root):
    """A1: validate explicit supersession metadata (non-blocking, read-only).

    Convention (see AGENTS.md 'Supersession'):
      - superseded page: `status: superseded`, `superseded_by: <wiki/path>`, and a
        top-of-body banner line matching '> ⚠ ... Superseded by ...'.
      - superseding page: `supersedes: [<wiki/path>, ...]` (reciprocal).
    Reports reciprocity / resolution / banner / status violations, plus preprint-
    sourced pages worth reviewing for a published successor. Writes
    outputs/audits/supersession-YYYYMMDD.md. Always exit 0 (never gates)."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    paths = sorted((root / "wiki").rglob("*.md"))
    meta = {}
    for path in paths:
        rel = path.relative_to(root).as_posix()
        fm, body = _read_fm_body(path)
        sb = fm.get("superseded_by")
        sup = fm.get("supersedes")
        if isinstance(sup, str):
            sup = [sup]
        srcs = fm.get("sources", [])
        if isinstance(srcs, str):
            srcs = [srcs]
        meta[rel] = {
            "status": str(fm.get("status") or "").strip().lower(),
            "superseded_by": wiki_target(sb) if sb else None,
            "supersedes": [wiki_target(s) or s for s in (sup or [])],
            "has_banner": bool(re.search(r"superseded by", body, re.I)),
            "sources": " ".join(str(s) for s in srcs),
        }
    existing = set(meta)
    violations, used = [], 0
    for rel, m in meta.items():
        if m["superseded_by"] or m["supersedes"] or m["status"] == "superseded":
            used += 1
        if m["superseded_by"]:
            t = m["superseded_by"]
            if t not in existing:
                violations.append(f"{rel}: superseded_by → missing page '{t}'")
            elif rel not in meta[t]["supersedes"]:
                violations.append(f"{rel}: superseded_by '{t}', but that page's supersedes: does not list it back")
            if m["status"] != "superseded":
                violations.append(f"{rel}: has superseded_by but status != 'superseded'")
            if not m["has_banner"]:
                violations.append(f"{rel}: superseded page missing '> ⚠ … Superseded by …' banner")
        for t in m["supersedes"]:
            if t not in existing:
                violations.append(f"{rel}: supersedes → missing page '{t}'")
            elif meta[t]["superseded_by"] != rel:
                violations.append(f"{rel}: supersedes '{t}', but that page's superseded_by != this page")
    candidates = sorted(
        rel for rel, m in meta.items()
        if re.search(r"arxiv\.org|10\.1101|biorxiv|researchsquare|osf\.io", m["sources"], re.I)
        and not m["superseded_by"])
    out_dir = root / "outputs/audits"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"supersession-{stamp}.md"
    lines = [f"# Supersession Check — {stamp}", "",
             f"Pages using supersession metadata: **{used}**. Reciprocity/banner violations: "
             f"**{len(violations)}**. Preprint-sourced review candidates: **{len(candidates)}**.",
             "", "Non-blocking. Marking a page superseded is a human/agent decision — this only validates.", ""]
    lines.append("## Violations")
    lines += ([f"- {v}" for v in violations] if violations else ["- none ✅"])
    lines += ["", "## Preprint-sourced pages to review for a published successor",
              "(arXiv / bioRxiv / Research Square / OSF sources; not yet superseded)", ""]
    lines += ([f"- `{c}`" for c in candidates] if candidates else ["- none"])
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Supersession check: {out.relative_to(root)}  (used={used}, violations={len(violations)}, candidates={len(candidates)})")
    for v in violations[:25]:
        print(f"  ! {v}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Generate weekly PM / agent reports for the wiki, or query it.")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--mode", choices=["pm", "agent", "health", "search", "query", "ask", "audit-entities", "preprint-status", "quality", "supersession-check"], default="agent",
                       help="pm = full health reports + lint; agent = add ingest plan, hidden-patterns, literature seeds; "
                            "health = fast structural preflight (no lint/graph compile), exit 1 on blocking issues; "
                            "search = BM25 keyword search; query = filter typed-edges; "
                            "ask = BM25 seeds + typed-edge neighbors (pure-retrieval closed loop); "
                            "audit-entities = list highly-similar entity merge + thin enrich candidates; "
                            "quality = non-blocking thin/uncited/structure-poor page report (A6); "
                            "supersession-check = validate supersedes/superseded_by metadata (A1); "
                            "preprint-status = scan raw/refs for preprint DOIs; --check-online queries Crossref.")
    parser.add_argument("--no-lint", action="store_true")
    parser.add_argument("--query", help="search: free-text query string")
    parser.add_argument("--limit", type=int, default=10, help="search/query: max results to show")
    parser.add_argument("--edge-kind", help="query: filter by edge type (e.g. links_to, has_tag, source_for, has_type). Supports * glob.")
    parser.add_argument("--source", help="query: filter by edge source (path or tag). Supports * glob.")
    parser.add_argument("--target", help="query: filter by edge target. Supports * glob.")
    parser.add_argument("--seed-limit", type=int, default=5, help="ask: BM25 seed pages to start from")
    parser.add_argument("--neighbor-limit", type=int, default=8, help="ask: max neighbors to show per seed")
    parser.add_argument("--semantic", action="store_true", help="ask: include A2 semantic-edge pilot output (off by default)")
    parser.add_argument("--thin-words", type=int, default=200, help="audit-entities: word threshold below which entities are thin")
    parser.add_argument("--check-online", action="store_true", help="preprint-status: also query Crossref to detect published versions")
    args = parser.parse_args()

    # Accept either the repository root (contains wiki/) or the wiki directory
    # itself. The module manual historically documented the latter.
    requested_root = Path(args.root).resolve()
    if not (requested_root / "wiki").is_dir() and requested_root.name == "wiki":
        requested_root = requested_root.parent
    args.root = str(requested_root)

    if args.mode == "health":
        sys.exit(run_health(Path(args.root)))

    if args.mode == "search":
        if not args.query:
            parser.error("--mode search requires --query")
        pages = load_pages(Path(args.root))
        run_search(Path(args.root), pages, args.query, args.limit)
        return

    if args.mode == "query":
        run_query(Path(args.root), args.edge_kind, args.source, args.target, args.limit)
        return

    if args.mode == "ask":
        if not args.query:
            parser.error("--mode ask requires --query")
        pages = load_pages(Path(args.root))
        run_ask(Path(args.root), pages, args.query, args.seed_limit, args.neighbor_limit, include_semantic=args.semantic)
        return

    if args.mode == "audit-entities":
        pages = load_pages(Path(args.root))
        run_entity_audit(Path(args.root), pages, args.thin_words, args.limit)
        return

    if args.mode == "preprint-status":
        run_preprint_status(Path(args.root), args.check_online, args.limit)
        return

    if args.mode == "quality":
        pages = load_pages(Path(args.root))
        sys.exit(run_quality(Path(args.root), pages))

    if args.mode == "supersession-check":
        sys.exit(run_supersession_check(Path(args.root)))

    root = Path(args.root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    for subdir in ["outputs/discovery", "outputs/gaps", "outputs/evolution", "outputs/typed-edges", "outputs/ingest-plans", "outputs/hidden-patterns", "outputs/literature-seeds"]:
        (root / subdir).mkdir(parents=True, exist_ok=True)

    pages = load_pages(root)
    inbox_items = collect_inbox_items(root)
    lint_code = 0
    lint_output = ""
    if not args.no_lint:
        lint_code, lint_output = run_lint(root)
        (root / f"outputs/lint-{stamp}.log").write_text(lint_output, encoding="utf-8")

    graph_stats = load_graph_stats(root)
    lint_issues = collect_lint_issues(root)
    questions = collect_questions(root)
    gaps = collect_research_gaps(root)
    discovery = write_discovery(root, pages, stamp)
    gap = write_gap(root, pages, questions, lint_issues, stamp)
    evolution = write_evolution(root, pages, graph_stats, stamp)
    edges, dated_edges = write_typed_edges(root, pages, stamp)
    extra_paths = {}
    if args.mode == "agent":
        extra_paths["Ingest plan"] = write_ingest_plan(root, inbox_items, stamp)
        extra_paths["Hidden patterns"] = write_hidden_patterns(root, pages, stamp)
        extra_paths["Literature seeds"] = write_literature_seeds(root, questions, gaps, pages, stamp)
    archived_count, archived_months = archive_old_outputs(root)
    dashboard = write_dashboard(root, discovery, gap, evolution, edges, lint_code, extra_paths, args.mode, archived_count, archived_months)
    log = append_log(root, stamp, {
        "discovery": discovery,
        "gap": gap,
        "evolution": evolution,
        "typed_edges": dated_edges,
        "dashboard": dashboard,
        **{label.lower().replace(" ", "_"): path for label, path in extra_paths.items()},
    }, lint_code, args.mode)

    print(f"Discovery: {discovery}")
    print(f"Gap: {gap}")
    print(f"Evolution: {evolution}")
    print(f"Typed edges: {edges}")
    for label, path in extra_paths.items():
        print(f"{label}: {path}")
    print(f"Dashboard: {dashboard}")
    print(f"Log: {log}")
    print(f"Lint exit code: {lint_code}")


if __name__ == "__main__":
    main()
