# qhaB

Quasiharmonic thermal expansion of crystals from universal machine-learning interatomic potentials.

qhaB computes the temperature-dependent volumetric coefficient of thermal expansion (CTE),
α_V(T), of a crystal within the quasiharmonic approximation (QHA). A universal
machine-learning interatomic potential (uMLIP) supplies all energies and forces. One YAML
file and one command take an input structure through relaxation, strained cells,
finite-displacement phonons and the QHA fit to V(T), α_V(T), B_T(T) and γ(T). Relaxations
use [ASE](https://wiki.fysik.dtu.dk/ase/) [1]. Supercells, force constants, thermal
properties and the QHA fit use [phonopy](https://phonopy.github.io/phonopy/) [2, 3].

qhaB was written for the author's M.S. thesis [4]. The thesis benchmarks the distilled
SevenNet-Nano potential against its SevenNet-Omni teacher and against DFT on 103 compounds
from the phononDB dataset, with DFT references at the PBE and PBEsol levels (see
[Benchmark Study](#benchmark-study)).

## Method

Within the QHA, the Helmholtz free energy at volume V and temperature T is the static lattice
energy plus the harmonic free energy of the phonons at that volume [5]:

```
F(V, T)    = E0(V) + F_ph(V, T)

F_ph(V, T) = 1/2 Σ_qs ħω_qs(V)  +  k_B T Σ_qs ln[ 1 − exp(−ħω_qs(V) / k_B T) ]
```

Here ω_qs(V) is the frequency of branch s at wavevector q, obtained from harmonic force
constants computed at volume V. At zero pressure the equilibrium volume minimises F at each
temperature. The CTE and the isothermal bulk modulus follow as

```
V(T)    = argmin_V F(V, T)
α_V(T)  = (1/V) (∂V/∂T)_P
B_T(T)  = V (∂²F/∂V²)_T        evaluated at V = V(T)
```

qhaB samples F(V, T) on a grid of isotropically strained cells. A strain ε scales all three
lattice vectors of the relaxed unit cell by (1 + ε):

```
V(ε) = V0 (1 + ε)³
```

V0 is the relaxed volume, so a grid from ε = −0.04 to +0.06 spans V/V0 = 0.885 to 1.191. At
each strain the atomic positions and the cell shape are relaxed at fixed volume, with the
space group held fixed. This is the volume-constrained zero static internal stress
approximation (v-ZSISA) [6]. phonopy's `PhonopyQHA` then fits an equation of state (EOS) to
F(V, T) at each temperature. It returns V(T), α_V(T), B_T(T), the thermodynamic Grüneisen
parameter γ(T), the isobaric heat capacity C_P(T) and the Gibbs free energy G(T).

## Workflow

`qhab` runs seven stages in a fixed order. Each stage has its own switch in the
configuration file. Stages exchange data only through files, so any stage can be rerun on
its own once the files from the earlier stages exist.

| Stage | Switch | Operation | Main output |
|---|---|---|---|
| 1 | `unitcell.run` | Relax the atomic positions and the cell of the input structure, space group fixed | `unitcell/<name>-unitcell_relaxed.extxyz` |
| 2 | `strain.run` | For each ε in `strain.eps`, scale the cell, then relax positions and cell shape at fixed volume | `strain/<name>-strained_relaxed.extxyz` |
| 3 | `supercell.generate` | Build the displaced supercells of each strained cell with phonopy | `supercell/<name>-<ε>-supercell-<j>.extxyz` |
| 4 | `supercell.calc` | Compute uMLIP forces on every displaced supercell | `supercell/<name>-<ε>-force_set.npy` |
| 5 | `fc2.run` | Compute second-order force constants from the force sets | `fc2/<name>-<ε>-force_constants.hdf5` |
| 6 | `mesh.run` | Compute phonons on a q-mesh, then thermal properties, DOS and band structure | `mesh/<name>-<ε>-thermal_properties.yaml` |
| 7 | `qha.run` | Fit the EOS to F(V, T) over the strains in `qha.eps` | `<qha.save>/thermal_expansion.dat` |

`<name>` is the `--name` argument. `<ε>` is the strain as written in the configuration, for
example `0.02`.

## Installation

qhaB requires Python 3.11 or later.

```sh
git clone https://github.com/yjkang1/qhaB.git
cd qhaB
pip install -e .
```

This installs phonopy, pymatgen and seekpath. qhaB also needs ASE and a uMLIP package;
SevenNet installs ASE as one of its dependencies:

```sh
pip install sevenn
```

SevenNet 0.13.0, the current release on PyPI, provides SevenNet-0 and SevenNet-Omni. As of
November 2026, the SevenNet-Nano checkpoints are only in the development version:
`pip install git+https://github.com/MDIL-SNU/SevenNet.git`. The other backends are listed
under [Supported Calculators](#supported-calculators).

## Quick Start

```sh
cd examples/MgO_225
qhab --config config.yaml --name MgO_225
```

`qhab` works in the current directory. It reads the structure given by `io.input` and creates
one subdirectory per stage. Next to them it writes three files:

- `parsed_config.yaml`: the configuration after merging with the defaults.
- `qhaB.info`: a summary of the structure and of the Slurm job.
- `qhaB.stdout`: the log, with the wall time of each stage.

[examples/MgO_225](examples/MgO_225/README.md) describes the example, its reference outputs
and their caveats.

## Configuration

The YAML file is merged recursively onto the defaults in [`qhab/config.py`](qhab/config.py),
and any key left out takes its default value. The defaults are not a ready-to-run setup:
`io.input` defaults to `./aln.extxyz`, and the calculator to SevenNet-Nano with a 4.5 Å cutoff
from a local checkpoint. Write every section explicitly instead, as
[`examples/MgO_225/config.yaml`](examples/MgO_225/config.yaml) does.

| Key | Default | Meaning |
|---|---|---|
| `io.input` | `./aln.extxyz` | Input structure, read with `ase.io.read(input, **load_args)` |
| `io.load_args` | `{format: extxyz, index: 0}` | Keyword arguments of `ase.io.read` |
| `calculator.calc` | `7net` | Backend: `7net` (SevenNet), `pet` (UPET), `nequip` or `esen` |
| `calculator.model`, `calculator.modal` | `nano`, `4.5` | Model and channel, see [Supported Calculators](#supported-calculators) |
| `calculator.d3` | `false` | Add SevenNet's D3 dispersion correction (PBE parameters); SevenNet only |
| `strain.eps` | 13 values, −0.05 to +0.08 | Strain grid ε |
| `supercell.matrix` | `[4, 4, 4]` | Diagonal supercell matrix, in units of the input cell |
| `supercell.primitive` | identity | Primitive matrix passed to phonopy. QHA volumes and energies are per primitive cell |
| `mesh.mesh.numbers` | `[48, 48, 48]` | q-mesh for the thermal properties |
| `mesh.thermal.t_min`, `t_max`, `t_step` | `0`, `1201`, `1` | Temperature grid (K) of the thermal properties |
| `mesh.tdos.run`, `mesh.band.run` | `true`, `true` | Total DOS; band structure along the seekpath path, written only when `tdos.run` is true |
| `qha.eps` | 10 values, −0.05 to +0.05 | Strains used in the QHA fit: a subset of `strain.eps`, at least 5 of them |
| `qha.eos` | `birch_murnaghan` | EOS of the fit: `birch_murnaghan`, `vinet` or `murnaghan` |
| `qha.t_max` | `1201` | Maximum temperature (K) of the QHA |
| `qha.thin_number` | `50` | Temperature stride of the F(V) curves in the plots and in `helmholtz-volume_fitted.dat` |
| `relax.unitcell`, `relax.strain` | FIRE2, `frechet`, fmax = 1e-5 eV/Å | ASE settings: `optimizer` (`fire`, `fire2`, `lbfgs`), `cell_filter` (`frechet`, `unitcell`), `fmax`, `steps`, `fix_symm`, `mask`. `relax.strain.const_volume: true` keeps the volume fixed |
| `<stage>.run`, `<stage>.save` | `true`, `./<stage>` | Stage switch and output directory (`./qha-symm` for the QHA) |

Strains enter file names, so each value must be written the same way in `strain.eps` and in
`qha.eps`: `0.0` and `0` give different file names.

## Supported Calculators

Each backend is a short module in [`qhab/calculator/`](qhab/calculator/) that returns an ASE
calculator. `calculator.calc` selects the module.

| `calc` | Package | Model selection | Notes |
|---|---|---|---|
| `7net` | [SevenNet](https://github.com/MDIL-SNU/SevenNet) [7] | `model: zero` gives SevenNet-0. `model: omni` with `modal: mpa`, `omat24`, `matpes_pbe`, `pet_mad`, … gives that SevenNet-Omni channel [8]. `model: nano-6.0` gives SevenNet-Nano [9] with a 6.0 Å cutoff; `nano-4.5`, `nano-5.0` and `nano-5.5` work the same way. Any other `model: X` loads the pretrained model `7net-X` | CPU or GPU. FlashTP acceleration is requested; SevenNet falls back to e3nn when FlashTP is not installed |
| `pet` | [UPET](https://github.com/lab-cosmo/upet) | The model name is `pet-<model>-<modal>`, e.g. `model: oam`, `modal: xl` gives `pet-oam-xl` | GPU |
| `nequip` | [NequIP](https://github.com/mir-group/nequip) | `modal: l` or `xl` selects a compiled NequIP-OAM-L or -XL model | GPU. Model paths are set in `nequip_calculator.py` |
| `esen` | fairchem-core | `modal: oam` or `omat` selects an eSEN-30M checkpoint | GPU. Checkpoint directory set in `esen_calculator.py`; uses `fairchem.core.OCPCalculator` |

The benchmark study used the SevenNet-Omni channels `mpa`, `omat24` and `matpes_pbe` (PBE) and
`pet_mad` (PBEsol). Local SevenNet checkpoints can be registered in `CALC_DCT` in
`qhab/calculator/sevenn_calculator.py`. With `model: nano`, `modal: <rc>` reads
`<CALC_DCT['nano']>/nano_cut<rc>/checkpoint_2.pth`.

## Output Files

All paths are relative to the run directory.

| Path | Content |
|---|---|
| `parsed_config.yaml`, `qhaB.info`, `qhaB.stdout` | Merged configuration, run summary, log |
| `unitcell/<name>-unitcell_relaxed.extxyz` | Relaxed unit cell; the optimizer trace is in `unitcell_relaxation.log` |
| `strain/<name>-strained_relaxed.extxyz` | All strained cells. `info` holds `eps`, `steps` and `e_fr_energy`, the energy used as E0(V) |
| `supercell/<name>-<ε>-phonopy.yaml.xz` | phonopy object: unit cell, supercell, displacements |
| `supercell/<name>-<ε>-supercell-<j>.extxyz`, `<name>-<ε>-force_set.npy` | Displaced supercells and their forces |
| `fc2/<name>-<ε>-force_constants.hdf5` | Force constants, also written as `FORCE_CONSTANTS` |
| `mesh/<name>-<ε>-thermal_properties.{yaml,png}` | F_ph, S and C_V versus T |
| `mesh/<name>-<ε>-mesh.{hdf5,yaml}` | Frequencies on the q-mesh |
| `mesh/<name>-<ε>-tdos.dat`, `<name>-<ε>-band_dos.png` | Total DOS; band structure with DOS |
| `mesh/<name>-<ε>-tdos.yaml` | Band structure in phonopy `band.yaml` format (despite the name) |
| `<qha.save>/thermal_expansion.dat` | α_V(T) in K⁻¹ |
| `<qha.save>/volume-temperature.dat`, `bulk_modulus-temperature.dat`, `gruneisen-temperature.dat`, `gibbs-temperature.dat` | V(T) in Å³, B_T(T) in GPa, γ(T), G(T) |
| `<qha.save>/Cp-temperature.dat`, `Cp-temperature_polyfit.dat` | C_P(T), numerical and polynomial-fit versions |
| `<qha.save>/helmholtz-volume.dat`, `helmholtz-volume_fitted.dat` | F(V, T) on the strain grid, and the fitted EOS |
| `<qha.save>/entropy-volume.dat`, `Cv-volume.dat`, `dsdv-temperature.dat` | S and C_V on the strain grid, and dS/dV |
| `<qha.save>/*.png`, `qha_plot.pdf`, `eos_<eos>.png` | Plots of the above |

## Benchmark Study

qhaB produced the uMLIP calculations of the benchmark in the author's M.S. thesis [4]. The
thesis asks whether a distilled universal potential keeps the accuracy that thermal
expansion requires. It follows a DFT ← SevenNet-Omni ← SevenNet-Nano chain: first the
teacher, SevenNet-Omni [8], is validated against DFT; then the distilled student,
SevenNet-Nano [9], is compared with the teacher.

### Protocol

Settings from the thesis, Supporting Information A:

| Item | Setting |
|---|---|
| Compounds | 103 from phononDB [3], mostly rock-salt (Fm-3m) and zincblende (F-43m) binaries, plus fewer wurtzite (P6₃mc) |
| DFT reference | VASP with PAW datasets, PBE and PBEsol; 520 eV cutoff; Γ-centred k-meshes with 0.10 Å⁻¹ spacing; non-spherical gradient corrections in the PAW spheres (LASPH); forces below 10⁻⁴ eV/Å |
| Teacher | SevenNet-Omni channels mpa, omat24 and matpes_pbe (against PBE), and pet_mad (against PBEsol) |
| Student | SevenNet-Nano, distilled from the Omni mpa channel, with cutoffs r_c = 4.5, 5.0, 5.5 and 6.0 Å |
| Fine-tuning | None (zero-shot) |
| Phonons | Finite displacements of 0.01 Å in supercells (phonopy) |
| Strain grid | ε = −0.04, −0.02, 0, +0.02, +0.04, +0.05, +0.06 |
| EOS | Third-order Birch–Murnaghan (BM3), Vinet, and the Rostami–Gonze polynomial [6] |

Under qhaB's strain convention, this grid spans V/V0 = 0.885 to 1.191.

### Results

Values from the thesis, Chapter 3. Structural and elastic agreement, R² about y = x:

| Comparison | V0/N | ΔE/N at ε = 0.06 | B0 (BM3) |
|---|---|---|---|
| Omni vs DFT (four channels) | > 0.999 | 0.982–0.986 | 0.989–0.996 |
| Nano, r_c = 4.5 Å, vs Omni-mpa | 0.991 | 0.890 | 0.92 |
| Nano, r_c = 5.0 Å, vs Omni-mpa | 0.997 | 0.900 | – |
| Nano, r_c = 5.5 Å, vs Omni-mpa | 0.997 | 0.906 | – |
| Nano, r_c = 6.0 Å, vs Omni-mpa | 0.998 | 0.895 | 0.97 |

Volumetric CTE of Nano against Omni-mpa on the dynamically stable subset, which holds 82–95 of
the 103 compounds depending on temperature. Mean absolute error in 10⁻⁶ K⁻¹:

| T (K) | r_c = 4.5 Å | 5.0 Å | 5.5 Å | 6.0 Å |
|---|---|---|---|---|
| 100 | 11.9 | 12.1 | 10.6 | 12.3 |
| 300 | 24.6 | 22.2 | 17.4 | 16.8 |
| 500 | 34.5 | 27.4 | 24.6 | 22.8 |
| 800 | 60.9 | 47.8 | 48.2 | 50.5 |

- **Structure and stiffness.** Distillation costs little here. For r_c ≥ 5.0 Å the student
  reproduces the teacher's equilibrium volume to R² ≥ 0.997, and at 6.0 Å its bulk modulus to
  R² = 0.97. The strain energy at the largest strain degrades first, with R² ≈ 0.9 at every
  cutoff.
- **CTE over all 103 compounds.** The student–teacher parity has a negative R² at 300 and
  800 K for every cutoff. A few compounds return unphysical CTEs from the teacher itself:
  Omni-mpa gives α_V ≈ 4.3 × 10⁻³ K⁻¹ for LiCl at 300 K and ≈ 2 × 10⁻² K⁻¹ for RbI at 800 K.
  A compound is excluded at a given temperature when either the teacher or the student
  returns such a divergent α_V. The remaining compounds form the stable subset used above.
- **Excluded compounds.** These are 14 alkali halides (LiF, LiCl, LiBr, LiI, NaCl, NaBr, NaI,
  KCl, KBr, KI, RbCl, RbBr, RbI, CsF), the alkali hydrides LiH, NaH, KH and RbH, and CuH.
  Twelve are excluded at each temperature and nineteen at one or more temperatures between
  100 and 800 K. Teacher and student fail on the same compounds.
- **Interpretation.** The thesis attributes these failures to the breakdown of the QHA:
  under expansion, soft branches reach ω² < 0, the harmonic free energy becomes undefined,
  and the free-energy minimum leaves the sampled volume window. It concludes that the binding
  constraint on uMLIP thermal expansion is the validity of the QHA, not the fidelity of the
  distilled potential.
- **Thermal stress.** A CTE error propagates into a thermal-stress error
  δσ_th ≈ B δα_V ΔT. With δα_V = 17 × 10⁻⁶ K⁻¹ and ΔT = 100 K, this gives 60 MPa for CdTe
  (B0 = 35 GPa) and 634 MPa for BN (B0 = 373 GPa).

In the thesis, the CTE is compared between student and teacher, and DFT enters through V0,
ΔE and B0. The DFT calculations, the Rostami–Gonze EOS fits and the parity statistics were
produced outside this package.

## Known Limitations

- Imaginary modes are not screened. phonopy leaves imaginary modes out of the thermal
  properties, and every strain in `qha.eps` enters the fit. Inspect `mesh/*-band_dos.png` and
  restrict `qha.eps` accordingly; the [MgO example](examples/MgO_225/README.md#reference-run)
  shows what happens otherwise.
- Only diagonal supercell matrices are supported: `supercell.matrix` is passed through
  `numpy.diag`.
- `supercell.distance` is not passed to phonopy, so displacements always use phonopy's
  default amplitude of 0.01 Å.
- `supercell.generate` takes effect only when a calculator stage is also enabled
  (`unitcell.run`, `strain.run` or `supercell.calc`).
- With fewer than 5 strains in `qha.eps`, the QHA stage logs a warning and writes no output.
- Several keys are accepted but do not affect the calculation: `io.wd`, `io.format`,
  `calculator.batch`, `calculator.calc_args`, `mesh.pdos`, `qha.symm` and the per-stage
  `restart` flags.

## Related Publications and Presentations

1. Y. Kang, *Application of Universal Machine Learning Interatomic Potentials to Thermal
   Properties of Crystalline Materials*, M.S. thesis, Seoul National University (2026).
2. Y. Kang and S. Han, "Soft Phonons and Negative Thermal Expansion with Universal Machine
   Learning Interatomic Potentials", oral presentation, 2026 KPS Spring Meeting, Korean
   Physical Society (2026).
3. Y. Kang and S. Han, "Systematic Assessment of Thermal Expansion Using Universal
   Machine-Learning Interatomic Potentials", poster, 2026 Winter Symposium on Computational
   Materials Science, The Korean Institute of Metals and Materials (2026).
4. Y. Kang and S. Han, "Robust and Transferable Thermal Expansion Calculation with Universal
   Machine Learning Interatomic Potentials", poster, 26th Asian Workshop on First-Principles
   Electronic Structure Calculations (ASIAN-26) (2025).

## Citation

If you use qhaB, please cite the thesis [4], phonopy [2, 3], ASE [1], and the potential you
use (for SevenNet, [7–9]).

```bibtex
@mastersthesis{kang2026qhab,
  author = {Kang, Yujin},
  title  = {Application of Universal Machine Learning Interatomic Potentials to Thermal Properties of Crystalline Materials},
  school = {Seoul National University},
  year   = {2026},
  month  = aug,
}
```

## Acknowledgements

qhaB was developed in the Materials Data and Informatics Laboratory, Department of Materials
Science and Engineering, Seoul National University, under the supervision of Prof. Seungwu
Han. Parts of the calculator and relaxation modules are adapted from code by colleagues in the
group.

## License

qhaB is released under the [MIT License](LICENSE).

## References

1. A. Hjorth Larsen *et al.*, "The atomic simulation environment—a Python library for working
   with atoms", J. Phys.: Condens. Matter **29**, 273002 (2017).
   [doi:10.1088/1361-648X/aa680e](https://doi.org/10.1088/1361-648X/aa680e)
2. A. Togo, L. Chaput, T. Tadano, and I. Tanaka, "Implementation strategies in phonopy and
   phono3py", J. Phys.: Condens. Matter **35**, 353001 (2023).
   [doi:10.1088/1361-648X/acd831](https://doi.org/10.1088/1361-648X/acd831)
3. A. Togo, "First-principles phonon calculations with phonopy and phono3py", J. Phys. Soc.
   Jpn. **92**, 012001 (2023). [doi:10.7566/JPSJ.92.012001](https://doi.org/10.7566/JPSJ.92.012001)
4. Y. Kang, *Application of Universal Machine Learning Interatomic Potentials to Thermal
   Properties of Crystalline Materials*, M.S. thesis, Seoul National University (2026).
5. E. T. Ritz, S. J. Li, and N. A. Benedek, "Thermal expansion in insulating solids from first
   principles", J. Appl. Phys. **126**, 171102 (2019).
   [doi:10.1063/1.5125779](https://doi.org/10.1063/1.5125779)
6. S. Rostami and X. Gonze, "Approximations in first-principles volumetric thermal expansion
   determination", Phys. Rev. B **110**, 014103 (2024).
   [doi:10.1103/PhysRevB.110.014103](https://doi.org/10.1103/PhysRevB.110.014103)
7. Y. Park, J. Kim, S. Hwang, and S. Han, "Scalable parallel algorithm for graph neural network
   interatomic potentials in molecular dynamics simulations", J. Chem. Theory Comput. **20**,
   4857 (2024). [doi:10.1021/acs.jctc.4c00190](https://doi.org/10.1021/acs.jctc.4c00190)
8. J. Kim *et al.*, "Optimizing cross-domain transfer for universal machine learning
   interatomic potentials", Nat. Commun. **17**, 3432 (2026).
   [doi:10.1038/s41467-026-70195-8](https://doi.org/10.1038/s41467-026-70195-8)
9. S. Oh *et al.*, "A lightweight universal machine-learning interatomic potential via
   knowledge distillation for scalable atomistic simulations", J. Chem. Inf. Model. **66**,
   8875 (2026). [doi:10.1021/acs.jcim.6c01103](https://doi.org/10.1021/acs.jcim.6c01103)
