"""Central configuration for lab-os ELN tools.

All environment-specific values live here so nothing else has to hardcode a
user handle, email, or URL prefix. Every value can be overridden by an
environment variable; sensible defaults let the toolkit run on a fresh clone
with zero config.

Environment variables (all optional):
  LABOS_USER              -- default author for `--by` flags     (default: value of $USER or "me")
  LABOS_CONTACT_EMAIL     -- polite contact for external APIs    (default: "labos-agent@example.org")
  LABOS_WIKI_URL_PREFIX   -- URL prefix for wiki summary links   (default: "" -> emits plain path)
  LABOS_REPO_ROOT         -- absolute path to repo root          (default: auto-detected from this file)
  LABOS_WIKI_DIR          -- wiki directory name at repo root    (default: "wiki")
  LABOS_ELN_DIR           -- eln directory name at repo root     (default: "eln")
"""
import os

# tools/ -> eln/ -> repo root
_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_ELN_ROOT = os.path.dirname(_HERE)
_DEFAULT_REPO_ROOT = os.path.dirname(_DEFAULT_ELN_ROOT)

REPO_ROOT     = os.environ.get("LABOS_REPO_ROOT", _DEFAULT_REPO_ROOT)
ELN_DIR       = os.environ.get("LABOS_ELN_DIR", "eln")
WIKI_DIR      = os.environ.get("LABOS_WIKI_DIR", "wiki")
ELN_ROOT      = os.path.join(REPO_ROOT, ELN_DIR)
WIKI_ROOT     = os.path.join(REPO_ROOT, WIKI_DIR)

USER          = os.environ.get("LABOS_USER") or os.environ.get("USER") or "me"
CONTACT_EMAIL = os.environ.get("LABOS_CONTACT_EMAIL", "labos-agent@example.org")
WIKI_URL_PREFIX = os.environ.get("LABOS_WIKI_URL_PREFIX", "").rstrip("/")


def wiki_url(rel_path: str) -> str:
    """Build a URL to a wiki file at a repo-relative path.

    If LABOS_WIKI_URL_PREFIX is set (e.g. https://your-host.example.com/?f=),
    the path is appended URL-encoded. Otherwise the plain repo-relative path
    is returned so the tool still produces useful output for local use.
    """
    from urllib.parse import quote
    if WIKI_URL_PREFIX:
        return f"{WIKI_URL_PREFIX}{quote(rel_path, safe='')}"
    return rel_path
