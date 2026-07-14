#!/usr/bin/env python3
"""today.py — chronological "page of the day" for the ELN, in the spirit of a paper lab notebook.

Where weekly_brief.py groups by type, this fuses every signal of activity into one time-ordered
stream so you can read the day left-to-right:
  - Records created today       (from index/data.duckdb, or a filesystem fallback)
  - Records edited today        (file mtime inside eln/, lims/, methods/)
  - Wiki summaries ingested     (parses wiki/log/YYYYMMDD.md; --wiki-log to override)
  - Git commits in the repo     (from `git log` inside REPO_ROOT)

Usage:
  python tools/today.py                          # print today's page
  python tools/today.py --date 2026-07-12        # a past day
  python tools/today.py --write                  # save to reports/today-YYYYMMDD.md
  python tools/today.py --json                   # machine-readable
  python tools/today.py --wiki-log path/to/other/wiki/log          # extra wiki log dir

Read-only. Modifies nothing.
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
RECORD_ROOTS = [_cfg.ELN_ROOT, _cfg.LIMS_ROOT, _cfg.METHODS_ROOT]


def _try_duckdb():
    try:
        import duckdb
        return duckdb
    except ImportError:
        return None


def collect_created(day: str):
    """Records whose frontmatter `created` equals `day`. Returns [(hhmm, kind, type, id, title, path)]."""
    duckdb = _try_duckdb()
    db = os.path.join(ROOT, "index", "data.duckdb")
    rows = []
    if duckdb and os.path.exists(db):
        con = duckdb.connect(db, read_only=True)
        try:
            rows = con.execute(
                "SELECT type, id, name, path FROM records WHERE created_date = ? ORDER BY id",
                [day],
            ).fetchall()
        finally:
            con.close()
    else:
        for base in RECORD_ROOTS:
            if not os.path.isdir(base):
                continue
            for dp, _, fs in os.walk(base):
                if R.is_excluded(dp):
                    continue
                for fn in fs:
                    if not fn.endswith(".md"):
                        continue
                    p = os.path.join(dp, fn)
                    meta, _body = fm.parse(p)
                    rid = meta.get("id")
                    if not rid or "XXXX" in rid:
                        continue
                    if str(meta.get("created", ""))[:10] == day:
                        rows.append((meta.get("type", "?"), rid, meta.get("title") or meta.get("name") or "", p))
    out = []
    for t, rid, title, p in rows:
        out.append(("", "created", t, rid, title, p))
    return out


def collect_edited(day: str, skip_ids: set[str]):
    """Files under record roots with mtime on `day`, excluding ones already in skip_ids (created today)."""
    d = datetime.date.fromisoformat(day)
    start = datetime.datetime.combine(d, datetime.time.min).timestamp()
    end = datetime.datetime.combine(d, datetime.time.max).timestamp()
    out = []
    for base in RECORD_ROOTS:
        if not os.path.isdir(base):
            continue
        for dp, _, fs in os.walk(base):
            if R.is_excluded(dp):
                continue
            for fn in fs:
                if not fn.endswith(".md"):
                    continue
                p = os.path.join(dp, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if not (start <= st.st_mtime <= end):
                    continue
                meta, _body = fm.parse(p)
                rid = meta.get("id") or ""
                if rid in skip_ids or not rid or "XXXX" in rid:
                    continue
                hhmm = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%H:%M")
                title = meta.get("title") or meta.get("name") or ""
                out.append((hhmm, "edited", meta.get("type", "?"), rid, title, p))
    return out


def _parse_wiki_log(path: str) -> list[str]:
    """Return the list of `summaries/<slug>.md` slugs referenced in a wiki log file."""
    slugs: list[str] = []
    seen: set[str] = set()
    try:
        with open(path, encoding="utf-8") as f:
            body = f.read()
    except OSError:
        return slugs
    for m in re.finditer(r"summaries/([\w\-]+\.md)", body):
        slug = m.group(1)
        if slug in seen:
            continue
        seen.add(slug)
        slugs.append(slug)
    return slugs


def collect_wiki(day: str, extra_log_dirs: list[str]):
    """Wiki summaries ingested on `day`, per wiki/log/YYYYMMDD.md (and any extra log dirs)."""
    ymd = day.replace("-", "")
    dirs = [os.path.join(_cfg.WIKI_ROOT, "log")] + list(extra_log_dirs)
    out = []
    seen: set[str] = set()
    for d in dirs:
        p = os.path.join(d, f"{ymd}.md")
        if not os.path.exists(p):
            continue
        for slug in _parse_wiki_log(p):
            if slug in seen:
                continue
            seen.add(slug)
            out.append(("", "wiki", "SUMMARY", slug.replace(".md", ""), slug, p))
    return out


def collect_git(day: str):
    """Git commits in REPO_ROOT whose author-date is on `day`. Returns [(hhmm, kind, ...)]."""
    if not os.path.isdir(os.path.join(REPO_ROOT, ".git")):
        return []
    d = datetime.date.fromisoformat(day)
    nxt = (d + datetime.timedelta(days=1)).isoformat()
    try:
        r = subprocess.run(
            ["git", "-C", REPO_ROOT, "log",
             f"--since={day} 00:00", f"--until={nxt} 00:00",
             "--pretty=format:%h%x1f%ad%x1f%s", "--date=format:%H:%M"],
            capture_output=True, text=True, timeout=20,
        )
        if r.returncode != 0:
            return []
    except Exception:
        return []
    out = []
    for line in r.stdout.splitlines():
        parts = line.split("\x1f")
        if len(parts) != 3:
            continue
        sha, hhmm, subj = parts
        out.append((hhmm, "commit", "GIT", sha, subj, REPO_ROOT))
    return out


def build_events(day: str, wiki_log_dirs: list[str]):
    created = collect_created(day)
    created_ids = {ev[3] for ev in created}
    edited = collect_edited(day, created_ids)
    wiki = collect_wiki(day, wiki_log_dirs)
    git = collect_git(day)

    # Sort: events with a real HH:MM come in time order; events without one sink to the top
    # (they're same-day but time-unknown, so listing them first as a header block reads best).
    def sort_key(ev):
        hhmm = ev[0]
        return (1, hhmm) if hhmm else (0, ev[1])

    events = created + edited + wiki + git
    events.sort(key=sort_key)
    return events


def render_md(day: str, events: list):
    L = []
    add = L.append
    d = datetime.date.fromisoformat(day)
    add(f"# {day} — Lab Day ({d.strftime('%A')})")
    add("")
    add(f"Generator: `today.py` · {len(events)} events")
    add("")

    if not events:
        add("_Quiet day. Nothing recorded._")
        add("")
        add("## Counts")
        add("")
        add("- total: 0")
        add("")
        add("---")
        add("_Read-only view. Generated by `tools/today.py`._")
        return "\n".join(L) + "\n"

    # Split into "time unknown" (mostly created records, wiki ingests without commit time)
    # and "time-stamped" (edits + commits + anything with mtime).
    timed = [e for e in events if e[0]]
    untimed = [e for e in events if not e[0]]

    if untimed:
        add("## Same day (time unknown)")
        add("")
        for hhmm, kind, typ, rid, title, path in untimed:
            add(_line(hhmm, kind, typ, rid, title, path))
        add("")

    if timed:
        add("## Chronological")
        add("")
        add("| time | what | id | title |")
        add("| ---- | ---- | -- | ----- |")
        for hhmm, kind, typ, rid, title, path in timed:
            add(f"| {hhmm} | {kind} {typ} | `{rid}` | {title or '(untitled)'} |")
        add("")

    # Counts summary
    by_kind: dict[str, int] = {}
    for ev in events:
        by_kind[ev[1]] = by_kind.get(ev[1], 0) + 1
    add("## Counts")
    add("")
    for k in ("created", "edited", "wiki", "commit"):
        if k in by_kind:
            add(f"- {k}: {by_kind[k]}")
    add("")
    add("---")
    add("_Read-only view. Generated by `tools/today.py`._")
    return "\n".join(L) + "\n"


def _line(hhmm, kind, typ, rid, title, path):
    prefix = f"{hhmm}  " if hhmm else ""
    return f"- {prefix}`{kind}` **{typ}** `{rid}` — {title or '(untitled)'}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--write", action="store_true", help="Write to reports/today-YYYYMMDD.md")
    ap.add_argument("--out", help="Force output path")
    ap.add_argument("--json", action="store_true", help="Emit JSON")
    ap.add_argument("--wiki-log", action="append", default=[],
                    help="Extra wiki log dir (repeatable). Use when the wiki log lives outside the repo's wiki/log.")
    args = ap.parse_args()

    day = args.date or datetime.date.today().isoformat()
    events = build_events(day, args.wiki_log)

    if args.json:
        j = {
            "date": day,
            "count": len(events),
            "events": [
                {"time": e[0], "kind": e[1], "type": e[2], "id": e[3], "title": e[4], "path": e[5]}
                for e in events
            ],
        }
        print(json.dumps(j, ensure_ascii=False, indent=2))
        return

    md = render_md(day, events)
    if args.write or args.out:
        out = args.out or os.path.join(ROOT, "reports", f"today-{day.replace('-', '')}.md")
        Path(os.path.dirname(out)).mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"✅ Daily page → {os.path.relpath(out, ROOT)}")
    else:
        print(md)


if __name__ == "__main__":
    main()
