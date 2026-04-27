# Examples

Reference QHA runs of `qhaB` on representative crystalline solids. Each
sub-directory ships the inputs needed to reproduce the run end-to-end and
a `reference/` tree containing the outputs that the developer obtained,
so that a user can compare numerical results against a known set.

| System    | Space group | $N_{\mathrm{atom}}$ | uMLIP backend | Notes                |
|-----------|-------------|---------------------|---------------|----------------------|
| `MgO_225` | Fm-3m (225) | 8 (conventional)    | `7net-zero`   | rock-salt, isotropic |

Large intermediate artefacts — displaced supercells, force constants,
$\mathbf{q}$-mesh dumps — are *not* shipped: they are bit-for-bit
regenerated from the inputs, and shipping them would inflate the repo
by hundreds of megabytes per system. The QHA-stage tables and plots,
which are the primary observables, are kept verbatim.

## Layout (per system)

```
examples/<system>/
├── README.md                 # system-specific notes
├── config.yaml               # driver configuration (paths relativised)
├── <system>.extxyz           # input structure
└── reference/                # frozen developer-run outputs
    ├── parsed_config.yaml    # config after merge with package defaults
    ├── qhaB.info             # SLURM/structure summary written at run-start
    ├── qhaB.stdout           # step-resolved log
    ├── unitcell/             # Stage 1 — fully relaxed unit cell
    ├── strain/               # Stage 2 — volume-fixed strained cells
    └── qha/                  # Stage 7 — PhonopyQHA tables + plots
```

## Reproducing a run

From the example directory:

```sh
cd examples/MgO_225
qhab --config config.yaml --name MgO_225
```

The driver writes its outputs into the current directory, so the run
materialises a `unitcell/`, `strain/`, `supercell/`, `fc2/`, `mesh/`,
and `qha/` tree alongside `reference/`. Compare the freshly produced
`qha/*.dat` to `reference/qha/*.dat` to validate.

## Notes

- The structure files in this directory are stored in extended-XYZ; the
  Mg–O bond lengths and lattice constants are uMLIP-relaxed from the
  Materials Project entry recorded in the file header (`material_id=...`).
- `reference/qha/` omits `helmhotz_volume_full.{dat,png}`, which are a
  $T$-step-1 dump of the fitted Helmholtz surface (≈2.5 MB) and are
  redundant with `helmholtz-volume_fitted.dat`.
