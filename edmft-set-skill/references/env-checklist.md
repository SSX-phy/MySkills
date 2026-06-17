# Environment checklist — eDMFT + WIEN2k on the remote server

**When to use this — almost never.** The remote cluster is a **trusted, pre-configured**
machine; its shells normally provide the WIEN2k + eDMFT toolchain automatically. Do **not**
run this as a routine step. Use it only when:
- the user **explicitly asks** you to verify the environment, or
- a later command fails with `command not found`, or `$WIEN_DMFT_ROOT` comes back **empty**
  (the symptom that the eDMFT environment is not active in the shell you are driving).

Otherwise skip it and go straight to Stage 1 Step 1.

## Checks
Run these in the remote shell you drive (via the `tmux-usage` skill) and read the output:

1. **Root variables** — `echo "$WIEN_DMFT_ROOT" "$WIENROOT"`
   → both should print a non-empty path (the eDMFT `bin` and the WIEN2k root). Empty ⇒ env not active.
2. **Core executables on PATH** — `which init_lapw init_dmft.py run_dmft.py x_dmft.py dmft_copy.py szero.py`
   → each should resolve to a path. A `no <x> in …` line ⇒ env not active.
3. **Python interpreter** — `which python; python --version`
   → confirm the interpreter the eDMFT scripts expect resolves (older eDMFT builds expect a
   specific Python 2.x).
4. **(analysis only)** `which maxent_run.py saverage.py` — needed by `edmft-aly-skill`.

## Interpreting
- **All resolve** → environment is healthy; proceed.
- **Missing / empty** → the toolchain is not active **in this shell**. The cause is
  **site-specific** (e.g. a login vs non-login shell reading different startup files, an
  environment module that wasn't loaded, or an activation script that wasn't run). **Do not
  guess or hardcode a fix** — report the gap to the user and ask how the site activates its
  eDMFT/WIEN2k environment, then apply exactly that.

## Note for batch jobs
Scheduler scripts (`sbatch` / `qsub`) run as **non-interactive, non-login** shells, so they
may not read the same startup files an interactive login shell does. Make sure the
environment actually reaches the job — either the submit command exports the current
environment (e.g. SLURM `--export=ALL`, the default) **or** the submit script activates the
environment itself per the site's convention. If a job dies immediately with a
`command not found`, this is the first thing to check.
