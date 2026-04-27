# MgO (Fm-3m, #225) — rock-salt MgO

Reference run of the full `qhaB` pipeline on conventional-cell MgO using
the SevenNet-zero universal MLIP. Lattice constant and geometry are taken
from Materials Project (`mp-1265`); the input header records the
$4{\times}4{\times}4$ supercell and primitive matrix used for the phonon
calculation.

## Run parameters

| Item                                | Value                                              |
|-------------------------------------|----------------------------------------------------|
| Calculator                          | `7net`, model `zero`                               |
| Conventional cell                   | 8 atoms (4 Mg + 4 O), $a = 4.2557$ Å               |
| Primitive matrix                    | $\frac{1}{2}[[0,1,1],[1,0,1],[1,1,0]]$ (fcc)       |
| Supercell matrix                    | $\mathrm{diag}(4,4,4)$                             |
| Displacement distance               | $0.01$ Å                                           |
| Strain set $\{\varepsilon_i\}$      | $\{-0.04, -0.02, 0, 0.02, 0.04, 0.06, 0.08\}$      |
| QHA strain subset                   | identical to strain set                            |
| EOS                                 | Birch–Murnaghan                                    |
| $\mathbf{q}$-mesh                   | $48{\times}48{\times}48$                           |
| Temperature range                   | $0 \le T \le 1200$ K, $\Delta T = 1$ K             |
| ASE optimiser / cell filter         | FIRE2 / Frechet                                    |
| Force convergence                   | $f_{\max} = 10^{-5}$ eV/Å                          |
| Symmetry                            | preserved (`FixSymmetry`)                          |

## Reproducing

```sh
cd examples/MgO_225
qhab --config config.yaml --name MgO_225
```

Wall time on a single A100 with `7net-zero` is on the order of one minute
for the unit-cell and strain stages combined, plus phonon / QHA stages.

## Reference outputs

`reference/qha/` contains the $T$-resolved QHA observables:

| File                            | Content                                              |
|---------------------------------|------------------------------------------------------|
| `volume-temperature.dat`        | $V(T)$                                               |
| `thermal_expansion.dat`         | $\alpha_V(T)$                                        |
| `bulk_modulus-temperature.dat`  | $B_T(T)$                                             |
| `gibbs-temperature.dat`         | $G(T)$                                               |
| `Cp-temperature.dat`            | $C_P(T)$ (numerical)                                 |
| `Cp-temperature_polyfit.dat`    | $C_P(T)$ (polynomial fit)                            |
| `gruneisen-temperature.dat`     | $\gamma(T)$                                          |
| `helmholtz-volume.dat`          | $F(V_i, T)$ on the strain grid                       |
| `helmholtz-volume_fitted.dat`   | EOS-fitted $F(V, T)$ at $T$-resolution `thin_number` |
| `dsdv-temperature.dat`          | $(\partial S / \partial V)_T$                        |
| `entropy-volume.dat`            | $S(V_i, T)$ on the strain grid                       |
| `Cv-volume.dat`                 | $C_V(V_i, T)$ on the strain grid                     |
| `eos_birch_murnaghan.png`       | Static EOS fit                                       |
| `*_temperature.png`             | Plots of the corresponding `*_temperature.dat`       |

Stage-1/2 outputs:

- `reference/unitcell/MgO_225-unitcell_relaxed.extxyz` — converged
  conventional cell with $E$, $F$, $\sigma$ in `info`.
- `reference/strain/MgO_225-strained_relaxed.extxyz` — stack of seven
  volume-fixed relaxed structures, indexed by `info['eps']`. The
  `info['e_fr_energy']` field carries $U_{\mathrm{el}}(V_i)$ used by
  the QHA stage.
