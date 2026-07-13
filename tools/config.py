"""Central configuration for agent-eln tools.

All environment-specific values live here so nothing else has to hardcode a
user handle, email, or URL prefix. Every value can be overridden by an
environment variable; sensible defaults let the toolkit run on a fresh clone
with zero config.

Environment variables (all optional):
  AGENT_ELN_USER              -- default author for `--by` flags     (default: value of $USER or "me")
  AGENT_ELN_CONTACT_EMAIL     -- polite contact for external APIs    (default: "agent-eln@example.org")
  AGENT_ELN_WIKI_URL_PREFIX   -- URL prefix for wiki summary links   (default: "" -> emits plain path)
  AGENT_ELN_REPO_ROOT         -- absolute path to repo root          (default: auto-detected from this file)
  AGENT_ELN_ELN_DIR           -- eln (activities) directory name     (default: "eln")
  AGENT_ELN_LIMS_DIR          -- lims (inventory) directory name     (default: "lims")
  AGENT_ELN_METHODS_DIR       -- methods (how-to) directory name     (default: "methods")
  AGENT_ELN_WIKI_DIR          -- wiki directory name                 (default: "wiki")
"""
import os

# tools/ sits at the repo root, so REPO_ROOT = tools/'s parent.
_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_REPO_ROOT = os.path.dirname(_HERE)

REPO_ROOT   = os.environ.get("AGENT_ELN_REPO_ROOT", _DEFAULT_REPO_ROOT)
ELN_DIR     = os.environ.get("AGENT_ELN_ELN_DIR",     "eln")
LIMS_DIR    = os.environ.get("AGENT_ELN_LIMS_DIR",    "lims")
METHODS_DIR = os.environ.get("AGENT_ELN_METHODS_DIR", "methods")
WIKI_DIR    = os.environ.get("AGENT_ELN_WIKI_DIR",    "wiki")
ELN_ROOT     = os.path.join(REPO_ROOT, ELN_DIR)
LIMS_ROOT    = os.path.join(REPO_ROOT, LIMS_DIR)
METHODS_ROOT = os.path.join(REPO_ROOT, METHODS_DIR)
WIKI_ROOT    = os.path.join(REPO_ROOT, WIKI_DIR)

USER          = os.environ.get("AGENT_ELN_USER") or os.environ.get("USER") or "me"
CONTACT_EMAIL = os.environ.get("AGENT_ELN_CONTACT_EMAIL", "agent-eln@example.org")
WIKI_URL_PREFIX = os.environ.get("AGENT_ELN_WIKI_URL_PREFIX", "").rstrip("/")


def wiki_url(rel_path: str) -> str:
    """Build a URL to a wiki file at a repo-relative path.

    If AGENT_ELN_WIKI_URL_PREFIX is set (e.g. https://your-host.example.com/?f=),
    the path is appended URL-encoded. Otherwise the plain repo-relative path
    is returned so the tool still produces useful output for local use.
    """
    from urllib.parse import quote
    if WIKI_URL_PREFIX:
        return f"{WIKI_URL_PREFIX}{quote(rel_path, safe='')}"
    return rel_path
