#!/usr/bin/env python3
"""A5 write-safe event hooks for Larry's Wiki.

These helpers stage, flag, and report only. They never write wiki pages.
"""

import argparse
import csv
import hashlib
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import knowledge_pm


ROOT = knowledge_pm.ROOT
PM = Path(__file__).resolve().with_name("knowledge_pm.py")


def utc_now():
    return datetime.now(timezone.utc)


def stamp_day():
    return utc_now().strftime("%Y%m%d")


def iso_now():
    return utc_now().isoformat(timespec="seconds").replace("+00:00", "Z")


def slugify(value):
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return value[:80] or "topic"


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def run_cmd(args):
    return subprocess.run(
        args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def existing_queue_paths(path):
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = csv.DictReader(f, delimiter="\t")
        return {row.get("path", "") for row in rows if row.get("path")}


def append_queue_rows(queue_path, rows):
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not queue_path.exists()
    with queue_path.open("a", encoding="utf-8", newline="") as f:
        fields = ["queued_at", "path", "bucket", "status", "priority", "size", "mtime", "title_hint", "sha256_12"]
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        if is_new:
            writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def file_digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def selected_inbox_items(root, raw_paths):
    items = knowledge_pm.collect_inbox_items(root)
    if not raw_paths:
        return items
    wanted = set()
    for raw in raw_paths:
        path = Path(raw)
        if not path.is_absolute():
            path = root / path
        try:
            rel = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
        if rel.startswith("raw/inbox/"):
            wanted.add(rel)
    return [item for item in items if item["path"] in wanted]


def run_inbox(root, raw_paths):
    queue_path = root / "outputs/ingest-plans/inbox-hook-queue.tsv"
    seen = existing_queue_paths(queue_path)
    rows = []
    skipped = []
    for item in selected_inbox_items(root, raw_paths):
        if item["path"] in seen:
            skipped.append(item["path"])
            continue
        path = root / item["path"]
        rows.append({
            "queued_at": iso_now(),
            "path": item["path"],
            "bucket": item["bucket"],
            "status": item["status"],
            "priority": item["priority"],
            "size": str(item["size"]),
            "mtime": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "title_hint": item["title_hint"],
            "sha256_12": file_digest(path),
        })
    if rows:
        append_queue_rows(queue_path, rows)

    report = root / "outputs/hooks/inbox-hook-latest.md"
    lines = [
        f"# Inbox Hook Report - {iso_now()}",
        "",
        "Report-only A5 hook. No wiki pages were written.",
        "",
        f"- Queue: `{queue_path.relative_to(root).as_posix()}`",
        f"- Newly queued: {len(rows)}",
        f"- Already queued: {len(skipped)}",
        "",
        "## Newly queued",
        "",
    ]
    lines.extend([f"- `{row['path']}` ({row['bucket']}, status `{row['status']}`)" for row in rows] or ["- none"])
    lines.extend(["", "## Already queued", ""])
    lines.extend([f"- `{path}`" for path in skipped] or ["- none"])
    atomic_write(report, "\n".join(lines) + "\n")

    print(f"Inbox hook: queued {len(rows)} new file(s), skipped {len(skipped)} already queued.")
    print(f"Queue: {queue_path}")
    print(f"Report: {report}")
    return 0


def run_session_start(root, topic, seed_limit, neighbor_limit, semantic):
    args = [
        "python3", str(PM), "--root", str(root), "--mode", "ask",
        "--query", topic, "--seed-limit", str(seed_limit), "--neighbor-limit", str(neighbor_limit),
    ]
    if semantic:
        args.append("--semantic")
    proc = run_cmd(args)
    print(proc.stdout, end="")

    out_dir = root / "outputs/session-start"
    report = out_dir / f"{stamp_day()}-{slugify(topic)}.md"
    latest = out_dir / "latest.md"
    body = "\n".join([
        f"# Session Start Pages - {topic}",
        "",
        f"- Generated: {iso_now()}",
        "- Boundary: report-only; no wiki pages were written.",
        f"- Command: `{' '.join(args)}`",
        "",
        "```text",
        proc.stdout.rstrip(),
        "```",
        "",
    ])
    atomic_write(report, body)
    atomic_write(latest, body)
    print(f"\nSession-start report: {report}")
    return proc.returncode


def run_nightly(root, limit):
    day = stamp_day()
    health = run_cmd(["python3", str(PM), "--root", str(root), "--mode", "health"])
    preprint = run_cmd([
        "python3", str(PM), "--root", str(root), "--mode", "preprint-status",
        "--check-online", "--limit", str(limit),
    ])
    failures = []
    if health.returncode != 0:
        failures.append("health")
    if preprint.returncode != 0:
        failures.append("preprint-status")

    report = root / f"outputs/nightly/{day}.md"
    body = "\n".join([
        f"# Nightly Wiki Gate - {day}",
        "",
        "Report-only A5 nightly job. It runs health and preprint re-checks; it does not write wiki pages.",
        "",
        f"- Generated: {iso_now()}",
        f"- Health exit code: {health.returncode}",
        f"- Preprint re-check exit code: {preprint.returncode}",
        f"- Alert emitted: {'yes' if failures else 'no'}",
        "",
        "## Health",
        "",
        "```text",
        health.stdout.rstrip(),
        "```",
        "",
        "## Preprint Re-check",
        "",
        "```text",
        preprint.stdout.rstrip(),
        "```",
        "",
    ])
    atomic_write(report, body)

    if failures:
        alert = root / f"outputs/alerts/nightly-{day}.md"
        alert_body = "\n".join([
            f"# ALERT - Nightly Wiki Gate Failed - {day}",
            "",
            f"- Failed checks: {', '.join(failures)}",
            f"- Report: `{report.relative_to(root).as_posix()}`",
            "",
            "No wiki pages were written. Human review is required.",
            "",
        ])
        atomic_write(alert, alert_body)
        print(f"Nightly hook: FAIL ({', '.join(failures)}). Alert: {alert}")
        print(f"Report: {report}")
        return 1

    print("Nightly hook: PASS. No alert emitted.")
    print(f"Report: {report}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="A5 write-safe hooks for Larry's Wiki.")
    parser.add_argument("--root", default=str(ROOT))
    sub = parser.add_subparsers(dest="command", required=True)

    inbox = sub.add_parser("inbox", help="Append new raw/inbox files to the ingest-plan queue.")
    inbox.add_argument("paths", nargs="*", help="Optional raw/inbox paths. Omit to scan all inbox files.")

    session = sub.add_parser("session-start", help="Print top relevant wiki pages for a topic via --mode ask.")
    session.add_argument("topic")
    session.add_argument("--seed-limit", type=int, default=5)
    session.add_argument("--neighbor-limit", type=int, default=8)
    session.add_argument("--semantic", action="store_true")

    nightly = sub.add_parser("nightly", help="Run health + preprint re-check; alert only on command failure.")
    nightly.add_argument("--limit", type=int, default=10, help="Preprint DOI limit for the online re-check.")

    args = parser.parse_args()
    root = Path(args.root)
    if args.command == "inbox":
        sys.exit(run_inbox(root, args.paths))
    if args.command == "session-start":
        sys.exit(run_session_start(root, args.topic, args.seed_limit, args.neighbor_limit, args.semantic))
    if args.command == "nightly":
        sys.exit(run_nightly(root, args.limit))


if __name__ == "__main__":
    main()
