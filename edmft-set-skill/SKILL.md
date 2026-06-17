---
name: edmft-set-skill
description: Set up and submit a WIEN2k + embedded-DMFT (Haule eDMFT) calculation on a remote server — prepare inputs, run the DFT initialization, prepare the DMFT step, and submit the eDMFT self-consistent run. Use when the user wants to start, configure, or launch an eDMFT/DFT+DMFT calculation. Not for analyzing finished results (that is edmft-aly-skill).
---

# eDMFT setup & submit (WIEN2k + Haule eDMFT, on a remote server)

This skill covers **setup + submit only**: from a structure to a running eDMFT
self-consistent job. Analysis / analytic continuation / DOS is the separate
`edmft-aly-skill`; the `edmft` subagent holds the global picture and routes between
the two. Calculations run on the **remote server** — drive it through the
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
- `$name_flag` (no `=`) → **must-ask**: no default. If it is not given in the context,
  **STOP and ask the user.** These are the physics choices that define the problem.

This is a complex program where a wrong choice (qsplit, double-counting, spin-orbit)
silently produces wrong physics. When a structural choice or a must-ask parameter is
undetermined, ask — do not guess.

---

## 1. Global picture

**Mental model.** eDMFT = Wien2k DFT + DMFT, combined through the *stationary*
Luttinger-Ward functional. The correlated subshell (Mn-d here; Sm-f / Co-d for the
SmCo5 target) is projected out by a **fixed real-space projector** (`-p 5`, written to
`projectorw.dat`) — fixing it is what keeps the functional stationary — and solved
dynamically by the **CTQMC** impurity solver. All other states stay at the DFT level
but are not removed.

**Two auto-cycles.** A *cycle* is launched by one human submit and then loops to
convergence on its own. Know the components; do **not** try to control the internals.

- **DFT cycle** (Stage 2): `lapw0 → lapw1 → [lapwso] → lapw2 → lcore → mixer`,
  iterated to charge convergence. This is a plain Wien2k run — it **never reaches
  `dmft1`**.
- **eDMFT cycle** (Stage 4): `lapw0 → lapw1 → [lapwso] → dmft1 → impurity(CTQMC) →
  dmft2 → lcore → mixer`, iterated to `finish`. `dmft2` replaces `lapw2`; the impurity
  runs between `dmft1` and `dmft2`. Inside it, a DFT charge sub-loop
  (`$max_lda_iterations_flag`, tolerances `$cc_flag`/`$ec_flag`) runs at fixed
  self-energy, nested inside the DMFT loop (`$max_dmft_iterations_flag`).

**Directory layout (two-stage).** One DFT directory + one eDMFT directory per
temperature:
```
<CASE>/            # Wien2k DFT (init + run); name == <CASE>.struct base name
edmft-T<T>/        # one per temperature T (K); the eDMFT run lives here
```

**File categories.** Four kinds of files, each handled differently.

1. **Input files** — the six you assemble in Stage 1 (see the Stage 1 checklist).
   Everything in the other categories is produced by the program from these.
   - **`<CASE>.struct`** — Wien2k crystal structure; the DFT dir shares its base name.
     If only a `.cif` is given, convert with `cif2struct`. Read by `init_lapw`.
   - **`params.dat`** — impurity-solver + iteration-control file (Python). Holds the
     must-ask physics (`$U_flag`, `$J_flag`, `$beta_flag`, `$nf0_flag`, `$DCs_flag`,
     `$recomputeEF_flag`) and the defaulted solver knobs; one copy per `edmft-T<T>/`
     with `beta`/`nom` set from that T.
   - **`dft_submit`** — DFT scheduler script (PBS `qsub` / SLURM `sbatch`); launches the
     DFT cycle. The default launch path (the login-node skip-queue is the easy-material alt). Named in a form <Type>_<QueueType>.<Manage_System> like `dft_batch.slurm`. 
   - **`edmft_submit`** — eDMFT scheduler script; launches the eDMFT cycle. DMFT always
     goes through the scheduler. The same naming convention applies, e.g. `edmft_batch.slurm`.
   - **`.machines`** — WIEN2k k-point-parallel granularity. *Conditional* — N/A when the
     DFT runs sequentially.
   - **`maxent_params.dat`** — MaxEnt analytic-continuation parameters (Python dict). Used
     later by `edmft-aly-skill` to continue Σ(iω)→Σ(ω); gathered now because it is a
     copy-as-is file that rarely needs editing — copy from a sibling case or the skill template.

2. **Inspecting files** — read to check the program's internal state *while it runs*.
   They can be long → **read only the last N lines** unless more is needed.
   - **`:log`** — WIEN2k/eDMFT command journal: every `x <module>` call with a timestamp,
     so you can see exactly which steps ran and in what order.
   - *(more to be added)*

3. **Intermediate control files** — generated by the program, but at certain steps you
   alter them by hand.
   - **`<CASE>.indmfl`** — the main solid↔impurity connector from `init_dmft.py`:
     hybridization window, projector type, correlated atoms, qsplit, the `Sigind` matrix
     (which orbitals are equivalent), and the transformation to the DMFT basis.
   - **`<CASE>.indmfi`** — the impurity-side companion; repeats the impurity `Sigind` blocks.
   - *(more to be added)*

4. **Important intermediate files** — usually you only check their **existence** and
   **last-modified time** to confirm a step ran; you rarely open them.
   - **`<CASE>.scf`** — the DFT SCF output/history; its existence and fresh mtime confirm
     the DFT cycle finished. Watch the run end rather than reading it.
   - *(more to be added)*

---

## 2. Workflow

**Think in parallel for multiple runs.** When the case spans several runs (multiple
temperatures and/or cases), do **not** serialize them — never drive one run to convergence
before the next is submitted. Run **Stage 4 (submit)** for *every* `<CASE>_<T>` first, and
**enter Stage 5 (watch) only after every run's Stage 4 is finished**. They then share the
scheduler queue and round-robin on limited resources (one runs, the others pend — expected, not
a problem to fix).

**Don't over-check.** If a command returns no error, treat it as done — don't re-read or
line-by-line compare the files it generated.

**If something goes wrong — report and stop.** If any command in these stages errors, or a
final check finds an expected file missing, **report the error to the user and stop.** Do not
retry, work around, or guess a fix — a broken step here is a setup/physics problem to surface,
not to patch. (Same posture as the job-failure rule in Section 3.)

**Prefer the `qdm` shortcuts.** Every stage below ends with a `qdm --<flag>` shortcut that
wraps the original commands shown. **If a `qdm` dispatcher exists at `~` , use the
shortcut and skip the manual commands** — `qdm --all` even runs Stages 1–4 end to end. Fall
back to the original commands only when no `qdm` is present.

**Use TODO List** For check steps , use todo list checkboxes.

**Report the steps** When running the workflow, report the stages and steps as you go.

### Stage 1 — Prepare
Goal: assemble the **six input files** in the **case root** (`$REMOTE_SCOPE_ROOT`) and
verify them. Prepare only gathers them in one place — generating the `<CASE>/` and
`edmft-T<T>/` subfolders and copying files in is the **start of Stage 2**. Track the steps
as a **TodoWrite checklist**; Prepare is done when each file is present in the case root
(or explicitly marked **N/A**).

Resolve parameters by tier first — steps 2–4 (and later `init_dmft.py` + DFT) draw on these:
- *Defaulted* — apply if unspecified: `$vxc_flag=13`, `$ecut_flag=-6.0`, `$rkmax_flag=7`,
  `$numk_flag=500` (DFT init); `$proj_flag=5`; solver knobs `svd_lmax`, `M`, `mode`, `ntail`,
  `max_*_iterations`, `finish` (see `references/parameters.md`).
- *Must-ask* — if not in context, **ASK**: temperature list `$T_flag` (→ beta), `$U_flag`,
  `$J_flag`, `$nf0_flag`, correlated atoms `-ca $ca_flag`, orbital `-ot $ot_flag` (d/f),
  `-qs $qs_flag`, double-counting `$DCs_flag`, spin-orbit on/off `$soc_flag`, `$recomputeEF_flag`, and
  whether the case is magnetic / needs local-axis rotation.

**Step 0 — Environment check (skip by default).** The remote server is **trusted and
pre-configured** — assume the WIEN2k + eDMFT toolchain is already active and go **straight to
Step 1**. Do **not** run an environment check as routine. Consult
`references/env-checklist.md` **only when** the user explicitly asks you to verify the
environment. If you do check,
**surface any gap to the user** rather than guessing or hardcoding a fix.

**Step 1 — Preparation: check what already exists.** `ls` the case root and test for each of the six:
`<CASE>.struct`, `params.dat`, `dft_submit`, `edmft_submit`, `.machines`, `maxent_params.dat`.
Any file already present and valid → **skip its get-step below**; this lets you safely re-enter Stage 1.

**Step 2 — Get `<CASE>.struct`** . Wien2k crystal structure; take the
path from context — **if context doesn't say where it is → ASK the user.** If only a `.cif`
is given, convert with `cif2struct`. Land it in the case root.

**Step 3 — Get `params.dat`** . Impurity-solver + iteration control (Python).
Fill `references/templates/params.dat` with the resolved parameters, **asking for any must-ask
not in context**; set `beta = 11604.534/T` and `nom ≈ NOMRATE·beta` (`$NOMRATE_flag=2`). Land
it in the case root.

**Step 4 — Get the submit files, `.machines`, and `maxent_params.dat`** . These are the
copy-as-is files that usually don't need per-case adjustment.

**First search the files from `*/EDMFT/` folder**, which usually the upper level of the working directory.

- **`dft_submit`** — DFT scheduler script (generic name; content scheduler-specific, PBS
  `qsub` / SLURM `sbatch`).  **if none found, write one from `references/slurm-submit.md`.**
- **`edmft_submit`** — eDMFT scheduler script (generic name). **Else write one from the skill reference.**
- **`.machines`** — WIEN2k k-point-parallel granularity.  else write from `references/templates/machines`.** 
- **`maxent_params.dat`** — MaxEnt analytic-continuation parameters (used later by
  `edmft-aly-skill`). Rarely edited. **Else copy `references/templates/maxent_params.dat`.**

**Check the `-so` flag matches `$soc_flag`.** The run command in each submit file must carry
`-so` **iff** spin-orbit is on: SO run → `run_lapw -so` in `dft_submit` **and** `run_dmft.py -so`
in `edmft_submit`; non-SO run → neither has `-so`. A mismatch silently computes the wrong
physics, so verify it here. 

**Step 5 — Final check.** `ls` the case root and confirm all six are present (or N/A):
`<CASE>.struct` header sane; `python params.dat` parses with the right `beta`/`nom`; each
submit script matches the cluster scheduler; `.machines` present or N/A; `maxent_params.dat`
present (copy-as-is).

### Stage 2 — Init DFT

**Step 1 — Preparation: distribute the prepared files into run dirs.** Create `<CASE>/` (name ==
`<CASE>.struct` base) holding `<CASE>.struct` (+ `dft_submit`, and `.machines` if used);
create one `edmft-T<T>/` per temperature holding `params.dat` + `edmft_submit`.
→ Shortcut: `qdm --init` (if a `qdm` exists at `~`) — makes the subfolders, copies the files
in from the root, and fills each `edmft-T<T>/`'s `beta`/`nom`.

**Step 2 — Initialize the DFT.** In `<CASE>/`: `init_lapw -b -vxc $vxc_flag=13
-ecut $ecut_flag=-6.0 -rkmax $rkmax_flag=7 -numk $numk_flag=5000`; then `initso` *only if
spin-orbit*. `initso` is interactive: press **Enter** to accept each default option, **except**
answer **`N`** then Enter to *"Do you have a spinpolarized case (and want to run symmetso)? (y/N)"*.

**Step 3 — Check how to run.** Decide how to launch the DFT cycle (`run_lapw`):
- **(default) Submit through the system** — go to Step 4.
- **(alt) Direct run on the login node** — skip the queue; *easy-to-calculate materials
  only, DFT only — never the DMFT cycle*. See `references/direct-run-dft.md` .

**Step 4 — Submit the DFT cycle through the system (long waiting).** `qsub dft_submit` (PBS) /
`sbatch dft_submit` (SLURM)  The cycle auto-loops `lapw0 → lapw1 → [lapwso] → lapw2 → lcore → mixer` to charge convergence
(never reaches `dmft1`). → Shortcut: `qdm --dft`.

**Step 5 — Final check: confirm the DFT cycle ended.** Submitted path: track `$JOB_ID` per Section 3 (same
watch as any scheduler job) — when it leaves the queue, a fresh `<CASE>.scf` means done.
Also see :log.


### Stage 3 — Prepare DMFT
Human operations only — no cycle.

**Step 1 — Preparation: confirm the DFT output is in place.** In `<CASE>/`, check the
existence of `<CASE>.scf` (DFT cycle finished) and `<CASE>.struct` (structure). Both must be
present before `init_dmft.py` can run.

**Step 2 — Initialize the DMFT inputs** (the main body of this stage). In `<CASE>/`:
`init_dmft.py -ca $ca_flag -ot $ot_flag -qs $qs_flag -p $proj_flag=5` (answer the
spin-orbit question). Generates `case.indmfl`, `case.indmfi`, and `projectorw.dat`.
*(MnO example: `-ca 1 -ot d -qs 7 -p 5`, SO = no. SmCo5: f on Sm, d on Co, qsplit 4 for the
f |j,mj> basis, SO = yes — confirm the must-ask values.)* → Shortcut: `qdm --dmftinit`.

**Step 3 — Final check.** Confirm `case.indmfl` and `case.indmfi` exist in `<CASE>/`.

### Stage 4 — Submit DMFT
One human operation per temperature launches the **eDMFT cycle**. For multiple runs, do this
stage for *all* of them before moving to Stage 5 (parallel note, top of Section 2).

**Step 1 — Preparation: populate and verify each `edmft-T<T>/`.** Stage the per-temperature
run dirs and confirm they are ready — preparation here includes *running commands*, not only
copying files:
- **Populate.** Run `dmft_copy.py <path-to-CASE>` (brings struct, `in*`, `clmsum`,
  `indmfl`/`indmfi`, `projectorw.dat`), then `szero.py` (blank `sig.inp`), and `findRot.py`
  *only if* local-axis rotation is needed. → Shortcut: `qdm --dmftset`.
- **Verify.** `case.indmfl` header sane (band window, projector 5, correlated-atom lines,
  `Sigind`, transformation matrix), `case.indmfi` matches, `sig.inp` present, and each
  `params.dat` has the right `beta`/`nom`.

**Step 2 — Submit the eDMFT cycle (long waiting).** Inside each `edmft-T<T>/`, submit
`edmft_submit` with the scheduler (`qsub edmft_submit` on PBS / `sbatch edmft_submit` on
SLURM) — **always through the scheduler; no login-node shortcut for DMFT.** The script writes
`mpi_prefix.dat` (and `.dat2` for the solver) from the core count, then runs
`run_dmft.py [-so] > nohup.dat`. The cycle auto-loops
`lapw0 → lapw1 → [lapwso] → dmft1 → impurity → dmft2 → lcore → mixer` up to `finish`.
→ Shortcut: `qdm --dmftsub` (per T) — or `qdm --all` to run Stages 1–4 end to end.

### Stage 5 — Watch
Enter this stage **only after every run's Stage 4 has been submitted** (parallel note, top of
Section 2). Watch all runs together and act on whichever is currently running. The detailed
mechanics — job-state polling, the dynamic wakeup schedule, and the no-question rule — are in
**Section 3**.

**Step 1 — Watch** (don't intervene unless it's wrong).
**Job state:** track `$JOB_ID` per Section 3 (queued / running / done — same as any scheduler job).
**Pacing:** when a job flips **pending → running**, reset the wakeup to the **30 min** default
(then tighten per Section 3 as it nears `finish`).
**Calculation progress** (DMFT-specific):
- `:log` — module sequence is running in order.
- `sig.inp.*.1` — the self-energy file, the number at " * " is the DMFT iteration,track and report the iteration number. Watch it is enough if the iteration running fast(if the iteration number is increasing in 6 hours). 
- `imp.0/`— The M in `params.dat` is the number of CTQMC measurements per DMFT step; and `imp.0/nohup_imp.out.000` report the impurity solver's steps at global_flip number. This is a important window as the impurity step is the most time costly step in the DMFT loop.Report this if the impurity step is over 2 hour which can be checked in the :log in edmft folder.

**Step 2 — Interfere** (the one controlled exception to Step 1's "don't intervene"). If a run is
**walltime-bounded** — a single job can't reach `finish` — run the estimate → cancel → renumber
→ resubmit loop from **Section 3 ("Walltime-bounded runs — loop Stage 4 ⇄ Stage 5")**:
benchmark the impurity step, estimate the iterations that fit the walltime, and dance the run
across jobs until its sig count reaches `finish`. Otherwise leave the auto-cycle alone.

**Step 3 — Final check.** Confirm the run completed its DMFT iterations: check the existence
of `sig.inp.$DMFT_LOOP_NUM.1` in the `edmft-T<T>/`, where `$DMFT_LOOP_NUM` is set by context,
else defaults to the `finish` value in `params.dat`. For multiple runs, the case is done only
when every run passes this check.


---

## 3. Watching a scheduler job

A submitted job (Stage 2 default path; Stage 4 always) is watched on **two layers**:
- **Job state** — queued / running / finished / failed. Ask the scheduler. **Identical for
  DFT and DMFT.**
- **Calculation progress** — is the physics converging? Read the working-dir files
  (`:log`, `nohup.dat`, `info.iterate`, …). Per-stage — DFT see Stage 2, DMFT see Stage 5.

At submit, hold the **job ID** the scheduler prints as an inline context variable —
**`$JOB_ID = <id>`** — and use `$JOB_ID` in every state/cancel command below.

**Don't live-watch — use the schedule (`/loop` dynamic mode / `ScheduleWakeup`).** Queue waits
and run times run to hours or days, and the tmux→SSH link drops on idle; the job runs on the
cluster **independently of the session**. So record `$JOB_ID` + the working dir and check back
through a **self-scheduled wakeup** (`/loop` / `ScheduleWakeup`), not a held-open watch.
**Never pause the watch with a question.** `AskUserQuestion` halts the self-paced loop until the
user returns (possibly hours). For anything the watch already covers — queue contention, a job
pending behind another user, "keep waiting" — just reschedule the wakeup and poll; do not ask.
**The loop shifts its wakeup time dynamically** across four scales — **5 min**, **15 min**,
**30 min (default)**, **1 h** — coarse when the job is far from done, fine as it nears finish.
**While queued (`Q`/Idle), each wakeup does three things in order:**
1. **Check job state** —  Use `$JOB_ID` check mission state. If it left `Q` (now `R`, done, or failed), drop this
   queueing logic and handle that case.
2. **Decide whether to re-estimate** — only once per hour, not every wakeup (the estimate is
   the costly call).
3. **If due, estimate and re-pace** — run `showstart $JOB_ID` (+ `showq`), report the queue and
   time-to-start, and set the next wakeup from it: **> 3 h → 1 h**; **1–3 h → 30 min**;
   **< 1 h → 15 min**. If not due, re-arm the current interval.

**Wakeup-time shift (running stage) — the main label is the impurity (CTQMC) step's wall cost,** read from `:log`. Pace the `/loop` with the Section 3 intervals (5 / 15 / 30 / 60 min):
- impurity step **> 1 h** → set the wakeup to **1 h** — finer than one iteration just polls an unchanged file.
- impurity step **≤ 1 h** → the **30 min** default, tightening to 15 / 5 min as the iteration count (`sig.inp.*.1`) nears `finish`.


Make "done" cheap and reliable so one check settles it:
- **Sentinel file** *(primary)* — submit script writes one when the run ends, e.g.
  `echo $? > STATUS.done`; one `cat STATUS.done` gives finished **and** exit status.
- **Scheduler mail** *(bonus)* — `--mail-type=END,FAIL --mail-user=<addr>` (SLURM) /
  `-m abe -M <addr>` (PBS); only if the cluster has a mail relay.
- **Queue-empty** *(fallback)* — `$JOB_ID` gone from `qstat`/`squeue` = finished, but can't
  tell success from crash; confirm with the sentinel or output file.

### Walltime-bounded runs — loop Stage 4 ⇄ Stage 5 (with renumbering)

When one scheduler job's walltime can't reach `finish` (short queues, e.g. a 1-h debug limit),
drive each run as a **Stage 4 → Stage 5 → Stage 4 → …** loop until its sig count hits `finish`:

- **Estimate, then cancel (Stage 5).** After iteration 1, read the impurity (CTQMC) step's wall
  time from `:log`; estimate how many iterations fit the walltime and when the last finishes.
  When that last `sig.inp.*.1` is written, `scancel` the job (don't let walltime kill it
  mid-iteration; if it does, same effect — the clean sigs are kept).
- **Renumber, then resubmit (re-entering Stage 4).** A resubmit **resets the iteration counter
  to 1**, so the new run's `sig.inp.1.1, 2.1, …` would overwrite the banked ones. *First* shift
  the existing files out of the low slots — **`mv` only, never `rm`** — by the **max existing
  index** (not the count, so gapped numbering doesn't collide), high→low:
  `maxn=<highest index>; for k=maxn..1: mv sig.inp.k.1 → sig.inp.(k+maxn).1`. Then submit as in
  Stage 4.
- **Repeat** until the run's total `sig.inp.*.1` count = `finish`; then it's done → analysis.

`mv` preserves mtime, so mtime is the true convergence order even after the renames. When a run
finishes, optionally renumber the kept sigs to contiguous `1..finish` by mtime (oldest→1),
moving any surplus aside (`dropped_sig_N`) — never deleting. Multiple runs loop independently
and round-robin on the shared node (parallel note, Section 2).

### qsub system (PBS / Torque)
- **Submit** → prints a job ID like `12345.head`; set `$JOB_ID`.
- **State** — `qstat -u <user>` or `qstat $JOB_ID`: `Q` queued, `R` running, `C` completed,
  `E` exiting. `showq` groups running/idle/blocked; `showstart $JOB_ID` estimates start.
  Detail: `qstat -f $JOB_ID`.
- **Output** — `<script>.o<JOB_ID-number>` (stdout) / `.e<…>` (stderr) in the submit dir;
  live progress is in the job's working-dir files (`nohup.dat`, `:log`).
- **Done** — job leaves `qstat` (or shows `C`). **Cancel:** `qdel $JOB_ID`.

### slurm system (SLURM)
- **Submit** → prints `Submitted batch job 12345`; set `$JOB_ID`.
- **State** — `squeue -u <user>` or `squeue -j $JOB_ID`: `PD` pending, `R` running,
  `CG` completing, `CD` completed, `F` failed. `squeue --start -j $JOB_ID` estimates start.
  Detail: `scontrol show job $JOB_ID`; after it ends, `sacct -j $JOB_ID`.
- **Output** — `slurm-$JOB_ID.out` in the submit dir (or the `#SBATCH -o` path); written live.
- **Done** — job leaves `squeue` (or shows `CD`). **Cancel:** `scancel $JOB_ID`.

**If the job fails — report and stop.** When a check says it didn't work (sentinel exit ≠ 0,
state `F`/`E`, or the queue is empty with no fresh `<CASE>.scf`), read the **last lines of the
run's output** — `nohup.dat` in the working dir, plus the scheduler files (`.o<JOB_ID>`/`.e<JOB_ID>`
on PBS, `slurm-$JOB_ID.out` on SLURM) — **report the error to the user and stop.** Do not retry,
re-submit, or try to fix it yourself; a failed eDMFT run is a setup/physics problem to surface.

For an **unattended** wait that must outlive the session, a `durable` `CronCreate` job is the
fallback (fixed cadence, 7-day cap); its prompt can delegate the check to the `edmft` subagent.

---

## When to ask
Stop and ask the user whenever a **must-ask** parameter is missing, or a structural
choice (which atoms are correlated, qsplit/basis, double-counting, spin-orbit,
magnetism/rotation, metal vs insulator → `recomputeEF`) is not determined by the
context. Wrong choices here fail silently as wrong physics.

## References (load only when needed)
- `references/parameters.md` — full `init_dmft.py` flags, the qsplit table, every
  `params.dat` field, and the double-counting schemes; each tagged *defaulted (value)*
  or *must-ask*. Read it when you need a value or meaning not covered above.
- `references/templates/params.dat` — the placeholder `params.dat` to fill.
- `references/templates/maxent_params.dat` — copy-as-is MaxEnt analytic-continuation
  parameters; drop into the case root at Stage 1 Step 4 if none is found in `*/EDMFT/`.
- `references/direct-run-dft.md` — the alt to scheduler submission: running the DFT cycle
  directly on the login node (easy materials, DFT only). Read at Stage 2 Step 3 if the
  material may qualify.
- `references/slurm-submit.md` — SLURM submission specifics: queue, nodes/tasks,
  InfiniBand env, how `mpi_prefix.dat` is built, and what `dft.slurm` /
  `edmft_batch.slurm` / `.machines` contain. **The `.slurm` scripts are
  cluster-specific** (values shown are for the current remote server) — read this only
  when actually submitting.
- `references/qdm` — the `qdm` dispatcher that wraps the commands in this skill with `--<flag>` shortcuts
- `references/env-checklist.md` — how to verify the remote eDMFT/WIEN2k environment. **Skip by
  default** (the server is trusted); used only at Stage 1 Step 0, when instructed or when a
  command errors with `command not found` / empty `$WIEN_DMFT_ROOT`.