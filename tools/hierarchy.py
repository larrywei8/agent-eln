"""hierarchy.py — parse compound IDs (L1 anchor + up to 2 derivation segments).

A compound ID has the shape:
    <anchor-ID>-<CODE><instance>[-<CODE><instance>]

  anchor-ID   matches the L1 numbering scheme registered in registry.py
              (PREFIX-NNNN, PREFIX-YYYY-NNNN, PREFIX-YYYY-MM-DD-NN, or PREFIX-YYYY-MM-DD).
  CODE        2-4 uppercase letters (registered in vocab.md).
  instance    optional trailing digits.

Public API:
  parse(rid)          -> dict {anchor, segments, direct_parent, depth, code, instance}
                          or None if rid is not a compound ID.
  is_compound(rid)    -> bool
  direct_parent(rid)  -> str or None (the parent = rid minus its last segment)
  anchor_of(rid)      -> str or None (the L1 anchor)
  segments_of(rid)    -> list[dict] with keys code, instance
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import registry as R

_SEGMENT = re.compile(r"^([A-Z]{2,4})(\d*)$")

# Anchor regexes for each id_style (anchored at start, unanchored at end so
# compound suffixes can trail).
_ANCHOR_PATTERNS = {
    "seq4":      re.compile(r"^([A-Z]+-\d{4,})"),
    "year-seq4": re.compile(r"^([A-Z]+-\d{4}-\d{4,})"),
    "date-nn":   re.compile(r"^([A-Z]+-\d{4}-\d{2}-\d{2}-\d{2})"),
    "date":      re.compile(r"^([A-Z]+-\d{4}-\d{2}-\d{2})"),
}


def anchor_of(rid):
    """Return the L1 anchor for rid, or None if rid does not match any known prefix."""
    prefix = R.prefix_of_id(rid)
    if not prefix:
        return None
    t, spec = R.by_prefix(prefix)
    if not spec:
        return None
    pat = _ANCHOR_PATTERNS.get(spec["id_style"])
    if not pat:
        return None
    m = pat.match(rid)
    if not m:
        return None
    anchor = m.group(1)
    # Guard against accidental over-match: the anchor must start with the exact
    # prefix + '-' (prefix_of_id already ensures this, but be defensive).
    if not anchor.startswith(prefix + "-"):
        return None
    return anchor


def _split_segments(tail):
    """Split '-CODE1-CODE2' style tails into ordered segment dicts. Returns None
    if any segment fails to parse (which would make the whole tail invalid)."""
    if not tail:
        return []
    if not tail.startswith("-"):
        return None
    out = []
    for seg in tail[1:].split("-"):
        m = _SEGMENT.match(seg)
        if not m:
            return None
        out.append({"raw": seg, "code": m.group(1), "instance": m.group(2) or ""})
    return out


def parse(rid):
    """Parse rid into anchor + segments. Returns None if rid has no compound tail
    (i.e. it is a bare anchor with no derivation segments)."""
    anchor = anchor_of(rid)
    if anchor is None:
        return None
    tail = rid[len(anchor):]
    if not tail:
        return None
    segments = _split_segments(tail)
    if segments is None:
        return None
    depth = len(segments)
    if depth == 1:
        direct_parent = anchor
    else:
        # direct parent = anchor + everything except last segment
        parent_tail = "-".join(s["raw"] for s in segments[:-1])
        direct_parent = f"{anchor}-{parent_tail}"
    last = segments[-1]
    return {
        "anchor": anchor,
        "segments": segments,
        "direct_parent": direct_parent,
        "depth": depth,
        "code": last["code"],
        "instance": last["instance"],
    }


def is_compound(rid):
    return parse(rid) is not None


def direct_parent(rid):
    p = parse(rid)
    return p["direct_parent"] if p else None


def segments_of(rid):
    p = parse(rid)
    return p["segments"] if p else []


if __name__ == "__main__":
    for rid in sys.argv[1:] or [
        "MUS-0042", "MUS-0042-BR1", "MUS-0042-BR1-RNA1",
        "PLA-0031-RE1", "SMP-2026-0189", "SMP-2026-0189-RNA1",
        "EXP-2026-07-07-01", "DAT-2026-0004-TRIM1",
    ]:
        p = parse(rid)
        print(f"{rid:35s} -> {p}")
