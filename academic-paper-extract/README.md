# academic-paper-extract

Claude Code skill that does a deep read of a single paper (PDF, arXiv ID, or DOI) and writes a structured note into the user's notes folder.

## Usage

Invoked by the `academic-explorer` subagent for Pattern B (single-paper deep dive):

```
source="<pdf-path|arxiv-id|DOI>" output_folder="<path>"
```

Examples:

```
source="paper.pdf"               output_folder="~/research/notes/condmat/"
source="2401.12345"              output_folder="~/research/notes/condmat/"
source="10.1103/PhysRevLett.130.123456" output_folder="~/research/notes/condmat/"
```

## Note structure (fully adaptive)

Only two blocks are universal:

- **Source** — clickable URL + full citation.
- **Key points** — same vocabulary as `academic-sweep` (method + key params, quantities used to show the result, plus 2–4 paper-specific key points discovered from the abstract).

The **body section list** is discovered from the paper itself — the abstract and the roadmap paragraph at the end of the introduction. A theory paper might end up with `Setup / Theorem / Proof sketch / Implications`; an experimental paper with `Apparatus / Procedure / Data / Discussion`. The skill does not impose one.

A short **Roadmap** block precedes the body sections (one bullet per section, one sentence each) so the reader can skim before diving in.

## Staged read

1. Build the Source block from the abstract page.
2. Read abstract + end-of-intro to discover key points and the paper's structure.
3. Lock the structure with the user.
4. **Ask before fetching the PDF.** Read only the sections needed to fill the locked body sections.
5. Write, confirm, save as `<author><year>-<slug>.md`.

## Layout

```
academic-paper-extract/
├── SKILL.md                  # full skill instructions
├── references/
│   └── note-template.md      # universal blocks + body placeholder
└── README.md
```

## Dependencies

For local-PDF input only — reuses `cover-letter/scripts/parse_manuscript.py`:

```
pip install pdfplumber python-docx docx2txt
```

arXiv-ID and DOI inputs use WebFetch only (no Python needed).
