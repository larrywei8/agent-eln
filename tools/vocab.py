"""vocab.py — parse vocab.md (controlled vocabulary + segment codes).

Reads /home/workspace/Projects/ELN/vocab.md at import time and exposes:

  SAMPLE_TYPES       set[str]   — allowed sample_type values
  SOURCE_TISSUES     set[str]   — allowed source_tissue values
  ORGANISMS          set[str]   — allowed organism values
  PRESERVATIONS      set[str]   — allowed preservation values
  SEGMENT_CODES      set[str]   — all registered compound-ID segment codes (uppercase)

If vocab.md is missing, everything is empty and validators treat it as "no
controlled vocabulary defined" — nothing breaks, no warnings fire.

Parsing rules (kept simple on purpose):
- Under `## sample_type` / `## source_tissue` / `## organism` / `## preservation`
  headers, every ``code``-quoted token is a value. Stops at the next `##` header.
- Under `## Segment codes` and its subsections, every markdown table row whose
  first cell is a 2–4 uppercase-letter token registers that code.
"""
import os
import re

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VOCAB_PATH = os.path.join(_ROOT, "vocab.md")

_BACKTICK = re.compile(r"`([^`\n]+)`")
_TABLE_ROW = re.compile(r"^\s*\|\s*([A-Z]{2,4})\s*\|")
_H2 = re.compile(r"^##\s+(.+?)\s*$")


def _collect_backtick_tokens(lines, start_idx):
    """Collect backtick-quoted tokens under a section until the next `## ` heading.
    Skips blockquote lines (they contain notes about field names, not values)."""
    out = set()
    for line in lines[start_idx + 1:]:
        if _H2.match(line):
            break
        if line.lstrip().startswith(">"):
            continue
        for m in _BACKTICK.finditer(line):
            tok = m.group(1).strip()
            if tok:
                out.add(tok)
    return out


def _parse():
    if not os.path.exists(_VOCAB_PATH):
        return set(), set(), set(), set(), set()
    with open(_VOCAB_PATH, encoding="utf-8") as f:
        lines = f.read().splitlines()

    sample_types = source_tissues = organisms = preservations = set()
    segment_codes = set()
    in_segments = False

    for i, line in enumerate(lines):
        h = _H2.match(line)
        if h:
            title = h.group(1).lower()
            in_segments = "segment codes" in title
            if title.startswith("sample_type"):
                sample_types = _collect_backtick_tokens(lines, i)
            elif title.startswith("source_tissue"):
                source_tissues = _collect_backtick_tokens(lines, i)
            elif title.startswith("organism"):
                organisms = _collect_backtick_tokens(lines, i)
            elif title.startswith("preservation"):
                preservations = _collect_backtick_tokens(lines, i)
            continue

        if in_segments:
            m = _TABLE_ROW.match(line)
            if m:
                code = m.group(1)
                if code != "CODE":  # skip the literal table-header cell
                    segment_codes.add(code)

    return sample_types, source_tissues, organisms, preservations, segment_codes


SAMPLE_TYPES, SOURCE_TISSUES, ORGANISMS, PRESERVATIONS, SEGMENT_CODES = _parse()


if __name__ == "__main__":
    print(f"vocab.md: {_VOCAB_PATH}")
    print(f"  sample_type    : {len(SAMPLE_TYPES)}   {sorted(SAMPLE_TYPES)[:6]}...")
    print(f"  source_tissue  : {len(SOURCE_TISSUES)} {sorted(SOURCE_TISSUES)[:6]}...")
    print(f"  organism       : {len(ORGANISMS)}      {sorted(ORGANISMS)}")
    print(f"  preservation   : {len(PRESERVATIONS)}  {sorted(PRESERVATIONS)}")
    print(f"  segment codes  : {len(SEGMENT_CODES)}  {sorted(SEGMENT_CODES)}")
