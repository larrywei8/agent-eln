# eln/raw/

Raw sequencer output, imaging data, instrument dumps. **Gitignored by default.**

Point your `raw/` at large-file storage (git-annex, DVC, S3, a NAS mount) rather than
committing binaries. The `.gitignore` at the repo root keeps this directory tracked
(via `README.md` and `.gitkeep`) but skips everything else inside it.
