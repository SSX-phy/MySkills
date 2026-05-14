# MySkills

This is a personal repository of agent skills. Also an attempt to skillize the whole working flow of a research career.

This repo is open to be refered by anyone want to create similar skills or any agent be assigned such a task.

## Skills

- **[academic-sweep](academic-sweep/)** — citation-network sweep of an academic topic. Walks references and forward citations one hop with topical filtering, and produces `report.md` (synthesis) + `corpus.md` (audit table). Invoked by the `academic-explorer` subagent.
- **[academic-paper-extract](academic-paper-extract/)** — deep read of a single paper (PDF path, arXiv ID, or DOI). Stages abstract → sections → full read with permission. Note structure is fully adaptive: Source + Key points are universal, the body sections mirror the paper's own roadmap. Invoked by the `academic-explorer` subagent.
- **[cover-letter](cover-letter/)** — drafts a journal submission cover letter from a manuscript file. Bundled requirement files for Nature, Science, PRL, PRB, Elsevier; falls back to a generic 4-paragraph formalism for other journals.
