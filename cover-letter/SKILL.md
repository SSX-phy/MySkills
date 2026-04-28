---
name: cover-letter
description: >
  Generate a journal submission cover letter from a manuscript file (PDF, DOCX, MD, or TXT).
  Works for any journal. Well-researched references for Nature, Science, PRL, PRB, and Elsevier
  are bundled; all other journals use the standard 4-paragraph formalism.
  Usage: /cover-letter <path/to/manuscript> [journal-name]
  Example: /cover-letter paper.pdf nature
  Example: /cover-letter paper.pdf "Journal of Chemical Physics"
  Extracts title, article type, background, research question, findings, and significance
  from the manuscript, confirms with you, then drafts a cover letter saved as .docx.
  For PRL, also generates the mandatory 100-word portal justification as a separate block.
when_to_use: >
  When the user says: "write a cover letter for my paper", "draft a cover letter for [journal]",
  "I need to submit to [journal] and need a cover letter", "help me write a cover letter",
  or provides a manuscript path and asks for a cover letter.
allowed-tools: Bash(python *), Bash(pip *)
---

# Cover Letter Skill

Generate a journal submission cover letter from a manuscript file. Follows a 4-paragraph formalism derived from Nature and Elsevier guidelines, with journal-specific additions for Nature, Science, PRL, PRB, and Elsevier. Works for any journal.

---

## Step 1 — Parse arguments

`$ARGUMENTS` contains `<manuscript-path> [journal-name]`.

- Extract the manuscript path (first token) and journal name (everything after the first space, if present).
- If journal name is missing,just use [journal-name]

---

## Step 2 — Check dependencies

First, resolve the skill directory:
```bash
SKILL_DIR="$HOME/.claude/skills/cover-letter"
```

Then check dependencies:
```bash
python -c "import pdfplumber, docx, docx2txt"
```

If this fails, run:
```bash
pip install pdfplumber python-docx docx2txt
```

Report success or failure. If pip fails, tell the user to install manually and stop.

---

## Step 3 — Extract manuscript text

Run:
```bash
python "$SKILL_DIR/scripts/parse_manuscript.py" "<manuscript-path>"
```

The script outputs JSON `{"text": "..."}` or `{"error": "...", "text": ""}`.

- PDF: first 15 pages extracted
- DOCX: full text
- MD / TXT: full file

If `text` is empty or very short (under 200 characters), the PDF likely has no text layer. Ask the user to paste the title, abstract, and key findings manually, then skip to Step 6 using the pasted content.

---

## Step 4 — Extract the 4-paragraph source material

Read the extracted text and identify the following fields. Display each one clearly before asking for confirmation:

| # | Field | Where to find it |
|---|---|---|
| 1 | **Title** | First prominent line / title block |
| 2 | **Article type** | Manuscript header, or submission instructions (research article, review, case study, letter, etc.) |
| 3 | **Background** | Introduction — 1–2 sentences on context and what was previously known |
| 4 | **Research question** | Introduction — the specific question the paper set out to answer |
| 5 | **Why the question matters** | Introduction — why answering it is important |
| 6 | **What was done** | Abstract or Methods — methods in one brief phrase |
| 7 | **Main findings** | Abstract or Results — 2–3 key results |
| 8 | **Significance** | Abstract or Discussion — why the findings matter, what they change or enable |
| 9 | **Corresponding author + email** | Author block or correspondence section |

If **article type** cannot be determined from the text, ask the user before continuing.


---

## Step 5 — Show and confirm

Display all fields from Step 4 plus the journal-fit answer from Step 5. Ask:

> *"Does this look correct? Correct anything before I draft the letter."*

Wait for confirmation or corrections. Apply any corrections to the fields before proceeding.

---

## Step 6 — Load journal reference file

Normalise the journal name to lowercase, strip spaces and punctuation (e.g. "Physical Review Letters" → "prl", "Nature Communications" → "nature").

Read the corresponding file from `$SKILL_DIR/references/<key>.md`,pick the Mapping part and find the best match from . If no match, load `general.md`.

Print a one-line header:
> *"Applying [Journal] requirements — [2–3 key rules from the reference file]."*

---

## Step 7 — Draft the cover letter

Write exactly four paragraphs using the confirmed fields. Follow the formalism precisely.

---

### Paragraph 1 — Title, Article Type, Background, and Question

> We submit [article type] entitled "[Title]". [Background — 1–2 sentences on context and what was previously known]. [Research question — what this study set out to answer and why answering it matters].

Rules:
- State the article type explicitly.
- Background should be readable by an editor outside the immediate subfield.
- The question sentence must convey *why* it needed answering.

---

### Paragraph 2 — What Was Done, Main Findings, Significance

> [What was done — methods in one brief phrase]. [Main finding 1]. [Main finding 2 if present]. [Significance — why these findings are important and what they change or enable].

Rules:
- Methods get one phrase only.
- State findings specifically; avoid "novel" and "important" without content.
- The significance sentence should name what is now possible or understood that was not before.

---

### Paragraph 3 — Relevance to the Journal

> We believe the readers of [Journal] would be interested in this work because [specific argument from Step 5 — how it fulfils the journal's aims and scope, and why it matters to that readership].

Rules:
- Must be specific to the named journal.
- If the user typed "skip", write: *[PLACEHOLDER — please personalise: explain how this work fulfils [Journal]'s aims and scope]* and note this to the user.

---

### Paragraph 4 — Corresponding Author and Journal-Specific Requirements

> Correspondence should be addressed to [name] at [email]. [Journal-specific requirements from the loaded reference file — e.g., ethical standards declaration, originality statement, COI, AI disclosure, author-approval statement.]

Rules:
- Use verbatim mandatory phrasing from the reference file where specified.
- **Omit this paragraph entirely** if the loaded reference file specifies no requirements AND the user has not provided any. For unknown journals using `general.md`, include only the generic originality statement:
  > *"This manuscript has not been published elsewhere and is not currently under consideration by another journal."*


---

## Step 8 — Show draft and confirm

Print the full letter. For PRL, print the justification block below a `===` divider. Ask:

> *"Any changes before I save?"*

Apply any edits the user requests.

---

## Step 9 — Save to .docx

Determine the output path:
- Same directory as the input manuscript
- Filename: `<manuscript-stem>-cover-letter-<journal>.docx`

Write the letter text to a temporary file and pipe it:
```bash
python "$SKILL_DIR/scripts/generate_docx.py" "<output-path>" < temp_letter.txt
```

If the DOCX write fails, save as `<manuscript-stem>-cover-letter-<journal>.md` instead and tell the user.

---

## Step 10 — Report

Print:
> *"Saved to: [full path]"*

---

## Failure handling

| Situation | Action |
|---|---|
| PDF with no text layer | Skip Steps 3–4; ask user to paste title, abstract, and key findings |
| Article type not found in manuscript | Ask user to specify before drafting |
| Corresponding author email not found | Leave as `[email]` placeholder and flag it |
| Journal reference file not matched | Use `general.md` silently |
| No abstract found | Ask: *"I couldn't find an abstract. Please paste your key findings (2–3 sentences)."* |
| pip install fails | Tell user: `pip install pdfplumber python-docx docx2txt` and stop |
| DOCX write fails | Save as `.md` and tell user |