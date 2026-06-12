from phonopy import Phonopy
import ase.io as ase_IO

from qhab.util.utils import aseatoms2phonoatoms, phonoatoms2aseatoms

config = {
        'ref_dir': 'DFT',
        'base_dir': 'DFT',
        'strain': [-0.05, -0.04, -0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08],
        'phonon_kwargs': {'supercell_matrix': [4,4,4], 'primitive_matrix': 'auto'}
        'supercell_kwargs': {'random_seed': 42},
        'models': ['omni', 'nano-4.5', 'nano-5.0', 'nano-5.5', 'nano-6.0'],
        }

def generate_supercells(config):
    pass
    # atoms = ase_IO.read(config['contcar_dir'])
    # unitcell = aseatoms2phonoatoms(atoms)
    # for model in models:
    #     test_dir = 

