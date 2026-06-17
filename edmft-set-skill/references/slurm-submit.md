# SLURM submission — cluster-specific

Read this only when actually submitting. The `.slurm` scripts are
**SLURM-cluster-specific**: they encode one cluster's queue, node/core layout, memory
and network env, so another cluster needs its own. `params.dat` and `.machines` (in
`templates/`) are general and travel between clusters. The values below are the
**current cluster, Bohr** — treat them as that instance, not as universal.

All remote actions go through the `tmux-usage` skill (SSH-in-tmux), never raw `ssh`.

## Current cluster (Bohr) SLURM facts
- Queue (`-p`): `batch`.
- `--ntasks-per-node=64` — fixed on Bohr (must be 64; do not change).
- Nodes (`-N`): **DFT = 1 node**, **eDMFT = 2 nodes**. Total cores = N × 64 →
  `$SLURM_NTASKS`.
- Memory: `--mem=224G` (≤ 256G per node).
- Walltime: `--time=DD-HH:MM:SS` (scripts use `2-0:0:0`).
- InfiniBand env — **do not modify**:
  ```
  export FI_PROVIDER=verbs
  export UCX_NET_DEVICES=mlx5_0:1
  ```
- Threads: `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1` (one thread per MPI rank for CTQMC).
- The eDMFT script builds the MPI launcher from the allocation:
  `echo "mpirun -np $SLURM_NTASKS" > mpi_prefix.dat`.

## `dft.slurm` (Stage 2 — submitted inside `<CASE>/`)
`-N 1`. Sets threads + IB env, records hosts, then runs the Wien2k SCF. The trailing
`-so` is present only for spin-orbit cases (qdm rewrites this line from `SOTRIGGER`):
```
run_lapw -p -so
```

## `edmft_batch.slurm` (Stage 4 — submitted inside each `edmft-T<T>/`)
`-N 2`. Same env, then builds `mpi_prefix.dat` and launches the eDMFT cycle. `-so`
only for spin-orbit:
```
echo "mpirun -np $SLURM_NTASKS" > mpi_prefix.dat
run_dmft.py -p -so >& nohup.dat
```
(`-p` = parallel; `-so` = spin-orbit. `mpi_prefix.dat2`, used to give the solver a
subset of cores with OpenMP, is optional — see the MnO tutorial.)

## `.machines` (general — deploy verbatim as `.machines` in the working dir)
The bundled `templates/machines` is a documented WIEN2k parallel-control file
(`granularity`, `extrafine`, `omp_lapw1`/`omp_lapw2`, then per-rank `1:localhost`
lines). It does not need per-case adjustment on Bohr. Copy it in as `.machines` before
the DFT submit (qdm's `--dft` does this).

## qdm shortcuts (when `~/qdm` exists)
| Stage | qdm | does |
|---|---|---|
| Prepare | `qdm --init` | make `<CASE>/` + `edmft-T<T>/`, copy files, fill `beta`/`nom`, set `-so` in the scripts |
| Init DFT | `qdm --dft` | copy `dft.slurm` + `.machines`, `init_lapw` (+`initso`), `sbatch dft.slurm` |
| Prepare DMFT | `qdm --dmftinit` then `qdm --dmftset` | `init_dmft.py`; then per T `dmft_copy.py` (+`findRot.py`) + `szero.py` |
| Submit | `qdm --dmftsub` | `sbatch edmft_batch.slurm` per T |
| All | `qdm --all` | Stages 1–4 end to end |
