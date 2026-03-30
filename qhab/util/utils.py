import numpy as np
import warnings
import yaml

import h5py
from ase import Atoms

import spglib
from phonopy.structure.atoms import PhonopyAtoms

def get_spgnum(atoms, symprec=1e-5):
    cell = (atoms.get_cell(), atoms.get_scaled_positions(), atoms.get_atomic_numbers())
    spgdat = spglib.get_symmetry_dataset(cell, symprec=symprec)
    return spgdat.number

def get_spg(atoms, symprec=1e-5):
    cell = (atoms.get_cell(), atoms.get_scaled_positions(), atoms.get_atomic_numbers())
    spg = spglib.get_spacegroup(cell, symprec=symprec)
    return spg

def apply_isometric_strain(atoms, strain):
    scaled = atoms.copy()
    scaled.set_cell(scaled.get_cell() * (1+strain), scale_atoms=True)
    return scaled

def phonoatoms2aseatoms(phonoatoms):
    atoms = Atoms(
        phonoatoms.symbols,
        cell=phonoatoms.cell,
        positions=phonoatoms.positions,
        pbc=True
    )
    return atoms

def aseatoms2phonoatoms(atoms):
    phonoatoms = PhonopyAtoms(
        atoms.symbols,
        cell=atoms.cell,
        positions=atoms.positions,
    )
    return phonoatoms

def check_imaginary_freqs(frequencies: np.ndarray) -> bool:
    try:
        if np.all(np.isnan(frequencies)):
            return True

        if np.any(frequencies[0, 3:] < 0):
            return True

        if np.any(frequencies[0, :3] < -1e-2):
            return True

        if np.any(frequencies[1:] < 0):
            return True
    except Exception as e:
        warnings.warn(f"Failed to check imaginary frequencies: {e}")

    return False

def load_mesh_yaml(mesh_yaml_path):
    with open(mesh_yaml_path, 'r') as f:
        data = yaml.safe_load(f)

    qblocks = data.get('phonon') or data.get('mesh') or data.get('mesh_points') or data['mesh']
    # try to be robust if key names differ:
    if not isinstance(qblocks, list):
        # some phonopy dumps nest differently
        qblocks = data['phonon'].get('qpoints', data['mesh'].get('qpoints'))

    weights = []
    freqs_list = []
    for qp in qblocks:
        w = qp.get('weight')
        w = int(w)
        bands = qp.get('band') or qp.get('bands')
        freqs = [float(b.get('frequency')) for b in bands]
        weights.append(w)
        freqs_list.append(freqs)

    weights = np.array(weights, dtype=float)         # shape (n_q,)
    freqs = np.array(freqs_list, dtype=float)       # shape (n_q, n_bands)
    return weights, freqs

def load_mesh_hdf5(mesh_hdf5_path):
    """
    Load q-point weights and frequencies from phonopy mesh.hdf5.

    Returns
    -------
    weights : np.ndarray, shape (n_q,)
    freqs   : np.ndarray, shape (n_q, n_bands)
    """
    with h5py.File(mesh_hdf5_path, "r") as f:
        if "frequency" not in f:
            raise ValueError("mesh.hdf5 missing 'frequency' dataset")

        freqs = f["frequency"][()]  # (n_q, n_bands)

        if "weight" in f:
            weights = f["weight"][()]  # (n_q,)
        else:
            # fallback: uniform weights
            weights = np.ones(freqs.shape[0], dtype=float)

    freqs = np.asarray(freqs, dtype=float)
    weights = np.asarray(weights, dtype=float)
    return weights, freqs


def load_band_yaml(filename: str) -> np.ndarray:
    with open(filename, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    phonon = data.get("phonon")
    if phonon is None:
        raise ValueError("Could not find 'phonon' section in band.yaml")

    freqs = []
    for qpoint in phonon:
        bands = qpoint.get("band", [])
        for band in bands:
            freq = band.get("frequency")
            if freq is None:
                raise ValueError("A band entry is missing the 'frequency' field")
            freqs.append(float(freq))

    if not freqs:
        raise ValueError("No frequencies found in band.yaml")
    return np.array(freqs, dtype=float)


"""
def read_tods():
    pass
def gaussian_dos(
    freqs: np.ndarray,
    sigma: float = 0.05,
    npts: int = 4000,
    padding: float = 5.0,
) -> tuple[np.ndarray, np.ndarray]:
    fmin = freqs.min() - padding * sigma
    fmax = freqs.max() + padding * sigma
    grid = np.linspace(fmin, fmax, npts)

    x = grid[:, None] - freqs[None, :]
    dos = np.exp(-0.5 * (x / sigma) ** 2) / (sigma * np.sqrt(2.0 * np.pi))
    dos = dos.sum(axis=1)

    return grid, dos


def imaginary_fraction_from_dos(grid: np.ndarray, dos: np.ndarray) -> float:
    total = np.trapezoid(dos, grid)
    if total <= 0:
        raise ValueError("Total DOS integral is non-positive")

    mask_imag = grid < 0.0
    if not np.any(mask_imag):
        return 0.0

    imag = np.trapezoid(dos[mask_imag], grid[mask_imag])
    return imag / total


def direct_imaginary_fraction(freqs: np.ndarray) -> float:
    return np.count_nonzero(freqs < 0.0) / freqs.size

"""
