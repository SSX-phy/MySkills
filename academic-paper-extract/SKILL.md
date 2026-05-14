---
name: academic-paper-extract
description: >
  Single-paper deep read producing a structured note in the user's notes folder.
  Accepts a local PDF path, an arXiv ID, or a DOI. Staged: read the abstract first,
  ask before fetching the PDF, then read only the sections needed to fill gaps.
  Note structure is fully adaptive — only the Source and Key points blocks are
  universal; the body section list is discovered from the paper's own structure
  (abstract + end of introduction). Uses the same key-points vocabulary as the
  academic-sweep skill so the note interoperates with corpus-level synthesis.
  WebSearch + WebFetch + Read only — no API keys.
  Usage (invoked by the academic-explorer subagent):
    source="<pdf-path|arxiv-id|DOI>" output_folder="<path>"
when_to_use: >
  Invoked by the academic-explorer subagent for Pattern B single-paper deep dive.
  Trigger: user supplies one paper (PDF path, arXiv ID, or DOI) and asks for a
  deep read or note extraction.
allowed-tools: WebSearch, WebFetch, Read, Write, Edit, Bash, Glob, Grep, TodoWrite
---

# Academic Paper Extract Skill

Deep read of one paper. Inputs come as a string in `$ARGUMENTS` of the form:

```
source="<pdf-path|arxiv-id|DOI>" output_folder="<path>"
```

## Operating principles (inherit from `academic-explorer` subagent)

1. Cite with a clickable link, **journal/DOI preferred** over arXiv. If both exist, cite the journal version and note the arXiv ID parenthetically only if useful for open access.
2. No fabrication — never invent authors, titles, journals, years, numbers, or URLs.
3. Distinguish **read** (you actually fetched it) from **inferred** (abstract or snippet only).
4. Confirm `output_folder` before writing. Never assume.
5. Do **not** auto-download PDFs. Ask the user before fetching any PDF.

## Adaptive note structure (universal vs. discovered)

Every note ships with exactly two universal blocks at the top:

1. **Source** — clickable URL + full citation (required by the `academic-explorer` subagent).
2. **Key points** — the adaptive key-points template inherited from `academic-sweep`: two seed hints (method + key params, quantities used to show the result) plus 2–4 paper-specific key points discovered from the abstract. This is the interop layer with corpus-level synthesis.

**Everything below those two blocks is per-paper.** Do not impose a fixed list of body sections (no automatic "Summary / Methods / Results / Limitations / Open Questions"). Instead, discover the body section list from the paper itself in Step 2 and lock it with the user in Step 3.

How to discover the structure:

- The **abstract** usually states the paper's main contributions in order ("we present X, derive Y, and validate Z").
- The **end of the introduction** is more reliable still — most physics/math/engineering papers include a roadmap paragraph like "In Section 2 we set up the model. Section 3 derives the central identity. Section 4 reports numerical experiments. Section 5 discusses limits and outlook."
- Use that roadmap (or the abstract's contribution list, if no roadmap is present) as the proposed body-section list for the note. One note section per significant contribution / paper section, with the same names the paper uses where they're informative.
- For a theory paper this might be `Setup / Theorem / Proof sketch / Implications`. For an experimental paper, `Apparatus / Procedure / Data / Discussion`. For an algorithm paper, `Problem / Algorithm / Analysis / Experiments`. For a review, `Background / Categorisation / Open problems`. The skill does **not** know which it is — it lets the paper say.

---

## Step 0 — Parse arguments and resolve source

Parse `$ARGUMENTS` into `source` and `output_folder`. Detect the source type:

- **Local PDF path** — file exists on disk. Use `Read` directly later.
- **arXiv ID** — matches `\d{4}\.\d{4,5}` (or legacy `<archive>/\d{7}`). Abstract: `https://arxiv.org/abs/<id>`. PDF: `https://arxiv.org/pdf/<id>.pdf`.
- **DOI** — matches `10\.\d{4,}/...`. Resolve via `https://doi.org/<id>`.

If the input matches none of the three patterns, **stop and ask** the user to clarify.

If `output_folder` is missing or doesn't exist, **stop and ask** the user to confirm a path. Do not silently create one.

Use `TodoWrite` to track Steps 1–7.

---

## Step 1 — Build the Source block

Fetch the abstract page:

- **DOI:** WebFetch `https://doi.org/<id>` (will redirect to the journal page).
- **arXiv ID:** WebFetch `https://arxiv.org/abs/<id>`.
- **Local PDF:** run the existing parser:
  ```bash
  python "$HOME/.claude/skills/cover-letter/scripts/parse_manuscript.py" "<pdf-path>"
  ```
  Use the first 15 pages of returned text.

Extract: title, authors (full list), venue (journal name + volume/pages, or "arXiv preprint"), year, link, full citation. Write the Source block exactly in the shape shown in `references/note-template.md`.

---

## Step 2 — Discover key points and the paper's own structure

Read the **abstract** and the **end of the introduction**. From these:

1. **Fill the two seed hints** of the Key Points block:
   - **Method (& key params)** — one phrase. If algorithmic, include the parameters that distinguish this run from a generic application (e.g., "DMRG with bond dimension 2000 on 2D Hubbard at U/t=8").
   - **Quantities used to show the result** — the central observables/metrics reported (e.g., "ground-state energy per site, spin gap").
2. **Identify 2–4 paper-specific key points** the abstract foregrounds — defining regime/limit, benchmark dataset, characteristic parameter the community tracks, etc.
3. **Discover the paper's own organizing structure.** Look for a roadmap paragraph at the end of the introduction ("In Section 2 we…, in Section 3 we…"); fall back to the abstract's contribution list if no roadmap is present. Build a proposed body-section list for the note from that — one entry per significant contribution / paper section, using the paper's own names where informative.

If the abstract + end-of-intro are too thin to identify either the key points or the structure, mark the missing items `?` for now — Step 4 will fill them from the PDF body if the user grants access.

---

## Step 3 — Show, lock, edit

Print three things to the user:

- The Source block (Step 1).
- The Key points block (Step 2.1–2.2).
- The **proposed body-section list** (Step 2.3) as a numbered outline, with one short sentence per section explaining what it'll cover (drawn from the paper's roadmap / abstract).

Ask:

> *"Lock these as the structure for the rest of the read, or want to edit? You can rename, drop, merge, or add sections."*

Apply edits. The locked section list becomes the body of the note — Step 5 will write exactly these sections in this order, no others.

---

## Step 4 — Staged section reading (with permission)

Decide which PDF sections you need to fill the locked body sections. Map each note section to the paper section(s) you need to read for it. Show the mapping to the user:

> *"To fill the locked sections I need to read [list of paper sections]. OK to fetch the PDF? (or paste the relevant sections directly)"*

If approved:

- **Local PDF:** `Read` it directly (Claude Code reads PDFs natively).
- **arXiv ID:** WebFetch `https://arxiv.org/pdf/<id>.pdf`, or `Read` if the user has already downloaded it.
- **DOI without local PDF:** ask the user to download it; do not attempt to bypass paywalls.

If declined: skip to Step 5, fill missing fields with `?`, note in the bottom of the note: *"Read abstract-only; body details inferred from the abstract."*

---

## Step 5 — Write the note

Use the template at `references/note-template.md`. Fill the Source block from Step 1, the Key points block from Step 2 (and Step 4 if the PDF was read), then write a short **Roadmap** block, then write each body section locked in Step 3 in order.

**Roadmap block (required, before any body section):** one bullet per locked body section, in order, formatted as `**<Section name>** — one sentence on what the section covers.` Mirrors the roadmap paragraph at the end of a paper's introduction, but for this note. Lets the reader skim the section list and know what each will deliver before diving in.

Per body section: 3–8 bullets or 1–3 short paragraphs, in your own words. Each non-trivial claim ends with a section/figure/equation pointer — `(§3.2, Fig 4)`, `(Eq 7)`, `(Tab 2)`. Quote the paper sparingly and only when wording matters.

When citing other papers inside the note, use the same format as `academic-sweep`: clickable DOI link, journal preferred. Never a bare arXiv ID or unlinked author-year.

---

## Step 6 — Show and confirm

Print the full draft note. Ask:

> *"Any changes before I save?"*

Apply edits.

---

## Step 7 — Save and report back

Filename: `<first-author-lastname><year>-<short-title-slug>.md`. Example: `Anderson1958-absence-of-diffusion.md`. Slug = first 4–6 informative words of the title, lowercased, hyphenated, punctuation stripped.

Save into `output_folder`. **If the file already exists, ask before overwriting** (offer `-v2` suffix as fallback).

Print:

> *"Saved to `<full-path>`. One-line corpus row: `| <title> | <authors> | <venue> | <year> | <link> | <cites> | node | 0 | deep-read |`"*

The corpus row is in `academic-sweep`'s `corpus.md` table format, so the user can paste it directly if they later run a sweep anchored on this paper.

---

## Failure handling

| Situation | Action |
|---|---|
| `output_folder` missing or doesn't exist | Stop and ask. Do not create silently. |
| Source matches no input pattern | Stop and ask the user to clarify. |
| arXiv ID malformed | Ask the user to confirm. |
| DOI returns 404 | Ask the user to verify; do not proceed. |
| arXiv abstract page unreachable | Try `https://export.arxiv.org/abs/<id>`; if that also fails, surface the error. |
| End-of-intro has no roadmap, abstract is generic | Propose a minimal 2–3 section list drawn from the abstract (e.g. `Contribution 1 / Contribution 2`) and ask the user to refine in Step 3. |
| PDF has no text layer | Skip Step 4 PDF read; ask the user to paste abstract + relevant sections. |
| User declines PDF read | Fill abstract-only, mark missing items `?`, continue to Step 5. Add the abstract-only note at the bottom of the note. |
| File already exists at the save path | Ask before overwriting. Offer `-v2` suffix. |
| WebFetch / WebSearch fails repeatedly | Stop and surface the error. **Do not** silently fall back to general knowledge or model priors. |
