---
name: edmft-aly-skill
description: Analyze a finished WIEN2k + embedded-DMFT (Haule eDMFT) run — analytic continuation of the self-energy and real-axis DOS / spectra. Use after a converged eDMFT self-consistent run to obtain real-frequency results (Sig.out, DOS, orbital-resolved spectra, hybridization). Not for setting up or launching a calculation (that is edmft-set-skill).
---

# eDMFT analysis (analytic continuation → real-axis DOS/spectra)

This skill covers **analysis only**: from a *converged* eDMFT self-consistent run to
real-frequency results. Setting up / initializing / submitting the run is the separate
`edmft-set-skill`; the `edmft` subagent holds the global picture and routes here **after**
a run has converged. Calculations run on the **remote server** — drive it through the
`tmux-usage` skill (never raw `ssh`).

**Command layer.** Each stage names the *original* eDMFT/Wien2k command (so you know
what actually runs). The user keeps a dispatcher `qdm` that wraps these; **if a `qdm`
exists at `~` on the remote server, prefer the `qdm --<flag>` shortcut** — otherwise run the
original commands. When present, `qdm` is on `PATH` (registered) — invoke it directly as
`qdm --<flag>`, no `~/` prefix or `bash` needed.

**Use the tools as black boxes.** Run the commands and respond to what they print; don't need to read
their source to predict behavior.

**Parameter notation.** Every tunable is written `$name_flag`. The `=` sign marks
whether it has a default:
- `$name_flag=value` → **defaulted**: apply `value` if the user did not specify it,
  but treat it as a real parameter (state it; never hardcode invisibly).
- `$name_flag` (no `=`) → **must-set**: no default. If it is not determined by the context,
  **STOP and ask the user.**

---

## 1. Global picture

**Mental model.** The self-consistent run converged the self-energy **Σ(iω_n) on the
Matsubara (imaginary) axis**, but physical spectra live on the **real axis**. Analysis
bridges the two in two one-shot steps: (1) **MaxEnt analytic continuation** turns
Σ(iω_n) → Σ(ω) (continuing an auxiliary function and inverting, because continuing Σ
directly is ill-posed), producing `Sig.out`; (2) a **single real-axis `dmft1`** embeds
that Σ(ω) back into the solid to produce the density of states and spectra.

**One-shot, not a cycle.** This is the key contrast with the set mission: the set mission's
DFT and eDMFT stages are **self-iterating cycles** launched by one submit and looped to
convergence. Here every stage is a **single post-processing pass** — it runs once, consumes
the previous output, and stops. Nothing loops.

**The cascade.** Each stage's output *is* the next stage's input — run them in order:

```
converged SC run ──[Stage 1: --alycnt]──▶ maxent/Sig.out ──[Stage 2: --gf]──▶ GF/{<CASE>.cdos, .gc1, .dlt1}
```

- Stage 2's `sig.inp` **is** Stage 1's `maxent/Sig.out` (copied in). Stage 2 also re-pulls
  the SC run's WIEN2k inputs via `dmft_copy.py`.
- Running a stage before its predecessor's output exists fails — `--gf` with no
  `maxent/Sig.out` has nothing to embed.

**Directory layout.** Analysis builds neat subdirs **inside** each `edmft-T<T>/` (the
finished SC run), one per stage — keep it tidy:

```
edmft-T<T>/            # the finished SC run (from edmft-set-skill)
├── maxent/            # Stage 1: analytic continuation → Sig.out
└── GF/                # Stage 2: real-axis dmft1 → cdos, gc1, dlt1
```

**File categories.** Four kinds of files. **This mission assembles no input files of its
own** — it consumes the finished run's outputs.

1. **Consumed files** — produced by the *previous* (set) mission, read here:
   - **`sig.inp.N.1`** — the per-iteration converged self-energies; the **last few** are
     averaged to reduce CTQMC noise (Stage 1).
   - **`maxent_params.dat`** — MaxEnt continuation parameters (the 6th input file gathered
     by `edmft-set-skill` Stage 1); copy-as-is, rarely edited.
   - **what `dmft_copy.py` pulls** for the real-axis run — `<CASE>.struct`, `in*`,
     `clmsum`, `<CASE>.indmfl`/`.indmfi`, `projectorw.dat` (Stage 2).

2. **Hand-altered control file** — generated, but edited by hand at one step:
   - **`GF/<CASE>.indmfl`** — switch to the real axis: first number of line 2 (matsubara
     flag) `1 → 0`, and set the real-axis window. The single manual edit in this skill.

3. **Output / deliverable files** — the analysis products (what Sec 3 plots):
   - **`maxent/Sig.out`** — real-axis self-energy Σ(ω).
   - **`GF/<CASE>.cdos`** — density of states (total + partial correlated-shell).
   - **`GF/<CASE>.gc1`** — orbital-resolved local Green's function (→ per-orbital DOS).
   - **`GF/<CASE>.dlt1`** — impurity hybridization function Δ(ω).

4. **Inspecting files** — read to confirm a step ran:
   - the maxent log's `Finished maxent … alpha= … ratio=` line, `:log`, `dmft1_info.out`.

---

## 2. Workflow (calculation only)


**Don't over-check.** If a command returns no error, treat it as done — don't re-read or
line-by-line compare the files it generated.

**If something goes wrong — report and stop.** If any command errors, or a stage's expected
output is missing, **report the error to the user and stop.** Do not retry, work around, or
guess a fix — a broken analysis step is usually an upstream convergence/setup problem to
surface.

**Prefer the `qdm` shortcuts.** Each stage below ends with a `qdm --<flag>` shortcut that
wraps the original commands shown. **If a `qdm` dispatcher exists at `~`, use the shortcut
and skip the manual commands.** Fall back to the original commands only when no `qdm` is present.

**Use TODO List.** For the stage/step sequence, use TodoWrite checkboxes.

**Report the steps.** When running the workflow, report the stages and steps as you go.

Resolve parameters by tier first:
- *Defaulted* — real-axis window `$omega_flag=-5..5` eV, `$broad_flag=0.025`,
  `$nomega_flag=200` (the `--gf` indmfl line); `$np_flag=16` (mpi_prefix); optional dense
  `$numk_flag` for a smooth DOS (the tutorial used 10000).
- *Must-set* — **`$siglist`**: which converged iterations to average. Use the **last few**
  (e.g. `sig.inp.6.1 … sig.inp.10.1`); the stock qdm `SIGLIST` is a placeholder and must be
  pointed at the converged tail. **`$soc_flag`** is inherited from the run (governs
  `lapwso` / `-so`).

### Stage 1 — Analytic continuation
**Consumes** the converged `sig.inp.N.1`. **Produces** `maxent/Sig.out`.

**Step 1 — Pick `$siglist`.** Choose the converged tail of self-energies to average (check
`info.iterate` / iteration count from the run to know which iterations converged).

**Step 2 — Stage the maxent dir.** `mkdir edmft-T<T>/maxent`; ensure `maxent_params.dat` is
present (gathered by `edmft-set-skill` Stage 1; else copy
`edmft-set-skill/references/templates/maxent_params.dat`). Copy it into `maxent/`.

**Step 3 — Average.** In `edmft-T<T>/`: `saverage.py $siglist` → writes `sig.inpx`; copy
`sig.inpx` into `maxent/`.

**Step 4 — Continue.** In `maxent/`: `maxent_run.py sig.inpx` → **`Sig.out`**. This anneals
for a few minutes; it's done at the `Finished maxent … alpha= … ratio=` line.

→ Shortcut: `qdm --alycnt` (averages `$siglist`, makes `maxent/`, copies params + `sig.inpx`,
runs `maxent_run.py`). **Adjust the dispatcher's `SIGLIST` to `$siglist` first.**

### Stage 2 — Real-axis Green's function / DOS
**Cascade:** consumes **`maxent/Sig.out`** — Stage 1 must be finished. **Produces**
`GF/<CASE>.cdos`, `GF/<CASE>.gc1`, `GF/<CASE>.dlt1`.

**Step 1 — Stage the GF dir.** `mkdir edmft-T<T>/GF`; `echo "mpirun -np $np_flag" >
GF/mpi_prefix.dat`.

**Step 2 — Pull inputs.** In `GF/`: `dmft_copy.py ../` (brings `struct`, `in*`, `clmsum`,
`indmfl`/`indmfi`, `projectorw.dat`).

**Step 3 — Install the real-axis self-energy.** `cp ../maxent/Sig.out sig.inp`.

**Step 4 — Switch `indmfl` to the real axis.** Edit `GF/<CASE>.indmfl` line 2: matsubara
flag `1 → 0`, window → `$omega_flag` (e.g. `0 0.025 0.025 200 -5.0 5.0`).

**Step 5 — Run once.** In `GF/`: `x lapw0 -f <CASE>` → `x_dmft.py lapw1` →
`[x_dmft.py lapwso]` (*only if* `$soc_flag`) → `x_dmft.py dmft1`.
**`-so` consistency:** `lapwso` is present **iff** spin-orbit is on — same rule as the set
mission; a mismatch silently computes wrong physics.

→ Shortcut: `qdm --gf` (makes `GF/`, `mpi_prefix.dat`, `dmft_copy.py ../`, copies `Sig.out`,
`sed`s `indmfl` to the real axis, runs `lapw0`/`lapw1`/`[lapwso]`/`dmft1`).

*Optional — smoother DOS:* densify the k-mesh (`x kgen` → `$numk_flag`, e.g. 10000) then
rerun `lapw1` + `dmft1`.

### Stage 3 — k-resolved spectral function A(k,ω) (band spectra) *(optional)*
**Optional**, like §3 plotting — the Stage 2 DOS/spectra already stand as deliverables; run
this only when a k-resolved band plot is wanted. **Parameters:** **`$klist_band`** (must-set,
no default) — the k-path file `<CASE>.klist_band`; **`$intensity_flag=1.0`** — `wakplot.py`
brightness.

**Cascade:** consumes the finished real-axis **`GF/`** (Stage 2 must be done — it reuses
`GF/`'s `sig.inp` = Σ(ω), `<CASE>.indmfl`, `struct`, `in*`). **Produces** `bd/eigvals.dat`
(the ω-dependent eigenvalues) and the A(k,ω) color plot `bd/1.png`.

**Step 1 — Locate `$klist_band`.** Check for `<CASE>.klist_band` in the project scope (local
and on the remote). **Do not generate one.** If it is not provided, by context either
**skip this optional stage** or **stop and ask the user**. If it exists only locally, put it
on the remote run dir before staging.

**Step 2 — Stage the bd dir.** `mkdir edmft-T<T>/bd`; copy the k-path
(`cp <CASE>.klist_band edmft-T<T>/bd`) and clone the real-axis run
(`cp -rf edmft-T<T>/GF/* edmft-T<T>/bd`), so `bd/` already holds `sig.inp`, `indmfl`,
`mpi_prefix.dat`, etc.

**Step 3 — `indmfl` window (follow qdm).** `qdm --bd` does **not** edit `bd/<CASE>.indmfl` —
it inherits `GF/`'s real-axis window (matsubara flag already `0` from Stage 2). Leave it as
inherited; narrow it by hand only if you want a tighter band-plot window.

**Step 4 — Eigenvalues on the path.** In `bd/`: `x lapw1 -f <CASE> -band` →
`[x lapwso -f <CASE> -band]` (*only if* `$soc_flag`) → `x_dmft.py dmftp`. `lapw1 -band`
recomputes Kohn–Sham states on the k-path; `dmftp` embeds Σ(ω) and writes **`eigvals.dat`**.
Same **`-so` consistency** rule as Stage 2.

→ Shortcut: `qdm --bd` (makes `bd/`, copies `<CASE>.klist_band` + `GF/*`, runs
`lapw1 -band`/`[lapwso -band]`/`dmftp`).

**Step 5 — Plot A(k,ω).** In `bd/`: `wakplot.py $intensity_flag` → saves `1.png` (or .pdf). Lower `$intensity_flag` if the map washes out.

→ Shortcut: `qdm --pltbd` (runs `wakplot.py` in each `bd/`).

---

## 3. Plotting (optional — separated from calculation)

Plotting is **optional** and **never required** to consider the analysis done — Section 2
stands on its own; the deliverable files are the result. This section is a self-contained
**3-stage workflow** (Preparation → Gather data → Plot) built on two small libraries kept
in this skill's `reference/` folder: **`data.py`** (the data model) and **`quickplot.py`**
(the plotting model). The driver just `import`s them — there is **no install step**.

**Physics quantities ↔ files** (columns counted Python-style, first column = column 0; files are in edmft-T<T> folder):

| Physics quantity | Main file | Iteration-wise file | Details |
|---|---|---|---|
| imaginary-axis self-energy Σ(iωₙ) | `sig.inpx` | `sig.inp.*.1` | col 0 = ωₙ; remaining columns are per-orbital (real, imaginary) pairs |
| density of states | `<CASE>.cdos` | – | col 0 = ω; col 1 = total (DFT+DMFT-level) DOS; following columns = partial DOS of the DMFT-treated orbital(s) |
| real-axis self-energy Σ(ω) | `maxent/Sig.out` | – | same column layout as the imaginary-axis self-energy |
| Green's function G(ω) | `GF/<CASE>.gc1` | – | same column layout as the imaginary-axis self-energy |

**The model.** A **mission** spans one study and may hold **several cases / temperatures**
(e.g. all the `edmft-T<T>/` run folders under one parent). **Default to a single mission**
pointed at that parent: `pull()` walks the whole tree and tags every file by its path, so
the T-points / cases stay distinguished within the one mission. Add a *second* mission only
to keep genuinely separate studies apart. Behind each folder is a *batch* of calculations
that the next parameter batch overwrites **in place** (no new folder), so the folder is
transient and the `datacol` (with its pickle) is the **durable record**: collect before a
folder is clobbered, and re-collect after each new batch.

**The formalism (data → plot).**
- `data.py` — a 3-level tree `datacol → mission → data`. A **mission** is one run-group
  (a material / phase). `mission.set([dir, title, comment], data.target[0], data.label[0],
  'edmft')` then `mission.pull()` walks `dir`, auto-discovers the eDMFT outputs (`sig`,
  `cdos`, `gc1`, `dlt1`), loads each, and — because `type='edmft'` — runs `edmft_modifier`
  to sign-correct the Im parts. A **`GF` tag** on the path marks the real-axis copies under
  `GF/`, including `GF/sig.inp`, which is the copy of `maxent/Sig.out` and so **is the
  real-axis Σ(ω)**.
- `quickplot.py` — a 3-level tree `album → page → figures`.
  `album.create_page(missions, '<tag>')` gathers every `data` of one tag across the
  missions; `page.init()` builds an overview `sketch` figure plus per-manifold figures in
  `fig_list`. `edmft_ax_modifier` sets sensible per-tag x-limits.

**Working style — interactive & append & adjust-friendly.** The formalism is meant for an
incremental notebook session where the **live objects are the state**:
- **Pickle the objects directly.** Save the whole `datacol` and the whole `album` (the
  latter *with its embedded matplotlib figures*) via `save_pkl`; reload with
  `data.load_dcl` / `qplt.load_alb`. The pickle *is* your working state, so a reload hands
  back live, editable figures — not just raw numbers.
- **Append, don't rebuild.** To add a run or a figure later, **load the `.pkl` and append
  to the existing list** (`col.mission_list.append(...)`, or add a page / append to
  `album[k].fig_list`), then `save_pkl` again — never re-walk or re-render from scratch.
- **Comment-out-when-done.** Once a figure looks right, wrap its construction / tweak code
  in a `'''…'''` block and leave the cell as a **single display line** (e.g.
  `alb.album[0].fig_list[0]`). To adjust it later, return to that block, un-comment, edit,
  re-run. The bundled samples model this.

**Samples to copy.** `reference/DataCol_sample.ipynb` (Stage 2),
`reference/Plot_sample_sketch.ipynb` (Stage 3) and `reference/Plot_sample_subtle.ipynb`
(Stage 4) are material-agnostic templates — copy one into `$PLOT_WORKDIR` and adapt.

### Stage 1 — Preparation
Resolve these **must-set** context variables (capitalized, `PLOT_`-namespaced). Take each
from context; **if any is unclear, STOP and ask the user.**
- **`$PLOT_RUN_LOC`** — where plotting runs: **remote (default)** or local. Sets the
  backend: remote → `matplotlib.use('Agg')` + `savefig` to PDF (then download the PDFs);
  local → `%matplotlib inline`.
- **`$PLOT_LIB_ENV`** — the python plotting environment: confirm `numpy` + `matplotlib`
  import there, and that `data.py` / `quickplot.py` are on `sys.path`. The libs are
  **Python-2 compatible** (a cluster env may be py2.7 / numpy 1.x / matplotlib 2.x).
- **`$PLOT_WORKDIR`** — the directory the notebook lives in and reads / writes; missions
  point at the converged run dir (which holds `GF/`).
- **`$PLOT_TARGETS`** — which outputs to plot: any subset of `sig`, `cdos`, `gc1`, `dlt1`.

### Stage 2 — Gather data → a pickled `datacol`
Copy `reference/DataCol_sample.ipynb` into `$PLOT_WORKDIR` as `DataCol.ipynb`. Build the
`datacol` **once**, pickle it, then comment the build block out.

**Step 1 — Notebook (+ stage data if local).** If `$PLOT_RUN_LOC = local`, make a
`datacopy/` folder in `$PLOT_WORKDIR` and copy the run outputs into it **preserving the
`edmft-T<T>/GF/` subtree** (so the `GF` tag still fires); the mission points at
`datacopy/`. If remote, the mission points straight at the run dir.

**Step 2 — Build the `datacol` (append → `set` → `pull`).** Create the mission *inside* the
`datacol` so it is owned there, then configure it before pulling: `pull()` only fills a
mission's `.data` — it does **not** set the member variables (`dir`, `title`, `comment`,
`target_list`, `label_list`, `type`); `set(...)` does. So `set()` **must precede** `pull()`.
Point the **one** mission at the parent that holds the study's `edmft-T<T>/` run folders —
`pull()` walks them all and distinguishes T-points / cases by path.
```python
import sys; sys.path.append('<dir with data.py / quickplot.py>')
import data
col = data.datacol()
col.mission_list.append(data.mission())                    # one mission for the whole study
col.mission_list[0].set(['<parent-of-edmft-T*-or-datacopy>', '<CASE>', '<comment>'],
                         data.target[0], data.label[0], 'edmft')   # set() configures the member vars
col.mission_list[0].pull()                                 # pull() walks all T-points; fills .data ($PLOT_TARGETS, incl. GF/ real-axis copies)
col.save_pkl('<CASE>_data.pkl')
```
Append a *second* `mission()` (its own `set`/`pull`) only to keep a genuinely separate study apart.
For a non-4f shell, pass a `label_list` generated from the run (`make_label` in
`DataCol_sample.ipynb`) instead of `data.label[0]` — see the Stage 3 material-agnostic note.

**Step 3 — Pickle, comment out, verify.** Once `save_pkl` has run, the pkl *is* the state —
**comment the whole build block out** (wrap in `'''…'''`, leave `save_pkl` / the reload line
as `#` lines) so re-running won't re-walk or duplicate. Confirm the round-trip in a fresh
cell — reload and inspect what was collected (each line = one file, with its `key_tag` and
`c_num`):
```python
col = data.load_dcl('<CASE>_data.pkl')
col.mission_list[0].show()
```
When a new batch has overwritten the folder, un-comment the build, `pull()` again (it appends
the new batch's results onto the mission), and `save_pkl`.

### Stage 3 — Sketch plot → overview figures + a pickled `album`
Copy `reference/Plot_sample_sketch.ipynb` into `$PLOT_WORKDIR` as `Plot.ipynb`, then:

**Step 1 — Reload + build album.**
```python
import data, quickplot as qplt
col = data.load_dcl('<CASE>_data.pkl')
alb = qplt.album()
for tag in [<your $PLOT_TARGETS>]:          # e.g. 'sig','cdos','gc1','dlt1'
    alb.create_page(col.mission_list, tag)  # page.init() builds sketch + fig_list
```

**Step 2 — Render & inspect the sketch.** Display a page's auto-laid-out overview with a
single line — `alb.album[k].sketch` (every manifold of one tag in one suptitled figure);
the per-manifold individual figures sit in `alb.album[k].fig_list[i]`. Check what `pull()`
gathered with `alb.album[k].mission.show()`. The `sig` page can carry many per-iteration
`sig.inp.N.1` curves — trim `alb.album[k].ax_data` to the converged tail (keep the `c_num`
window plus the averaged `inpx`) then `alb.album[k].update()` to re-draw. Figures render
inline in the notebook — no `savefig` needed to view them. Polishing individual figures
into publication form is **Stage 4**.

**Step 3 — Persist the album.** `alb.save_pkl('<CASE>_alb.pkl')` keeps the live figures
for later tweaking (reload with `qplt.load_alb`). **Append later:** `load_alb` → add a page
/ append to `album[k].fig_list` → `save_pkl`; adjust an existing figure by re-running its
(commented-out) construction block, then re-save.

Once saved, apply the comment-out discipline to the notebook itself: **wrap the whole build
block** (`load_dcl` → `album` → `create_page`/`init` → `save_pkl`) in `'''…'''`, and put a
`alb = qplt.load_alb('<CASE>_alb.pkl')` line **in front of the presentation cells** (the
`alb.album[k].sketch` / `fig_list[i]` displays). Re-running then reloads the pickled album —
live figures and all — instead of re-walking and re-rendering; un-comment the build only to
rebuild from a new `datacol`.

**Material-agnostic note — generate labels from the run, don't hardcode 4f.** `data.label[0]`
ships tuned for a **4f** shell (5/2, 7/2). `data.get` only swaps in generic `c0, c1, …` on a
**length mismatch** — so when a d-shell's column counts *coincide* with the 4f preset
(MnO: sig/gc1 = 5 cols, cdos = 3) the wrong 4f names are applied **silently**. Don't rely on
that fallback: build `label_list` from the run itself — manifold names from the
`GF/<CASE>.gc1` header, correlated-shell letter from `<CASE>.cdos`'s `L=` — and pass it to
`mission.set` in place of `data.label[0]` (see `make_label` in `DataCol_sample.ipynb`). That
labels any shell correctly (d → eg/t2g, 4f → 5/2 / 7/2) without baking in one material.

### Stage 4 — Subtle plotting
*(To be filled.)* Refining the raw Stage-3 figures into publication form — direct,
in-place adjustment of the live `album` figures (axes, curves, labels, guides), the
comment-out-when-done discipline, and the worked recipes per target — using
`reference/Plot_sample_subtle.ipynb`.

---

## When to ask
Stop and ask whenever **`$siglist`** (which iterations are converged) is unclear, the
real-axis window or `$soc_flag` is undetermined, or the run does not appear converged (check
with the set skill / `info.iterate` first). Continuing a noisy or unconverged self-energy
produces meaningless spectra.

## References (load only when needed)

- `reference/data.py` — the data model (`datacol → mission → data`, `pull`,
  `edmft_modifier`, `load_dcl`); the §3 Stage 2 backbone.
- `reference/quickplot.py` — the plotting model (`album → page → figures`, `create_page`,
  `edmft_ax_modifier`, `load_alb`); the §3 Stage 3 backbone.
- `reference/DataCol_sample.ipynb`, `reference/Plot_sample_sketch.ipynb`,
  `reference/Plot_sample_subtle.ipynb` — copy/adapt these as the Stage 2 / Stage 3 / Stage 4
  notebooks. (Worked example the formalism was distilled from:
  Haule-tutorial-style Sm 4f study — not bundled.)
