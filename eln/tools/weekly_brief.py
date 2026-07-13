#!/usr/bin/env python3
"""weekly_brief.py — weekly rollup dashboard (in the spirit of SciCrucible's forge-weekly, ELN edition).

Produces a markdown brief:
- New records this week (by type)
- Unread queue (LIT with empty wiki_link)
- wiki summaries ingested this week (reads knowledge/log/YYYYMMDD.md)
- Compressed summary of health.py results
- Reagent expiry warnings (within 30 days)

Usage:
  python tools/weekly_brief.py                # print to stdout (dry-run)
  python tools/weekly_brief.py --write        # write to reports/weekly-brief-YYYYMMDD.md
  python tools/weekly_brief.py --since 14d    # custom window (default 7d)
  python tools/weekly_brief.py --json         # machine-readable output (for automation)

Sends no notifications and modifies no ELN records. Hook up push/email in external automation.
"""
from __future__ import annotations
import os, sys, argparse, json, re, datetime, subprocess
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import fm
import registry as R
import config as _cfg

ROOT = R.ROOT
REPO_ROOT = _cfg.REPO_ROOT
LIT_DIR = os.path.join(ROOT, "literature")
WIKI_LOG = os.path.join(_cfg.WIKI_ROOT, "log")


def _try_duckdb():
    try:
        import duckdb  # noqa: F401
        return duckdb
    except ImportError:
        return None


def collect_new_records(since_date: str):
    """Return [(type, id, title/name, path), ...] grouped by type."""
    duckdb = _try_duckdb()
    db = os.path.join(ROOT, "index", "data.duckdb")
    if duckdb and os.path.exists(db):
        con = duckdb.connect(db, read_only=True)
        rows = con.execute(
            "SELECT type, id, name, path, created_date FROM records "
            "WHERE created_date >= ? ORDER BY created_date DESC, id",
            [since_date],
        ).fetchall()
        con.close()
        return rows
    # Fallback: scan the whole library
    out = []
    for dp, _, fs in os.walk(ROOT):
        if any(s in dp for s in (".git", "/index", "/templates", "/tools", "/reports")):
            continue
        for fn in fs:
            if not fn.endswith(".md"):
                continue
            p = os.path.join(dp, fn)
            meta, _ = fm.parse(p)
            rid = meta.get("id")
            if not rid or "XXXX" in rid:
                continue
            created = str(meta.get("created", ""))[:10]
            if created and created >= since_date:
                out.append(
                    (meta.get("type", "?"), rid, meta.get("title") or meta.get("name") or "", p, created)
                )
    out.sort(key=lambda r: (r[4], r[1]), reverse=True)
    return out


def collect_unread_lit():
    """LIT cards with empty wiki_link -> to-read queue."""
    out = []
    if not os.path.isdir(LIT_DIR):
        return out
    for fn in sorted(os.listdir(LIT_DIR)):
        if not fn.endswith(".md"):
            continue
        p = os.path.join(LIT_DIR, fn)
        meta, _ = fm.parse(p)
        rid = meta.get("id", "")
        if not rid.startswith("LIT-"):
            continue
        if not meta.get("wiki_link"):
            out.append(
                (
                    rid,
                    meta.get("title") or "",
                    str(meta.get("journal") or ""),
                    str(meta.get("year") or ""),
                    p,
                )
            )
    return out


def collect_recent_wiki_ingests(since_date: str):
    """Scan knowledge/log/YYYYMMDD.md and list wiki summary lines ingested within the window."""
    if not os.path.isdir(WIKI_LOG):
        return []
    since = datetime.date.fromisoformat(since_date)
    out = []
    for fn in sorted(os.listdir(WIKI_LOG), reverse=True):
        if not re.match(r"^\d{8}\.md$", fn):
            continue
        try:
            d = datetime.date(int(fn[:4]), int(fn[4:6]), int(fn[6:8]))
        except ValueError:
            continue
        if d < since:
            continue
        p = os.path.join(WIKI_LOG, fn)
        with open(p, encoding="utf-8") as f:
            body = f.read()
        # Capture all summary paths
        for m in re.finditer(r"summaries/([\w\-]+\.md)", body):
            out.append((d.isoformat(), m.group(1)))
    # Deduplicate, keeping earliest occurrence
    seen, dedup = set(), []
    for d, slug in out:
        if slug in seen:
            continue
        seen.add(slug)
        dedup.append((d, slug))
    return dedup


def run_health_capsule():
    """Run health.py --json, keep only summary counts. Returns None on failure."""
    try:
        r = subprocess.run(
            ["python3", os.path.join(ROOT, "tools", "health.py"), "--json"],
            capture_output=True, text=True, timeout=60,
        )
        if r.returncode != 0:
            return None
        return json.loads(r.stdout)
    except Exception:
        return None


def collect_expiring_resources(days: int = 30):
    """Scan the expiry field in resource card frontmatter and list items expiring within X days."""
    out = []
    today = datetime.date.today()
    limit = today + datetime.timedelta(days=days)
    root = os.path.join(ROOT, "resources")
    if not os.path.isdir(root):
        return out
    for dp, _, fs in os.walk(root):
        for fn in fs:
            if not fn.endswith(".md"):
                continue
            p = os.path.join(dp, fn)
            meta, _ = fm.parse(p)
            exp = meta.get("expiry") or meta.get("expiration")
            if not exp:
                continue
            try:
                d = datetime.date.fromisoformat(str(exp)[:10])
            except ValueError:
                continue
            if d <= limit:
                out.append((meta.get("id", "?"), meta.get("name", ""), d.isoformat(), p))
    out.sort(key=lambda r: r[2])
    return out


def render_md(data):
    lines = []
    L = lines.append
    since = data["since"]
    today = data["today"]
    L(f"# Weekly Brief — {today}")
    L("")
    L(f"Window: `{since}` ~ `{today}` · Generator: `weekly_brief.py`")
    L("")

    # New records
    new = data["new_records"]
    L(f"## 📥 New this week · {len(new)} entries")
    L("")
    if new:
        by_type = {}
        for row in new:
            by_type.setdefault(row[0], []).append(row)
        for t in sorted(by_type):
            L(f"### {t} — {len(by_type[t])} entries")
            L("")
            for row in by_type[t][:15]:
                _, rid, title, _, created = row
                L(f"- `{rid}` · {created} · {title or '(untitled)'}")
            if len(by_type[t]) > 15:
                L(f"- ... {len(by_type[t]) - 15} more")
            L("")
    else:
        L("_No new records in window_")
        L("")

    # wiki ingest
    ingests = data["wiki_ingests"]
    L(f"## 📖 Wiki ingests this week · {len(ingests)} entries")
    L("")
    if ingests:
        for d, slug in ingests[:30]:
            L(f"- {d} · [`{slug}`]({_cfg.wiki_url(f'{_cfg.WIKI_DIR}/summaries/{slug}')})")
        if len(ingests) > 30:
            L(f"- ... {len(ingests) - 30} more")
    else:
        L("_No new wiki summaries in window_")
    L("")

    # Unread literature
    unread = data["unread_lit"]
    L(f"## 📚 To-read queue · {len(unread)} entries")
    L("")
    if unread:
        for rid, title, journal, year, _ in unread[:20]:
            meta = f"{journal} {year}".strip() or "—"
            L(f"- `{rid}` · **{title or '(untitled)'}** · _{meta}_")
        if len(unread) > 20:
            L(f"- ... {len(unread) - 20} more")
    else:
        L("_All LIT have wiki_link closed out_ 🎉")
    L("")

    # Reagent expiry
    exp = data["expiring"]
    L(f"## ⏰ Resources expiring within 30 days · {len(exp)} entries")
    L("")
    if exp:
        for rid, name, d, _ in exp:
            L(f"- `{rid}` · {d} · {name or '(unnamed)'}")
    else:
        L("_No expiring resources in window_")
    L("")

    # health capsule
    h = data.get("health")
    L("## 🩺 health.py summary")
    L("")
    if h and isinstance(h, dict):
        summary = h.get("summary") or h
        for k, v in list(summary.items())[:12]:
            L(f"- **{k}**: {v}")
    else:
        L("_health.py did not emit JSON (requires `--json` support; can be run manually via `python tools/health.py`)_")
    L("")

    L("---")
    L("_Generated by `tools/weekly_brief.py` · does not modify any ELN records · hook up push/email in external automation_")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="7d", help="Window: Nd or YYYY-MM-DD (default 7d)")
    ap.add_argument("--write", action="store_true", help="Write to reports/weekly-brief-YYYYMMDD.md")
    ap.add_argument("--json", action="store_true", help="Emit JSON (for automation)")
    ap.add_argument("--out", help="Force output path (optional)")
    args = ap.parse_args()

    today = datetime.date.today()
    if re.match(r"^\d+d$", args.since):
        since = (today - datetime.timedelta(days=int(args.since[:-1]))).isoformat()
    else:
        since = args.since

    data = {
        "today": today.isoformat(),
        "since": since,
        "new_records": collect_new_records(since),
        "unread_lit": collect_unread_lit(),
        "wiki_ingests": collect_recent_wiki_ingests(since),
        "expiring": collect_expiring_resources(30),
        "health": run_health_capsule(),
    }

    if args.json:
        # tuple → list, path → str
        def _s(rows):
            return [list(r) if isinstance(r, tuple) else r for r in rows]
        j = {
            "today": data["today"],
            "since": data["since"],
            "new_records": _s(data["new_records"]),
            "unread_lit": _s(data["unread_lit"]),
            "wiki_ingests": _s(data["wiki_ingests"]),
            "expiring": _s(data["expiring"]),
            "health": data["health"],
        }
        print(json.dumps(j, ensure_ascii=False, indent=2))
        return

    md = render_md(data)
    if args.write or args.out:
        out = args.out or os.path.join(ROOT, "reports", f"weekly-brief-{today.strftime('%Y%m%d')}.md")
        Path(os.path.dirname(out)).mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"✅ Weekly brief → {os.path.relpath(out, ROOT)}")
    else:
        print(md)


if __name__ == "__main__":
    main()
