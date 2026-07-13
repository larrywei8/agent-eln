"""Minimal YAML frontmatter parser + single-field writer (standard library only).

Parsing (`parse`) supports: scalars, [inline lists], `- ` block lists, and inline
comments after ` #` in unquoted values. Quoted values are preserved as-is.
Nested maps (indented) are not indexed and simply ignored.

Single-field writer (`set_field`) is block-list aware:
- If value is str/int/None -> single-line `key: value` replacement;
- If value is list -> preserves the file's existing style (block/inline); new fields default to block;
- If the field was previously block and the new value is still str, subsequent `- ` items are removed and a single-line scalar is written;
- If the field does not exist, it is inserted right after the `type:` line (or appended to the end of frontmatter if not found).

This is not a full YAML round-trip: comments, anchors, and complex nesting are out of scope. Everyday ELN
frontmatter only uses flat keys + three value shapes (scalar/inline list/block list); this covers 100% of that
and keeps file bytes stable (does not touch other fields).
"""
import re

# ---------- Parsing ----------

def _clean(v):
    v = v.strip()
    if v[:1] in ("'", '"'):
        return v.strip("'\"")
    if v.startswith("#"):
        return ""
    i = v.find(" #")
    if i != -1:
        v = v[:i].rstrip()
    return v

def parse(path):
    with open(path, encoding="utf-8") as f:
        txt = f.read()
    if not txt.startswith("---"):
        return {}, txt
    end = txt.find("\n---", 3)
    if end == -1:
        return {}, txt
    head, body = txt[3:end], txt[end + 4:]
    meta = {}
    key = None
    for line in head.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        m = re.match(r"^(\w[\w\-]*):\s*(.*)$", line)
        if m:
            key = m.group(1)
            val = _clean(m.group(2))
            if val.startswith("[") and val.endswith("]"):
                meta[key] = [x.strip().strip("'\"") for x in val[1:-1].split(",") if x.strip()]
            elif val == "":
                meta[key] = []
            else:
                meta[key] = val
        elif line.strip().startswith("- ") and key:
            if not isinstance(meta.get(key), list):
                meta[key] = []
            meta[key].append(_clean(line.strip()[2:]))
    return meta, body


# ---------- Single-field writer ----------

def _split(txt):
    """Return (head, sep, rest); head is the content between the first --- and the next \\n---
    (excluding the ---). sep is '\\n---', rest is the body after sep (including leading '\\n')."""
    if not txt.startswith("---"):
        return None
    end = txt.find("\n---", 3)
    if end == -1:
        return None
    return txt[3:end], "\n---", txt[end + 4:]

def _find_block(head, key):
    """Locate the full block range for key in head (key line + subsequent indented `- ` items).
    Returns (start, end, m_key_line) or None."""
    m = re.search(rf"(?m)^{re.escape(key)}:[ \t]*(.*)$", head)
    if not m:
        return None
    # Probe subsequent block `- ` items: start scanning after the newline of the key line.
    # The consumed items do not include the final newline, so after the caller's replacement
    # head[end:] naturally starts with \n and no extra concatenation is needed.
    end = m.end()
    scan = end
    if scan < len(head) and head[scan] == "\n":
        scan += 1
    while True:
        # Find the end of the next line
        nl = head.find("\n", scan)
        line = head[scan:] if nl == -1 else head[scan:nl]
        if not re.match(r"^[ \t]+-[ \t]", line):
            break
        # Consume this `- ` item + the newline before it
        end = nl if nl != -1 else len(head)
        if nl == -1:
            break
        scan = nl + 1
    return m.start(), end, m

def _render(key, value, style="block"):
    """Render value as a frontmatter fragment (no surrounding newlines). style only applies to lists."""
    if value is None:
        return f"{key}:"
    if isinstance(value, (list, tuple)):
        if not value:
            return f"{key}: []"
        if style == "inline":
            inner = ", ".join(_scalar(x) for x in value)
            return f"{key}: [{inner}]"
        lines = [f"{key}:"] + [f"  - {v}" for v in value]
        return "\n".join(lines)
    return f"{key}: {value}"

def _scalar(x):
    s = str(x)
    if any(c in s for c in ":#,[]{}") or s.strip() != s:
        return f'"{s}"'
    return s

def set_field(txt, key, value):
    """Set key to value in the frontmatter of txt, handling 4 cases:
    - key does not exist -> insert after the `type:` line (or at end of frontmatter);
    - key is a block list -> replace the entire block with the new value;
    - key is an inline list -> replace inline with the new value;
    - key is a scalar -> single-line replacement.
    When value is a list, if the original field was block-style it remains block; new/originally-scalar fields default to block.
    """
    parts = _split(txt)
    if parts is None:
        return txt  # Not a frontmatter file, no change
    head, sep, rest = parts

    loc = _find_block(head, key)
    if loc is None:
        # Insert after the type: line; if not found, append to end of head
        m_type = re.search(r"(?m)^type:.*$", head)
        style = "block" if isinstance(value, (list, tuple)) else "scalar"
        rendered = _render(key, value, "block")
        if m_type:
            new_head = head[:m_type.end()] + "\n" + rendered + head[m_type.end():]
        else:
            new_head = head.rstrip() + "\n" + rendered + "\n"
        return "---" + new_head + sep + rest

    start, end, m = loc
    # Determine original style (block vs inline vs scalar)
    key_line_val = m.group(1).strip()
    has_block_items = end > m.end()  # Consumed `- ` items after the key line
    original_style = "block" if has_block_items else ("inline" if key_line_val.startswith("[") else "scalar")

    if isinstance(value, (list, tuple)):
        style = "inline" if original_style == "inline" else "block"
    else:
        style = "scalar"

    rendered = _render(key, value, style)
    new_head = head[:start] + rendered + head[end:]
    return "---" + new_head + sep + rest


def get_field(txt, key):
    """Read a single field (semantic frontmatter parse, including block lists)."""
    parts = _split(txt)
    if parts is None:
        return None
    head, _, _ = parts
    loc = _find_block(head, key)
    if loc is None:
        return None
    start, end, m = loc
    inline = m.group(1).strip()
    if end > m.end():
        # Block-style: extract text after each `- `
        items = []
        for line in head[m.end():end].splitlines():
            item = line.strip()
            if item.startswith("- "):
                items.append(_clean(item[2:]))
        return items
    if inline.startswith("[") and inline.endswith("]"):
        return [x.strip().strip("'\"") for x in inline[1:-1].split(",") if x.strip()]
    if inline == "":
        return None
    return _clean(inline)


def dump(path, txt):
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
