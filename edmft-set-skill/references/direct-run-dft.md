# Direct-run DFT (login-node, skip-queue)

The **alternative** to submitting the DFT cycle through the scheduler (Stage 2): run
`run_lapw` directly on the login node, skipping the queue. The default is scheduler
submission — use this only when the material clearly qualifies.

## When to use
- **Easy-to-calculate materials only.** <!-- TODO(user): define the criterion —
  cell size / k-points / expected runtime. To be specified later. -->
- **DFT only — never the DMFT cycle.** `run_dmft.py` always goes through the scheduler.

## How
In `<CASE>/`, after `init_lapw` (Stage 2 Step 2), launch the cycle directly — no
`qsub`/`sbatch`, no `dft_submit`:

```
run_lapw          # add -so for a spin-orbit run
```

The cycle auto-loops `lapw0 → lapw1 → [lapwso] → lapw2 → lcore → mixer` to charge
convergence (never reaches `dmft1`) — identical to the submitted run; only the launch
path differs.

## Why it is the non-default
Login-node compute steals shared resources and has no scheduler accounting; it is a
convenience for cheap DFT, not for production. Anything expensive — and all DMFT — goes
through the queue.

## Watching
Direct run is a foreground process in your tmux pane — there is no scheduler job, so Section 3
does not apply. Just watch the `run_lapw` process end (the cycle stops on its own at charge
convergence), then confirm `<CASE>.scf` is fresh.
