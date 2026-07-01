---
name: reverse-engineering
description: >
  Generate a progressive-disclosure "global picture" report of an unfamiliar
  codebase, with UML class diagrams and interaction (sequence) diagrams rendered
  as mermaid. Use this whenever the user wants to understand, map, or onboard to
  a project they didn't write — phrasings like "reverse engineer this code",
  "give me an architecture / overview of this project", "what does this codebase
  do", "draw a class / sequence diagram of X", "map out how these modules
  interact", or "help me understand this repo". The report classifies classes,
  functions, and variables by how heavily they're used so the high-level diagrams
  stay readable, then discloses the full diagrams and reference tables underneath.
  For procedure-oriented code with no meaningful classes, it produces only the
  interaction diagram.
---

# Reverse Engineering

## What this produces

**Always two markdown files**, built around **progressive disclosure**: the reader
understands the system from the first file, then opens the second only when they
need ground truth.

- **`<project>-overview.md` — the global picture.** A short executive summary plus
  mermaid diagrams showing *only the important elements*. This file must fit in the
  reader's head — it's what they read first. How many *levels* of zoom it holds
  depends on the project's complexity (next section): a simple project gets one
  overview; a complex one gets a top **system map** of subsystems followed by a
  compact overview of each subsystem — both still inside this one file.
- **`<project>-detail.md` — the full detail.** The complete diagrams with every
  member, plus reference tables listing every function and every significant
  variable, each tagged with its importance and where it's used.

Two files is a hard rule — never emit a tree of files. The overview stays short
enough to read in one sitting; the detail file is the reference you open only when
the overview isn't enough. Cross-link them so the reader can move between them.

## Disclosure depth: simple vs complex projects

Before drawing, **gauge the project's complexity** — it decides whether the
overview holds one level of zoom or two.

- **Simple** — one cohesive codebase: a CLI tool, a single service, a library with
  a handful of modules (DmftManager is here). A single overview of the important
  elements stays within the ~7±2 legibility limit. → **2 levels**: `overview.md`
  (one overview) + `detail.md` (everything).
- **Complex** — several subsystems / packages / bounded contexts, where a single
  overview would blow past ~7±2 nodes and stop fitting in the reader's head. →
  **3 levels**:
  1. a top **system map** — a flowchart whose nodes are *subsystems* and whose
     arrows are how they depend on or call each other, plus one high-level
     sequence diagram of the main cross-subsystem flow;
  2. a compact **overview per subsystem** — the same important-elements treatment,
     scoped to one subsystem at a time;
  3. the **full detail**.

  Levels 1 and 2 both live in `overview.md` (the map first, then the subsystem
  overviews); level 3 is `detail.md`. **Still two files.**

Cap the depth at three. If a single subsystem is still too big for one overview,
don't add a fourth level or more files — **compress** instead (collapse helper
clusters, summarize a sub-flow into one step; see the compression note in step 7).

## The core idea: importance by usage

A diagram that shows everything shows nothing — it becomes a hairball. So before
drawing anything, decide what matters. An element is **important** if any of
these hold:

- It's an **entry point**: a CLI command, `main`, an exported/public API symbol,
  a request/route/event handler — the places execution actually starts.
- It has **high fan-in**: it's referenced or called from many distinct sites.
  Rank symbols by how many places use them; the heavily-used cluster is
  important, the long tail of used-once helpers is not.
- It sits on the **main execution path** traced from an entry point.
- It's a **core domain type**: a class that many others depend on, compose, or
  inherit from.

Everything else — private leaf helpers called from one place, trivial
one-off utilities, local-only constants — is **unimportant**. It is *not* deleted;
it's deferred to the detail file.

State the cut you chose and why ("kept the 6 symbols referenced 3+ times; the
remaining 14 are used once and appear in the detail file"). Being explicit keeps
the report honest and reproducible, and lets the reader trust that the omissions
in the overview were deliberate.

**For variables**, judge only state that shapes the design: module-level/global
variables, significant configuration, and key instance attributes. Important
state is read or written from many places — in procedure-oriented code,
shared global state is often the real backbone of the system. Do **not** inventory
local variables; that's noise, not architecture.

## Workflow

Work through these steps. Use a todo list if the project is non-trivial.

### 1. Survey and scope

Read the project layout: entry points, top-level modules/files, build or config
files that reveal structure. Identify the language(s). If the user pointed at
specific files, that's your scope; otherwise scope to the project root. Form a
one-sentence hypothesis of what the project does — you'll refine it. Note whether
it looks like one cohesive codebase or several subsystems; that sets the
disclosure depth in step 6.

### 2. Detect the paradigm

This decides which diagrams you produce.

- **OOP** — behavior lives in classes with meaningful relationships → class
  diagram **and** interaction diagram.
- **POP** (procedure-oriented) — behavior lives in module-level functions and
  shared state, with no meaningful classes → **interaction diagram only**. Skip
  the class diagram entirely; don't fake one out of modules.
- **Mixed** — some real classes plus free functions → class diagram for the OO
  portion, and an interaction diagram whose participants include the relevant
  modules/functions.

A handful of trivial data-holder classes (named tuples, plain structs) does not
make a project OOP. Ask whether the *design* is carried by classes or by
procedures.

### 3. Inventory the symbols

List the classes, functions/methods, and significant variables in scope. For
each note where it's defined. This is the raw material for both the diagrams and
the Part 2 tables, so don't skip items — completeness lives in Part 2.

### 4. Measure usage and trace the main path

For each symbol, count how many distinct places reference it (fan-in). Grep for
the identifier across the project to find call/reference sites — this is the
language-agnostic way to measure usage and works even without an AST. Identify
the entry point(s) and trace the dominant execution path outward from them: what
calls what, in what order. That trace becomes your interaction diagram.

### 5. Classify

Tag every symbol **important** or **unimportant** using the rules above. Apply
semantic sense when counts mislead — an entry point referenced "once" (from the
shell) is still important; a logging helper called 50 times is still plumbing.
The goal is a Part 1 that reads cleanly, so optimize for the reader's
understanding, not for a mechanical threshold.

### 6. Set disclosure depth and granularity (adaptive to complexity)

First **fix the depth** using the complexity gauge above. Decide by the ~7±2 test:
if a single overview of the *whole* system would need more than ~7±2 nodes, it's
complex — lift its subsystems into a system map and give each its own overview a
level down (3 levels); otherwise keep it simple (2 levels). State the depth you
chose. Either way the output is two files (step 9).

Then **pick the granularity** for each overview, and state it:

- **Tiny project** (a handful of files, ≲15 functions): function-level — let the
  diagram participants and class members be individual functions; you can afford
  to show most of them.
- **Medium/large**: class/module-level — participants are classes or modules, and
  the overview shows only their important members. Collapse helper clusters.
- **System map (complex only)**: subsystem-level — nodes are whole subsystems;
  their internals are deferred to the per-subsystem overviews.

A single overview diagram with more than ~7±2 participants or a couple dozen
members is a signal your cut is too loose, or that the project wants the 3-level
treatment — tighten the cut or split into subsystems.

### 7. Build the overview file (important elements only)

**Simple project** → build one overview: a class diagram and an interaction
diagram of the important elements (below). **Complex project** → build the **system
map** first (step 6) — a flowchart whose nodes are subsystems with dependency
arrows, plus one high-level, compressed sequence diagram of the main
cross-subsystem flow — then a compact class+interaction overview for *each*
subsystem, scoped to that subsystem's important elements. Everything in this step
goes into `overview.md`, map first.

The rules below apply to every overview at every level (the system map's "nodes"
are subsystems; a subsystem overview's participants are its classes/objects).

- **Class diagram**: the important classes, their important members, and the
  relationships between them (inheritance, composition, association). Omit for
  pure POP.
- **Interaction diagram**: the main scenario traced in step 4, showing only the
  important calls. Omit unimportant helper calls here — they live in the detail file.

**Lifelines are objects and processes — not modules, methods, or the outside
world.** A sequence diagram's columns should be the stateful parts of *this*
system that persist across the interaction: class instances (objects) and the
distinct processes/actors that make up the system (e.g. the client process and
the daemon). Three things look like participants but should **not** get a column:

- **A method or function is a message, not a lifeline.** Don't give
  `handle_command`, `update_job_state`, or `submit` their own column; they ride on
  arrows. A call from an object into its own helper is a self-message
  (`Manager->>Manager: handle_command -> _dispatch`).
- **A procedural helper module is not an object.** A bag of free functions in the
  same process as its caller (e.g. a `scheduler_layer` of `submit`/`cancel`
  functions) has no independent lifetime, so it earns no lane. Show the call as a
  self-message on the object that uses it, naming the function:
  `Task->>Task: submit() via scheduler_layer`. (In the *class* diagram that same
  module can still appear as a `<<module functions>>` box — that's a grouping, not
  a lifeline.)
- **The outside world gets exactly one column.** The OS, the filesystem, a
  scheduler like SLURM/PBS, a database, any third-party service — collapse them all
  into a single `environment` participant on the far side of the diagram, and send
  every boundary-crossing call to it with the specific command named on the arrow
  (`Task->>env: sbatch / qsub`, `Task->>env: read params.dat`). Don't give each
  external system its own lane, and don't model them as transient create/destroy
  nodes — both just litter the picture. One env column keeps every boundary
  visible at the cost of exactly one lane. (Split the environment into named lanes
  only when the protocol *between* those specific external systems is the whole
  point of the diagram.)

Then **weigh each remaining lifeline by how much it interacts.** Apply the same
usage cut you used for elements: a participant carrying only one or two arrows — a
`User` who just sends the first command and reads the last reply — costs a column
without earning one, so fold it into a `Note` or begin the flow at the first real
component. But when the human user genuinely drives the interaction (many turns,
real branch-points), give the user its **own actor column** — and keep it distinct
from the single `environment` column, since the user is an actor, not part of the
external system. This is importance-by-usage applied to lifelines, and it governs
both files.

**Compress a long interaction diagram.** When a flow has too many arrows to scan
(common in the system map and in any complex subsystem), don't draw every step —
compress it:

- **Collapse a sub-flow into one labelled step.** Replace a detailed multi-message
  exchange with a single arrow that names it (`Manager->>Task: run tick (poll +
  act)`), and let the *detail* file expand it. This is progressive disclosure
  inside one diagram.
- **Group a phase with `rect`** (a tinted box) plus a `Note` to label it, so the
  reader sees "sense phase" / "act phase" without tracing each arrow.
- **Factor structure with blocks** — `loop`, `alt`, `opt`, `par` — instead of
  redrawing similar arrows.

The overview shows the compressed form; the detail file carries the expansion.

See `references/mermaid.md` for exact mermaid syntax (class, sequence, and the
flowchart used for the system map) and the errors that commonly break rendering.
Sanity-check that each diagram is valid mermaid before moving on.

### 8. Build the detail file (full detail)

- **Full class diagram**: every class, every member, all relationships. Omit for
  pure POP.
- **Full interaction diagram(s)**: the complete flow including the calls you
  omitted from the overview. Add a second scenario diagram if one main flow
  doesn't capture the system (e.g. a separate setup vs. run path).
- **Function reference table** and **variable/state reference table** (templates
  below) covering everything in the inventory.

For a complex project, organize this file **by subsystem** — a full diagram set
and reference tables under a heading per subsystem — so the detail mirrors the
overview's subsystem split. The reference tables stay whole-project-complete
regardless.

### 9. Assemble and write the two files

Fill the templates below and write the executive summary last (once you actually
understand the system). Save two files in the project root unless the user
specifies otherwise: `<project>-overview.md` (the global picture) and
`<project>-detail.md` (the full detail). Even for a 3-level project this is still
exactly two files — the system map and the per-subsystem overviews stack inside
`overview.md` (map first), and all the detail goes in `detail.md`. Link from the
overview to the detail file, and from the detail file back to the overview, so the
reader can move between them.

## Report templates

Two files. Sections marked *(OOP/mixed only)* are dropped for pure POP.

### Overview file — `<project>-overview.md`

````markdown
# <Project Name> — Overview

## Executive summary

<2–4 sentences: what the project does, its paradigm (OOP / POP / mixed), the
entry point(s), and the single most important thing to know before reading code.>

> Depth: <2-level (simple) | 3-level (complex)>. Granularity: <function-level |
> class/module-level | subsystem-level>. Importance cut: <state the rule you
> applied and roughly how many elements it kept vs. deferred>.

<!-- ========== Complex projects only: level 1, the system map ========== -->
## System map  <!-- (complex only) -->

```mermaid
flowchart TD
    %% nodes = subsystems, arrows = dependency / calls; ~7±2 nodes
```

```mermaid
sequenceDiagram
    %% main cross-subsystem flow, compressed (one step per subsystem hop)
```

<1–2 sentences on how the subsystems fit together.>

<!-- ========== The overview proper ==========
     Simple project: skip the system map above and emit ONE pair of diagrams for
     the whole project (drop the "<Subsystem> —" prefix).
     Complex project: repeat the pair below once per subsystem (level 2). -->

## <Subsystem / Project> — class diagram  <!-- (OOP/mixed only) -->

```mermaid
classDiagram
    %% important classes + important members + relationships
```

## <Subsystem / Project> — interaction diagram

```mermaid
sequenceDiagram
    %% main scenario, important calls only, compressed where long
```

<1–3 sentences walking the reader through the flow above.>

---
Full diagrams, every member, and complete reference tables:
see [`<project>-detail.md`](<project>-detail.md).
````

### Detail file — `<project>-detail.md`

````markdown
# <Project Name> — Full detail

Back to the [overview](<project>-overview.md).

## Full class diagram  <!-- (OOP/mixed only) -->

```mermaid
classDiagram
    %% every class, every member, all relationships
```

## Full interaction diagram

```mermaid
sequenceDiagram
    %% complete flow, including calls omitted from the overview
```

## Function reference

| Function / Method | Defined in | Importance | Used by (fan-in) | Role |
|---|---|---|---|---|
| `name` | file:line | ● important / ○ minor | callers / count | one line |

## Variable / state reference

| Name | Scope | Importance | Read / written by | Role |
|---|---|---|---|---|
| `name` | global / class attr / config | ● / ○ | sites | one line |

## Honest omissions

<anything you couldn't resolve — dynamic dispatch, generated code, external
boundaries — stated plainly rather than guessed at.>
````

Use ● for important and ○ for minor so the tables are scannable. Sort each table
important-first so the reader meets the load-bearing pieces before the long tail.

## Quality bar

- **Always exactly two files** — `overview.md` + `detail.md`, never a tree. For a
  complex project the system map and per-subsystem overviews stack inside
  `overview.md`.
- **Every level stays legible.** Each diagram — the system map, each subsystem
  overview — obeys the ~7±2 cut on its own; the map shows subsystems, not classes.
  If a view overflows, tighten the cut or compress (collapse sub-flows, `rect`
  phases); don't add a fourth level.
- **Every diagram renders.** Invalid mermaid is worse than no diagram. Check
  syntax against `references/mermaid.md`.
- **The detail file is complete.** Every function and significant variable appears
  in a table, even the minor ones — that's the payoff of progressive disclosure.
- **Describe what exists, not what to build.** This is a map of the code as it
  is, not a plan of work. Avoid "TODO", "should", or implementation steps.
- **Honest omissions.** If you couldn't resolve something (dynamic dispatch,
  generated code, an external boundary), say so rather than inventing edges.
