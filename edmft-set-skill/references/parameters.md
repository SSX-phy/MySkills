# eDMFT parameters reference

Every tunable is tagged **[default=…]** (apply if unspecified) or **[MUST-ASK]** (no
default — ask the user if the context does not give it). Values shown are the MnO
tutorial values; the f-electron column notes the SmCo5-type target.

## `init_dmft.py` flags (→ `case.indmfl`, `case.indmfi`, `projectorw.dat`)

| Flag | Meaning | Tier | MnO | f-electron (SmCo5) |
|---|---|---|---|---|
| `-ca` | correlated atoms (indices in `case.struct`; every atom counts, even equivalent ones) | **MUST-ASK** | `1` (Mn) | Sm and Co indices |
| `-ot` | orbital type per correlated atom (`d`/`f`) | **MUST-ASK** | `d` | `f` (Sm), `d` (Co) |
| `-qs` | qsplit / local basis per orbital (table below) | **MUST-ASK** | `7` (cubic) | `4` (\|j,mj⟩, l±½ — needed with SO) |
| `-p` | projector type | **[default=5]** | `5` | `5` |
| spin-orbit prompt | "Is this a spin-orbit run?" | **MUST-ASK** | `n` | `y` |

Projector 5 = fixed projector written to `projectorw.dat`; required for a stationary
functional (free energy / forces). Use it unless you have a specific reason not to.

### qsplit table
```
 0  average GF, non-correlated
 1  |j,mj> basis, no symmetry, except time reversal (-jz=jz)
-1  |j,mj> basis, no symmetry, not even time reversal
 2  real harmonics basis, no symmetry, except spin (up=dn)
-2  real harmonics basis, no symmetry, not even spin
 3  t2g orbitals
-3  eg orbitals
 4  |j,mj>, only l-1/2 and l+1/2          <- typical f-electron + spin-orbit
 5  axial symmetry in real harmonics
 6  hexagonal symmetry in real harmonics
 7  cubic symmetry in real harmonics       <- MnO (cubic d, no SO)
 8  axial, up != down
 9  hexagonal, up != down
10  cubic, up != down
11  |j,mj> basis, non-zero off-diagonal
12  real harmonics, non-zero off-diagonal
13  J_eff=1/2 basis for 5d ions, non-magnetic with symmetry
14  J_eff=1/2 basis for 5d ions, no symmetry
```
The CTQMC ignores off-diagonal hybridization by default, so the choice of basis
matters: pick the basis where hybridization is (near-)diagonal for the local symmetry.

## DFT init flags (`init_lapw`)
| Flag | Meaning | Tier |
|---|---|---|
| `-vxc` | XC functional (13 = PBE) | **[default=13]** |
| `-ecut` | core/valence separation energy (Ry) | **[default=-6.0]** |
| `-rkmax` | plane-wave cutoff RKmax | **[default=7]** |
| `-numk` | k-points in the full BZ (DMFT wants more, e.g. 2000+) | **[default=500]** |

## `params.dat` — top-level fields
| Field | Meaning | Tier |
|---|---|---|
| `solver` | impurity solver | **[default='CTQMC']** |
| `max_dmft_iterations` | DMFT steps per global iteration | **[default=1]** |
| `max_lda_iterations` | DFT charge steps per DMFT step | **[default=100]** |
| `finish` | max global (charge) iterations | **[default=50]** (MnO used 10) |
| `ntail` | log-mesh points in the high-frequency tail | **[default=300]** |
| `cc` / `ec` | charge / energy convergence tolerance | **[default=5e-6]** |
| `recomputeEF` | recompute Fermi level in dmft2 (0 = fixed, good for insulators; 1 = metals) | **MUST-ASK** |
| `DCs` | double-counting scheme (below) | **MUST-ASK** |
| `wbroad` / `kbroad` | self-energy broadening (only for Matsubara sampling, i.e. svd_lmax=0) | **[default=0.0]** |

## `params.dat` — `iparams0` (impurity dict; one dict per impurity: iparams0, iparams1, …)
| Key | Meaning | Tier |
|---|---|---|
| `exe` | solver executable | **[default='ctqmc']** |
| `U` | Coulomb repulsion F0 (eV); larger than downfolded-DMFT because screening is explicit | **MUST-ASK** |
| `J` | Hund coupling (eV); can be estimated from U via `RCoulombU.py -U <U>` | **MUST-ASK** |
| `CoulombF` | `'Ising'` (density-density, fast) or `'Full'` (rotationally invariant) | **[default='Ising']** (physics-sensitive — confirm) |
| `beta` | inverse temperature (1/eV) = `11604.534 / T[K]` | **MUST-ASK** (via T) |
| `nom` | sampled Matsubara points ≈ 2–4 × beta | **[default≈2·beta]** (derived) |
| `svd_lmax` | SVD basis cutoff for G (0 = direct Matsubara sampling) | **[default=25]** |
| `M` | Monte-Carlo steps per core (total = M × Ncores) | **[default=5e6]** |
| `mode` | sampling/tail mode: `SH` (sample Σ + Hubbard-I tail), `GH`, `SM`, … | **[default='SH']** |
| `tsample` | how often to record measurements | **[default=30]** (tutorial used 30–100) |
| `GlobalFlip` | how often to attempt a global spin flip , must less than or equal 0.1 M  | **[default=500000]** |
| `warmup` | discarded warmup MC steps (small if continuing from `status.*`) | **[default=1e5]** |
| `nf0` | expected nominal valence (starting double-counting) | **MUST-ASK** |
| `Nmax` | perturbation-order cutoff (check `histogram.dat` reaches 0 before it) | **[default=500]** |

## Double-counting (`DCs`) — MUST-ASK
- `'nominal'` — most stable; uses `nf0`. Close to exact (PRL 115, 196403).
- `'exacty'` — exact DC, Yukawa screening; good for many metals.
- `'exactd'` — exact DC, dielectric screening; good for some insulators (MnO).
- `'exact'` — combination of Yukawa + dielectric (often best); may need `recomputeEF=1`
  for a few steps to move μ, then back to 0.
- `'FLL'` — fully-localized limit; **not recommended**.

## Temperature → beta / nom
- `beta = 11604.534 / T[K]` (1/eV).
- `nom = round(NOMRATE · beta)`, with `$NOMRATE_flag=2` (tutorial guidance: 2–4×beta).
- The starting self-energy `szero.py` reads `beta` and `nf0` from `params.dat` and sets
  the Anisimov double-counting `VDC = U·(nf0−½) − J/2·(nf0−1)`.
