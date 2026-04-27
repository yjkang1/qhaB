# qhaB

A driver for benchmarking the coefficient of thermal expansion (CTE) of
crystalline solids within the quasi-harmonic approximation (QHA), using
universal machine-learning interatomic potentials (uMLIPs) as the underlying
energy/force model. Atomic relaxations and single-point evaluations are
delegated to [ASE](https://wiki.fysik.dtu.dk/ase/); harmonic phonons,
thermal properties, and the QHA fit are obtained from
[phonopy](https://phonopy.github.io/phonopy/).

## Theory

The Helmholtz free energy at volume $V$ and temperature $T$ is decomposed as

$$
F(V,T) \;=\; U_{\mathrm{el}}(V) \;+\; F_{\mathrm{ph}}(V,T),
$$

where $U_{\mathrm{el}}(V)$ is the static (clamped-ion) energy obtained from
the uMLIP and $F_{\mathrm{ph}}(V,T)$ is the harmonic vibrational free energy
evaluated on the dynamical matrix at volume $V$,

$$
F_{\mathrm{ph}}(V,T) \;=\; \tfrac{1}{2}\sum_{\mathbf{q}\nu}\hbar\omega_{\mathbf{q}\nu}(V)
\;+\; k_{\mathrm{B}}T\sum_{\mathbf{q}\nu}\ln\!\Bigl[1-\exp\!\bigl(-\hbar\omega_{\mathbf{q}\nu}(V)/k_{\mathrm{B}}T\bigr)\Bigr].
$$

The equilibrium volume at temperature $T$ minimises the Gibbs free energy
$G(V,T) = F(V,T) + PV$; at $P=0$ this reduces to
$V(T) = \arg\min_{V} F(V,T)$. The volumetric thermal expansion is

$$
\alpha_{V}(T) \;=\; \frac{1}{V(T)}\left(\frac{\partial V}{\partial T}\right)_{P}.
$$

In practice $F(V,T)$ is sampled on a discrete grid of isotropically strained
volumes $V_{i}=(1+\varepsilon_{i})^{3}V_{0}$ with the cell shape held fixed
during ionic relaxation (volume-conserving v-ZSISA[^1]). $U_{\mathrm{el}}(V)$
is fitted to an analytic equation of state — Birch–Murnaghan by default —
and the temperature-dependent observables (equilibrium volume, isothermal
bulk modulus, Grüneisen parameter, $C_{P}$, Gibbs energy) are extracted from
$F(V,T)$ by `phonopy.api_qha.PhonopyQHA`.

## Workflow

The driver `qhab` executes the following stages, each gated by a flag in the
configuration file:

1. **Unit-cell relaxation** — full relaxation of the input structure with
   space-group symmetry preserved (`ase.constraints.FixSymmetry`).
2. **Volume-fixed strain sweep** — for each $\varepsilon_{i}$, the cell is
   isotropically scaled and the internal coordinates are relaxed at fixed
   shape and volume.
3. **Supercell + displacements** — phonopy generates the supercells with
   finite displacements for each strained reference structure.
4. **Force evaluation** — the uMLIP computes forces on every displaced
   supercell; force sets are stored per strain.
5. **Force constants** — second-order force constants are produced from
   the displacement–force data set.
6. **Mesh sampling** — phonon frequencies on a regular $\mathbf{q}$-mesh,
   thermal properties $F_{\mathrm{ph}}, S, C_{V}$, total/projected DOS,
   and band structures are computed per strain.
7. **QHA fit** — energies $\{U_{\mathrm{el}}(V_{i})\}$ and per-volume thermal
   tables are passed to `PhonopyQHA`, which performs the EOS fit at every
   $T$ and returns $V(T)$, $B_{T}(T)$, $\alpha_{V}(T)$, $\gamma(T)$,
   $C_{P}(T)$ and the Gibbs free energy.

Stages communicate exclusively through files on disk, so any subset can be
re-run independently.

## Installation

```sh
git clone https://github.com/ywllnkang/qhaB
cd qhaB
pip install -e .
```

Runtime dependencies: `phonopy`, `pymatgen`, `seekpath`, `ase`, `spglib`,
`h5py`, `numpy`, `pyyaml`, `matplotlib`. A working uMLIP backend
(`sevenn`, `fairchem`, `nequip`, `upet`, …) must be installed separately
for the calculator that is requested in the configuration.

## Usage

```sh
qhab --config config.yaml --name <run-tag>
```

The driver runs in the current working directory; all per-stage output
directories (`unitcell/`, `strain/`, `supercell/`, `fc2/`, `mesh/`,
`qha-*/`) are created relative to it. A parsed configuration
(`parsed_config.yaml`), a run summary (`qhaB.info`), and a step-resolved
log (`qhaB.stdout`) are written alongside.

## Configuration

The YAML configuration is merged on top of the defaults in
`qhab/config.py`. The major sections are

| Section      | Purpose                                                       |
|--------------|---------------------------------------------------------------|
| `io`         | Input structure, on-disk formats                              |
| `calculator` | uMLIP backend selector (`calc`, `model`, `modal`, `d3`, …)    |
| `unitcell`   | Reference relaxation                                          |
| `strain`     | Set of volumetric strains $\{\varepsilon_{i}\}$               |
| `supercell`  | Supercell matrix, primitive matrix, displacement distance     |
| `fc2`        | Force-constants stage                                         |
| `mesh`       | $\mathbf{q}$-mesh, thermal range, DOS/band toggles            |
| `qha`        | Subset of strains used in the EOS fit, EOS choice, $T_{\max}$ |
| `relax`      | Per-stage ASE optimiser/filter/symmetry settings              |

Each stage carries an independent `run` flag, allowing partial pipelines.

## Outputs

Per strain $\varepsilon_{i}$:

- `strain/<name>-strained_relaxed.extxyz` — relaxed strained structures
  with energies and forces in `info`.
- `supercell/<name>-{eps}-supercell-*.extxyz` — displaced supercells.
- `supercell/<name>-{eps}-force_set.npy` — `(n_disp, n_atom, 3)` forces.
- `supercell/<name>-{eps}-phonopy.yaml.xz` — phonopy state.
- `fc2/<name>-{eps}-force_constants.hdf5` — second-order force constants.
- `mesh/<name>-{eps}-{mesh,thermal_properties,tdos,band_dos}.{hdf5,yaml,dat,png}`.

After the QHA stage, the `qha/` directory contains the $V(T)$, $B_{T}(T)$,
$\alpha_{V}(T)$, $\gamma(T)$, $C_{P}(T)$, Gibbs-energy tables and the
corresponding plots produced by `PhonopyQHA`.

## References

[^1]: Y. M. Oba *et al.*, *Phys. Rev. Mater.* **3**, 033601 (2019);
A. Togo and I. Tanaka, *Scr. Mater.* **108**, 1 (2015) — phonopy.
