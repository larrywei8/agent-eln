# agent-eln — 3-minute roadshow pitch

**Runtime target**: 3:00 exactly (~435 words at 145 wpm)
**Format**: HyperFrames HTML-as-video. One sentence ≈ one frame beat.
**Voice**: Larry's cloned voice via ListenHub. SRT drives frame timing.
**Style**: BlockFrame — cream paper, dot grid, mint + hot-pink highlighter blocks.

---

## SCENE 1 — The paper problem (0:00–0:18, ~43 words)

> Every wet lab still runs on paper.
> Handwrite. Print the gel. Cut. Tape it in.
> Six months later — which mouse? Which plasmid? Which lane?
> The details are gone.
> When the postdoc leaves, the lab loses its memory.

**Visual**: paper notebook, tape, scissors, faded gel photo. Kicker: `THE PROBLEM · 01`.

---

## SCENE 2 — The digital notebook trap (0:18–0:36, ~43 words)

> Then came the digital ELN. OneNote. Benchling.
> You type instead of write. Paste screenshots instead of gels.
> Faster. Cleaner. Still broken.
> The notebook is **flat**.
> No link from the experiment to the plasmid. No link from the plasmid to the paper.
> Every trace is a search bar.

**Visual**: OneNote-style page with orphaned screenshot, broken chain overlay. Highlighter on `flat`.

---

## SCENE 3 — The premise (0:36–0:52, ~39 words)

> I'm building **agent-eln** — an AI-native lab operating system.
> One repo. Four blocks. Every resource **auto-labeled**. Every link **automatic**.
> No database. No cloud lock-in. Just Markdown and git.
> The AI is the primary user. Every result — traceable.

**Visual**: four blocks light up. Terminal: `git clone agent-eln`.

---

## SCENE 4 — The four blocks (0:52–1:07, ~35 words)

> Under the hood — four blocks. One repo.
> **LIMS. METHODS. ELN. WIKI.**
> Four folders. Every file linked to every other file that references it.
> Let me show you what each one holds.

**Visual**: four highlighter cards land in a 2×2 grid — `LIMS · PLA-0042`, `METHODS · SOP-0011`, `ELN · EXP-0117`, `WIKI · REF-0203`.

---

## SCENE 4A — LIMS deep dive (1:07–1:23, ~38 words)

> **LIMS** logs what you *have*.
> Plasmid on the bench. Mouse in the cage. Reagent in the freezer.
> Snap a photo of the label. Point at a cage tag.
> Each item gets a unique ID. Instant inventory. Zero forms.

**Visual**: three polaroid cards slide in — PLA-0042, MUS-0088, RGT-0114. Mint highlighter "Snap a photo. It's registered."

---

## SCENE 4B — METHODS deep dive (1:23–1:37, ~34 words)

> **METHODS** logs what you *know*.
> SOPs. Analysis pipelines. Scripts you author and reuse.
> Author once — every future experiment reaches for the same file.
> Every method is versioned. Every rerun reproducible.

**Visual**: lime-header terminal listing `SOP-0011.md`, `PIP-0004.py`, `SCR-0022.R`, `SOP-0033.md`. Lime highlighter "Author once. Reuse forever."

---

## SCENE 4C — ELN deep dive (1:37–1:57, ~48 words)

> **ELN** logs what *happened*.
> Every experiment. Every analysis. Every meeting. Every paper you read.
> Describe your day — "run mini-prep on PLA-0042."
> agent-eln finds the plasmid in LIMS, loads the protocol from METHODS, mints a new experiment ID, and stamps every sample it will produce.
> An append-only ledger the AI can reason over.

**Visual**: pink-header agent terminal showing 7 lines: Found PLA-0042 · Loaded SOP-0011 · Created EXP-0117 · Minted SMP-0245 · Linked 4 ancestors 1 descendant.

---

## SCENE 4D — WIKI deep dive (1:57–2:13, ~38 words)

> **WIKI** logs what you *learned* from others.
> Drop a PDF. A photo of a poster. A GitHub repo. A website.
> llm-wiki ingests it, extracts concepts and entities, and stitches them into a personal knowledge base.

**Visual**: four source cards — PDF, POSTER, GITHUB, WEBSITE — funnel arrows into a pink `llm-wiki` hub. Cyan highlighter "Ingest anything. Build your brain."

---

## SCENE 5 — The daily loop (2:13–2:33, ~48 words)

> This is the day.
> You describe. Agent assembles.
> Finds the plasmids, mice, reagents in your LIMS.
> Pulls the right protocol from METHODS.
> Writes the plan into your ELN.
> Mints IDs for every new sample, every gel, every dataset.
> Auto-links every resource to its ancestors.
> Nothing orphaned. Every result — traceable.

**Visual**: terminal typing → graph auto-draws between LIMS/METHOD/ELN nodes.

---

## SCENE 6 — Why now (2:33–2:48, ~36 words)

> Legacy ELNs were built for humans clicking forms.
> They can't hand context to an AI.
> agent-eln flips the model.
> The file system **is** the database.
> `git log` is your timeline. Every commit — a snapshot of the entire lab.

**Visual**: git log scrolling, folder tree at three different dates.

---

## SCENE 7 — Traction + ask (2:48–3:00, ~33 words)

> It's already running my UCSD lab.
> Mouse colony, sequencing, literature ingest — one repo. 117 tests green.
> agent-eln is open source. MIT. Runs on a laptop.
> The next breakthrough will be co-authored by an AI. Come build it with me.

**Visual**: GitHub URL + MIT badge. `github.com/…/agent-eln`.

---

## Delivery notes

- Pace to **145 wpm** — a touch faster than casual, gives urgency without rushing.
- One-sentence-per-frame keeps HyperFrames SRT clean.
- **Cold-open** the paper pain. No logo, no title card until Scene 3.
- **Scene 4** is a fast family portrait — 15 seconds, all four cards on screen.
- **Deep dives** (4A–4D) hold each block for 14–20 seconds — this is where you *sell* each module.
- **Scene 5** is the magic reveal. Type the description live; let the graph auto-draw.
- Save the URL for the final 5 seconds.
- Sentences under 12 words. Verbs first.
- Use `.hl` (mint / lime / cyan) for **capabilities** (`auto-labeled`, `automatic`, `traceable`, `registered`, `reuse forever`).
- Use `.hl.pink` for **pain** (`flat`, `gone`, `broken`) and **the ELN block name**.

## Word count

| Scene | Runtime | Words |
|---|---|---|
| 1 — Paper problem | 0:18 | 43 |
| 2 — Digital trap | 0:18 | 43 |
| 3 — Premise | 0:16 | 39 |
| 4 — Four blocks overview | 0:15 | 35 |
| 4A — LIMS deep dive | 0:16 | 38 |
| 4B — METHODS deep dive | 0:14 | 34 |
| 4C — ELN deep dive | 0:20 | 48 |
| 4D — WIKI deep dive | 0:16 | 38 |
| 5 — Daily loop | 0:20 | 48 |
| 6 — Why now | 0:15 | 36 |
| 7 — Traction + ask | 0:12 | 33 |
| **Total** | **3:00** | **~435** |
