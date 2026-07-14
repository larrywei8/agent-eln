#!/usr/bin/env python3
"""Generate a project literature-evidence view from optional relation metadata."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import records
import registry as R


def build(project_id, root=None):
    groups = {key: [] for key in sorted(R.LIT_RELATIONS)}
    groups["unclassified"] = []
    for _path, rel, meta, _body in records.iter_records(root):
        if meta.get("type") != "literature":
            continue
        projects = records.reference_values(meta.get("related_projects"))
        if isinstance(meta.get("project"), str):
            projects.append(meta["project"])
        if project_id not in projects:
            continue
        relation = meta.get("relation")
        relations = records.reference_values(relation) if isinstance(relation, list) else ([relation] if relation else [])
        known = [value for value in relations if value in R.LIT_RELATIONS]
        keys = known or ["unclassified"]
        row = {"id": meta.get("id"), "title": meta.get("title", ""), "path": rel,
               "relation": relations, "why_it_matters": meta.get("why_it_matters", "")}
        for key in keys:
            groups[key].append(row)
    return {"project": project_id, "groups": groups,
            "count": len({row["id"] for values in groups.values() for row in values})}


def main():
    parser = argparse.ArgumentParser(description="Group project literature by optional typed relation.")
    parser.add_argument("project_id")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = build(args.project_id)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(f"# Evidence for {args.project_id}\n")
    for relation, rows in payload["groups"].items():
        if not rows:
            continue
        print(f"## {relation}\n")
        for row in rows:
            note = f" — {row['why_it_matters']}" if row["why_it_matters"] else ""
            print(f"- {row['id']}: {row['title']}{note}")
        print()


if __name__ == "__main__":
    main()
