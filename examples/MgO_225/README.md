# MgO (Fm-3m, No. 225) with SevenNet-0

A complete qhaB run on rock-salt MgO using SevenNet-0, a public universal potential that
ships with SevenNet (`pip install sevenn`). It goes through all seven stages, from relaxing
the input cell to the QHA fit, and comes with the outputs of a reference run for comparison.

## Files

| File | Content |
|---|---|
| `MgO_225.extxyz` | Input structure: conventional 8-atom cell, a = 4.2557 Å. The header records the phononDB metadata (`material_id=mp-1265`, supercell and primitive matrices). |
| `config.yaml` | Full pipeline (stages 1–7). |
| `config.qha-subset.yaml` | Stage 7 only: refits the QHA without the two largest strains, reusing the phonons of the `config.yaml` run. |
| `reference/` | Outputs of the reference run (see [Reference Run](#reference-run)). |

## Run Parameters

| Item | Value |
|---|---|
| Calculator | SevenNet-0 (`calc: 7net`, `model: zero`) |
| Supercell | 4 × 4 × 4 conventional cells (512 atoms) |
| Primitive matrix | fcc, `[[0, 0.5, 0.5], [0.5, 0, 0.5], [0.5, 0.5, 0]]`; QHA volumes and energies are per primitive cell |
| Displacements | phonopy default amplitude, 0.01 Å |
| Strain grid | ε = −0.04, −0.02, 0, +0.02, +0.04, +0.06, +0.08 |
| Volume grid | V/V0 = (1 + ε)³ = 0.885, 0.941, 1, 1.061, 1.125, 1.191, 1.260 |
| q-mesh | 48 × 48 × 48 |
| Temperatures | 0 to 1200 K in 1 K steps |
| EOS | third-order Birch–Murnaghan |
| Relaxation | FIRE2 with `FrechetCellFilter`, fmax = 1e-5 eV/Å, space group fixed |

## Running the Example

```sh
cd examples/MgO_225
qhab --config config.yaml --name MgO_225
```

The run writes `unitcell/`, `strain/`, `supercell/`, `fc2/`, `mesh/` and `qha/` into this
directory, next to `reference/`. Compare `qha/*.dat` with `reference/qha/*.dat`; small
differences can come from the SevenNet version and from the hardware.

The QHA can then be refitted on a narrower strain window without recomputing any phonons:

```sh
qhab --config config.qha-subset.yaml --name MgO_225
```

This writes `qha-subset/`. Each call to `qhab` overwrites `parsed_config.yaml` and `qhaB.info`
in the run directory and appends to `qhaB.stdout`.

## Reference Run

The files in `reference/` were produced on 2026-03-31 with SevenNet-0 and the qhaB code of
that date. The run took 3 min 22 s from start to finish (`reference/qhaB.stdout`); the
hardware was not recorded. The stages that produce these numbers have not changed since,
apart from bookkeeping: the current code also tags each strained structure with its strain
(`info['eps']`) and reads the QHA strain set from `qha.eps`, which `config.yaml` sets to the
full grid.

Selected values at 300 K (volume per two-atom primitive cell):

| Quantity | File | Value |
|---|---|---|
| α_V | `thermal_expansion.dat` | 4.35 × 10⁻⁵ K⁻¹ |
| V | `volume-temperature.dat` | 19.534 Å³ |
| B_T | `bulk_modulus-temperature.dat` | 145.98 GPa |
| γ | `gruneisen-temperature.dat` | 1.914 |

The reference is a regression target for the pipeline, not a converged result for MgO. Its
strain grid extends to V/V0 = 1.26, beyond the volume at which SevenNet-0 MgO develops
imaginary modes:

- At ε = +0.08, the heat capacity at 1200 K is 39.2 J K⁻¹ mol⁻¹ (`Cv-volume.dat`), against
  the harmonic limit 6R = 49.9 J K⁻¹ mol⁻¹ of a two-atom cell. About a fifth of the phonon
  modes are imaginary at this volume, and phonopy leaves imaginary modes out of the
  thermal properties.
- At ε = +0.06, the heat capacity and entropy at 50 K are three to four times their values at
  ε = +0.04, as expected for modes that have softened towards zero frequency.
- The fit over the full grid gives α_V < 0 between 1 and 81 K, and a bulk modulus B_T(T) that
  passes through a minimum of 136.6 GPa at 750 K and rises to 149.4 GPa at 1200 K.

Imaginary modes that appear under expansion are also what limits uMLIP thermal expansion in
the benchmark study (see the main [README](../../README.md#benchmark-study)). Before trusting
a fit, inspect the phonon
dispersions at every strain (`mesh/MgO_225-<eps>-band_dos.png`) and restrict `qha.eps` to the
strains without imaginary modes, as `config.qha-subset.yaml` does.

## Redactions

Absolute paths in `reference/parsed_config.yaml` and `reference/qhaB.stdout` have been
replaced by `<run_dir>` and `<input_dir>`. The Slurm job ID, cluster name and node list in
`reference/qhaB.info` have been replaced by `<redacted>`. No other file was changed.
