"""Canonical record discovery and safe I/O for agent-eln tools."""
from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator

import fm
import registry as R


def iter_record_paths(root: str | None = None) -> Iterator[str]:
    root = os.path.abspath(root or R.ROOT)
    paths = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        if R.is_excluded(dirpath):
            dirnames[:] = []
            continue
        for filename in sorted(filenames):
            if filename.endswith(".md"):
                paths.append(os.path.join(dirpath, filename))
    yield from sorted(paths)


def load_record(path: str):
    meta, body = fm.parse(path)
    return meta, body


def iter_records(root: str | None = None):
    base = os.path.abspath(root or R.ROOT)
    for path in iter_record_paths(base):
        meta, body = load_record(path)
        yield path, os.path.relpath(path, base), meta, body


def find_record(record_id: str, root: str | None = None):
    for path, _rel, meta, _body in iter_records(root):
        if meta.get("id") == record_id:
            return path, meta
    return None, None


def existing_ids(record_type: str, root: str | None = None):
    return [meta["id"] for _path, _rel, meta, _body in iter_records(root)
            if meta.get("type") == record_type and meta.get("id")]


def reference_values(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def extract_edges(meta):
    source = meta.get("id")
    if not source:
        return []
    return [{"src": source, "dst": target, "rel": field}
            for field in R.FORWARD_REF_FIELDS
            for target in reference_values(meta.get(field))
            if R.prefix_of_id(target)]


def atomic_write(path: str, text: str):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".agent-eln-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
