# reverse-engineering

Generates a progressive-disclosure "global picture" report of an unfamiliar
codebase: UML class diagrams + interaction (sequence) diagrams as mermaid.
Output is **always two files** — `<project>-overview.md` (important elements only,
read first) and `<project>-detail.md` (full diagrams + reference tables). Depth is
chosen by complexity: **simple → 2 levels**, **complex → 3 levels** (system map +
per-subsystem overviews). See [SKILL.md](SKILL.md) for the full method.

## Worked examples

Both applied the "omit standalone/support single files" scope and wrote the two
reports to the working directory.

- **eDMFT** (`D:\console\eDMFT\src`, Python orchestrator + Fortran/MPI executables)
  — classified **complex (3-level)**: system map + per-subsystem overviews, single
  `environment` lane for WIEN2k/Fortran/MPI/disk, procedural modules shown as
  `<<module functions>>` boxes.
- **SSE / `ssejk`** (`D:\console\SSE\plato\special`, OOP C++ Monte Carlo)
  — classified **simple (2-level)**: hub `SSE` → `Update`/`Obs`; `general/` and
  `randomc/` support libraries folded into the environment.
