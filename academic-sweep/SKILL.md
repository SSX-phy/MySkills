---
name: academic-sweep
description: >
  Topic exploration via citation-network walk. Anchors on one or more node papers,
  walks backward and (best-effort) forward citations with topical filtering, and
  writes report.md (synthesis) plus corpus.md (audit table) into the user-confirmed
  output folder. WebSearch + WebFetch only — no API keys needed.
  Usage (invoked by the academic-explorer subagent):
    topic="<topic>" entry_point=<E1|E2|E3> seed="<arxiv-id|DOI|path|notes-folder>" output_folder="<path>"
when_to_use: >
  Invoked by the academic-explorer subagent for Pattern A topic exploration. Three
  entry points: E1 topic-only (start from keyword), E2 seed-paper supplied (skip
  to citation walk), E3 partial corpus supplied (skip to enrichment / gap analysis).
allowed-tools: WebSearch, WebFetch, Read, Write, Edit, Bash, Glob, Grep, TodoWrite
---

# Academic Sweep Skill

Topic exploration via citation-network walk. Inputs come as a string in `$ARGUMENTS` of the form:

```
topic="..." entry_point=<E1|E2|E3> seed="..." output_folder="..."
```

`seed` is optional for E1, required for E2 and E3.

## Operating principles (inherit from `academic-explorer` subagent)

1. Cite with a clickable link, **journal/DOI preferred** over arXiv. If both exist, cite the journal version and note the arXiv ID parenthetically only if useful for open access.
2. No fabrication — never invent authors, titles, journals, years, numbers, or URLs.
3. Distinguish **read** (you actually fetched it) from **inferred** (you only saw the abstract or a search snippet).
4. Confirm output paths before writing. Never assume.
5. Do **not** auto-download PDFs. Ask the user before fetching any PDF.

## Key-points template (adaptive — discovered from the node)

Coherent same-topic papers tend to report a common set of "key points." This skill does **not** fix that set in advance. It starts with two hints, discovers topic-specific extras from the node paper(s) in Step 2, and may extend the set during Step 4 as patterns recur.

**Seed hints (always extracted):**

1. **Research method** — one phrase. If the method is an algorithm, include the **key parameters** that distinguish this run from a generic application (e.g., "DMRG with bond dimension 2000 on 2D Hubbard at U/t=8", "diffusion-map embedding with σ self-tuned per neighborhood").
2. **Quantities used to show the result** — the central observables/metrics reported (e.g., "ground-state energy per site, spin gap", "bit error rate vs. SNR", "ROC AUC on dataset X").

**Discovered key points (added in Step 2):** after reading the node paper(s), name 2–4 additional fields that the node foregrounds and that you'd expect coherent same-topic papers to also report. Examples: a defining regime or limit, a benchmark dataset or system, a characteristic parameter the community tracks. Write the resulting field set into the "Key points template" block at the top of `corpus.md`.

**Template extension (during Step 4):** if a new key point emerges in ≥2 hop-1 neighbors and isn't in the template, **add it** and back-fill earlier rows where the abstract supports it. Note the addition in `corpus.md` so the user can see the template grew.

**Use as the investigation lens.** Once the template is set in Step 2, every subsequent paper read in Steps 4 and 5 is evaluated **field-by-field** against it. Do not skip a field just because the abstract doesn't volunteer it — explicitly check, and write `?` if missing. The template also drives the report: Step 6 surfaces it as the top-level section of `report.md`.

For any field a paper's abstract does not address, mark it `?` rather than guessing.

## Known limitation — forward citations are best-effort

This skill uses WebSearch + WebFetch only, no structured API. Backward citations (what the node cites) are reliable when the user shares the PDF or the journal page exposes a reference list. **Forward citations (what cites the node) are best-effort:** Google Scholar is typically not accessible to headless fetches, and most journal pages only show backward references. The skill leans on (a) review papers that name later work, (b) topic-keyword searches in recent years, and (c) CrossRef "Cited by" widgets when the journal exposes them. Document any incompleteness in `report.md`.

## Entry-point routing

| Entry point | What the user gave | Start at | Skip                    |
|-------------|--------------------|----------|-------------------------|
| **E1**      | Topic only         | Step 1   | —                       |
| **E2**      | Seed paper (arXiv ID, DOI, or PDF path) | Step 2 | Step 1 (treat seed as the node) |
| **E3**      | Partial corpus (folder of notes or list of papers) | Step 3 | Steps 1–2 (ingest supplied papers as nodes / hop-1 neighbors; pick the most-cited as the walk anchor) |

---

## Step 0 — Parse arguments and confirm output folder

Parse `$ARGUMENTS` into `topic`, `entry_point`, `seed`, `output_folder`. If `output_folder` is missing, empty, or the directory doesn't exist, **stop and ask the user** to confirm a path. Do not silently create one.

Initialise `<output_folder>/corpus.md` with this header:

```markdown
# Corpus — <topic>

| Title | Authors | Venue | Year | Link | Cites | Role | Hop | Notes |
|-------|---------|-------|------|------|-------|------|-----|-------|
```

`role` ∈ {node, neighbor, dropped}. `hop` ∈ {0 for node, 1, 2}. `Notes` carries the kept-or-dropped reason.

Below the table, reserve a stub for the topic's key-points template that Step 2 will fill in:

```markdown
## Key points template — <topic>

*(To be filled by Step 2 after reading the node paper(s). May be extended in Step 4.)*

1. Research method (& key params): _seed hint_
2. Quantities used to show the result: _seed hint_
3. _topic-specific key point — added in Step 2_
4. _topic-specific key point — added in Step 2_
```

Below that, each paper that is **kept** (node or neighbor) gets a per-paper extraction block in this shape:

```markdown
### <Short title> — <role>, hop=<N> — [link](https://doi.org/...)
- **Method (& key params):** ...
- **Quantities:** ...
- **<discovered key point 1>:** ...
- **<discovered key point 2>:** ...
- **Relation to node:** ...   <!-- neighbors only -->
```

Dropped papers stay only as table rows (no extraction block) — the table row plus the drop reason in `Notes` is enough.

Use `TodoWrite` to track Steps 1–8 so the user sees progress on long sweeps.

---

## Step 1 — Find node paper(s)  *(E1 only)*

Run three WebSearch passes; collect 5–10 unique candidate papers across them:

1. `<topic> review article OR survey` — review papers tend to name foundational works.
2. `<topic> site:journals.aps.org OR site:nature.com OR site:science.org` — restrict to top venues.
3. `<topic> seminal OR foundational OR "first to"` — surface community framing.

Score each candidate by:

- **Venue rank.** Top tier (Nature, Science, PRL, RMP, Annals of Math, top field-specific journals like JHEP / ApJ / IEEE flagship transactions) → +3. Mid-tier journal → +1. Conference proceedings → +1. arXiv-only → 0 unless clearly the live frontier with no published equivalent.
- **"Seminal" framing.** Explicitly named as foundational by a review hit → +2.
- **Independent mentions.** Surfaced by ≥2 of the three searches → +1.
- **Recency tiebreaker** only — do not prefer recent over high-impact older.

Present the top 3–5 to the user with one-line justifications (`<title> — <venue> <year>, score X (venue+seminal+mentions)`) and ask which 1–2 to use as nodes. Do not proceed without confirmation.

---

## Step 2 — Read node paper(s)  *(E1, E2)*

For each chosen node, WebFetch the journal abstract page (DOI link preferred, arXiv abstract as fallback). Then:

1. Fill the two **seed hints** (method + key params, quantities) — see the *Key-points template* section above.
2. Identify 2–4 **topic-specific key points** the node foregrounds that you'd expect coherent same-topic papers to also report. Write the full field set into the "Key points template" block at the top of `corpus.md`, then write the node's per-paper extraction block (see Step 0 for the block format).

If the abstract is too thin to identify topic-specific points (or you need the full reference list), **ask the user** before fetching the PDF. If they OK it, use `Read` on the PDF to fill the missing fields and to extract the bibliography for Step 3-backward.

Tag the entry `role=node, hop=0`.

---

## Step 3 — Walk the citation graph  *(all entry points)*

Two sub-steps, run per node:

### 3a. Backward (references the node cites)

Source order:

1. If user provided / approved the PDF: extract the bibliography directly.
2. Else: WebFetch the journal abstract page — many journals (APS, Nature, Elsevier) list references inline.
3. Else: ask the user to paste the bibliography.

For each reference, do a one-shot WebSearch on `<title> <first-author>` and WebFetch the resulting abstract page to recover title + venue + abstract.

### 3b. Forward (papers citing the node) — *best-effort*

Try in order:

1. WebFetch the node's journal abstract page and look for a CrossRef "Cited by" widget.
2. WebSearch for the exact title in quotes: `"<node-paper-title>"`. Citers often quote the title.
3. WebSearch in the most recent 2–3 years: `<topic-keyword> <node-author> <year-range>`.
4. Look at later review papers found in Step 1; their reference lists often include forward citers of the nodes.

If forward yields very little, note it explicitly. Do **not** fabricate citers.

### 3c. Filter for topical relevance

Keep a neighbor only if its title OR abstract mentions either:

- the topic keywords from `topic`, **or**
- any of the node's key-points template fields (method, key params, quantities, or topic-specific points — extracted in Step 2).

Drop the rest. **Log every drop** in `corpus.md` with `role=dropped, Notes="off-topic: <one-phrase reason>"`. The dropped rows are what makes the sweep auditable.

---

## Step 4 — Enrich kept neighbors

Cap at **~15 in-topic neighbors per node, hop 1** (combined backward + forward).

For each kept neighbor:

- WebFetch the journal abstract page (DOI preferred). Use arXiv abstract only if no journal version exists.
- Read the neighbor through the **Key-points template** (defined in Step 2). Walk the fields one by one — explicitly check each field against the abstract, mark `?` if missing rather than skip. If a new key point recurs in ≥2 hop-1 neighbors and isn't in the template, add it (and back-fill earlier rows where the abstract supports it). Add one extra line: **Relation to the node** — extends method? challenges a result? applies the method to a new domain? — in one phrase. Write the result as a per-paper extraction block below the corpus table (see Step 0 for the block format).
- **Resolve preprint↔journal duplicates.** If the same paper surfaces as both an arXiv preprint and a journal article, keep one row, cite the journal version, note the arXiv ID parenthetically.

Tag rows `role=neighbor, hop=1`.

---

## Step 5 — Recurse one hop, with permission

Print a 5-bullet hop-1 summary covering:

1. Which methods recur across the corpus.
2. Which results form a consensus.
3. Which results are contested.
4. Which gaps stand out.
5. Top 2–3 hop-1 neighbors by inbound citation count (or by how often they were cited *within the hop-1 corpus itself* if external counts are unavailable).

Then ask:

> *"Expand to hop 2 from these top hop-1 neighbors? (y/n)"*

- **`y`:** repeat Steps 3–4 from the 2–3 named hop-1 neighbors, with budget halved (~7 per anchor). Tag new rows `hop=2`.
- **`n`:** skip to Step 6.

---

## Step 6 — Synthesise `report.md`

Use the template at `references/report-template.md`. The report opens with the **Key points of this topic** section (which mirrors the template developed in Steps 2–4), then synthesises across them. Sections (in order):

0. **Key points of this topic** — list the final key-points template (as it stood after Step 4 / Step 5). For each field, give one sentence on what the corpus collectively says about it (e.g., what methods are used, what parameter ranges are typical, what quantities are reported). Each sentence ends with one or two inline citations from the corpus. This is what discriminates the topic.
1. **State of the art** — 2–3 paragraphs synthesising what the corpus collectively says.
2. **Consensus** — bullet list of agreed-upon points, each cited.
3. **Open disagreements** — bullet list, each side cited.
4. **Gaps** — what the corpus does *not* cover.
5. **Recommended next reads** — short list of papers worth reading after this sweep.
6. **Crucial sources** — 3–7 papers the user should read deeply, each with link and a one-sentence justification.

**Citation format.** Every factual claim ends with an inline link.

- **Node papers** (deeply read) are labelled with the ` — node` suffix:
  ```
  ([Author Year — node](https://doi.org/...))
  ```
- **Neighbor papers** (abstract-level) are cited *without* a role label — just author + year:
  ```
  ([Author Year](https://doi.org/...))
  ```

The `— node` tag is what tells the reader "this claim rests on a paper I actually read"; neighbors carry no such tag, so the absence of a tag means abstract-level support. Do not write `— neighbor` in the report. For multi-source claims, link all. **Never** use a bare arXiv ID or unlinked author-year. Use arXiv links only when no DOI exists.

If hop 1's forward search was thin, add a short paragraph at the end of *State of the art* labelled "*Coverage caveat:*" naming the gap.

---

## Step 7 — Finalise `corpus.md`

Sort the table by `role` (node → neighbor → dropped) then by `hop`. Verify every paper that was searched, fetched, or filtered appears as a row — the kept rows justify the report; the dropped rows justify the boundary of the topic.

---

## Step 8 — Report back

Print a final line:

> *"Saved to `<output_folder>/report.md` and `<output_folder>/corpus.md`. Hop-1 corpus: N kept, M dropped. Hop-2: K kept (or 'skipped')."*

---

## Failure handling

| Situation | Action |
|---|---|
| `output_folder` missing or doesn't exist | Stop and ask. Do not create silently. |
| No node paper clearly stands out (Step 1) | Present top 5 with scores, ask the user to pick. |
| User declines to share PDF for backward references | Use journal abstract page only; flag in `corpus.md` `Notes` that the bibliography is incomplete. |
| Forward citation search yields almost nothing | Document the gap in `report.md` under "*Coverage caveat*". Do not fabricate citers. |
| WebSearch / WebFetch fails repeatedly | Stop and surface the error to the user. **Do not** silently fall back to general knowledge or model priors. |
| Same paper appears as preprint and journal article | Keep one row, cite the journal version, note the arXiv ID parenthetically. |
| Topic is too broad and Step 1 returns disjoint clusters | Stop, list the clusters, ask the user to narrow. |
