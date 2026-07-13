#!/usr/bin/env python3
"""trace.py — trace ancestor + descendant chains for any record ID.

Reads index/graph.json (rebuild with `python tools/index.py` first) and walks
the provenance graph. Ancestors follow forward relations from the target
outward (derived_from, produced_in, used_resources, ...); descendants follow
the reverse direction.

Usage:
  python tools/trace.py <ID>                       # both directions, depth 6
  python tools/trace.py <ID> --up-only             # ancestors only
  python tools/trace.py <ID> --down-only           # descendants only
  python tools/trace.py <ID> --depth 3             # limit depth
  python tools/trace.py <ID> --json                # machine-readable output
"""
import argparse
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
import registry as R

ROOT = R.ROOT
GRAPH = os.path.join(ROOT, "index", "graph.json")

# Relations that mean "this record derives from / was produced from / used
# these upstream records". Following these edges forward = walking up.
UP_RELS = {"derived_from", "produced_in", "used_resources", "inputs",
           "protocols", "pipeline", "scripts", "instrument"}
# Backlink (auto) edges have "(auto)" suffix — we ignore them (redundant).


def load_graph():
    if not os.path.exists(GRAPH):
        print(f"❌ {os.path.relpath(GRAPH, ROOT)} not found. Run `python tools/index.py` first.")
        sys.exit(1)
    with open(GRAPH) as f:
        return json.load(f)


def build_adjacency(edges):
    """Return two dicts:
        forward[src] = list of (dst, rel)  — edges as declared
        reverse[dst] = list of (src, rel)  — edges reversed
    Ignores '(auto)' backlink edges to avoid double-counting."""
    forward = defaultdict(list)
    reverse = defaultdict(list)
    for e in edges:
        rel = e["rel"]
        if rel.endswith("(auto)"):
            continue
        forward[e["src"]].append((e["dst"], rel))
        reverse[e["dst"]].append((e["src"], rel))
    return forward, reverse


def walk(start, adj, up_rels, direction, max_depth):
    """BFS from start, following only edges with rel in up_rels when direction=='up',
    or the reverse relation when direction=='down'.

    Actually simpler: adj is already directional. When direction=='up' we take
    adj=forward and filter to up_rels; when direction=='down' we take adj=reverse
    and filter to up_rels (a descendant is a record whose forward up-relation
    points at us)."""
    visited = {start: 0}
    order = []
    frontier = [(start, 0)]
    while frontier:
        node, depth = frontier.pop(0)
        if depth >= max_depth:
            continue
        for nxt, rel in adj.get(node, []):
            if rel not in up_rels:
                continue
            if nxt in visited:
                continue
            visited[nxt] = depth + 1
            order.append((nxt, depth + 1, node, rel))
            frontier.append((nxt, depth + 1))
    return order


def find_node(nodes, rid):
    for n in nodes:
        if n["id"] == rid:
            return n
    return None


def format_node(nodes_by_id, rid):
    n = nodes_by_id.get(rid)
    if not n:
        return f"{rid}  (not indexed)"
    label = n.get("name") or ""
    return f"{rid:30s} {n.get('type', '?'):12s} {label}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id", help="Record ID to trace.")
    ap.add_argument("--up-only", action="store_true", help="Only walk ancestors.")
    ap.add_argument("--down-only", action="store_true", help="Only walk descendants.")
    ap.add_argument("--depth", type=int, default=6, help="Max walk depth (default 6).")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    a = ap.parse_args()

    g = load_graph()
    nodes_by_id = {n["id"]: n for n in g["nodes"]}
    forward, reverse = build_adjacency(g["edges"])

    if a.id not in nodes_by_id:
        print(f"❌ {a.id} not found in index. Rebuild with `python tools/index.py`.")
        sys.exit(1)

    do_up = not a.down_only
    do_down = not a.up_only
    ancestors = walk(a.id, forward, UP_RELS, "up", a.depth) if do_up else []
    descendants = walk(a.id, reverse, UP_RELS, "down", a.depth) if do_down else []

    if a.json:
        out = {
            "id": a.id,
            "node": nodes_by_id.get(a.id),
            "ancestors": [{"id": rid, "depth": d, "via": parent, "rel": rel}
                          for rid, d, parent, rel in ancestors],
            "descendants": [{"id": rid, "depth": d, "via": parent, "rel": rel}
                            for rid, d, parent, rel in descendants],
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    print(f"┃ {format_node(nodes_by_id, a.id)}")
    if do_up:
        if ancestors:
            print(f"\n▲ Ancestors ({len(ancestors)})")
            for rid, d, parent, rel in ancestors:
                indent = "  " * d
                print(f"  {indent}└─ {format_node(nodes_by_id, rid)}   [{rel} of {parent}]")
        else:
            print("\n▲ Ancestors: none")
    if do_down:
        if descendants:
            print(f"\n▼ Descendants ({len(descendants)})")
            for rid, d, parent, rel in descendants:
                indent = "  " * d
                print(f"  {indent}└─ {format_node(nodes_by_id, rid)}   [{rel} <- {parent}]")
        else:
            print("\n▼ Descendants: none")


if __name__ == "__main__":
    main()
