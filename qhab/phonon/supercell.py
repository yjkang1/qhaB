import numpy as np
import os

from phonopy import Phonopy
from phonopy import file_IO as ph_IO
# from phonopy.interface.vasp import write_supercells_with_displacements #TODO ??
import ase.io as ase_IO

from qhab.logger import logger
from qhab.util.utils import aseatoms2phonoatoms, phonoatoms2aseatoms


def run_supercell_generation(config):
    name = config['io']['name']
    cwd = os.path.join(config["io"]["abswd"], config["supercell"]["save"])
    prev_wd = os.path.join(config["io"]["abswd"], config["strain"]["save"])

    strained_output = ase_IO.read(f'{prev_wd}/{name}-strained_relaxed.extxyz')

    for i, eps in enumerate(config['strain']['eps']):
        logger.info(f'Generating phonopy object & supercells with displacements for volumetric strain {eps}')
        atoms = strained_output[i]
        phatoms = phonoatoms2aseatoms(atoms)
        ph = Phonopy(unitcell=phatoms,
                     supercell_matrix=np.diag(config['supercell']['matrix']),
                     primitive_matrix='auto',
                     )
        ph.generate_displacements(random_seed=config['supercell']['random_seed'])

        for i, sc in enumerate(ph.supercells_with_displacements):
            sc_atoms = phonoatoms2aseatoms(sc)
            ase_IO.write(f'{cwd}/{name}-{eps}-supercell-{i}.extxyz', sc_atoms, format='extxyz')

        logger.info(f'Saved phonopy object with unitcell + supercell information for volumetric strain {eps}')
        ph.save(f'{cwd}/{name}-{eps}-phonopy.yaml', compression=True) 
