# cover-letter

Claude Code skill that generates a journal submission cover letter from a manuscript file (PDF, DOCX, MD, or TXT).

## Usage

```
/cover-letter <path/to/manuscript> [journal-name]
```

Examples:

```
/cover-letter paper.pdf nature
/cover-letter paper.pdf "Journal of Chemical Physics"
```

The skill extracts title, article type, background, research question, findings, and significance from the manuscript, confirms the fields with you, then drafts a 4-paragraph letter and saves it as a `.docx` next to the manuscript.

For PRL, it also generates the mandatory 100-word portal justification as a separate block.

## Supported journals

Bundled reference files with journal-specific requirements:

- Nature
- Science
- Physical Review Letters (PRL)
- Physical Review B (PRB)
- Elsevier journals

Any other journal falls back to `general.md` (standard 4-paragraph formalism).

## Dependencies

```
pip install pdfplumber python-docx docx2txt
```

The skill checks for these on first run and prompts to install if missing.

## Layout

```
cover-letter/
├── SKILL.md                  # full skill instructions
├── references/               # per-journal requirement files
│   ├── general.md
│   ├── nature.md
│   ├── science.md
│   ├── prl.md
│   ├── prb.md
│   └── elsevier.md
└── scripts/
    ├── parse_manuscript.py   # extracts text from PDF/DOCX/MD/TXT
    └── generate_docx.py      # writes the final .docx
```