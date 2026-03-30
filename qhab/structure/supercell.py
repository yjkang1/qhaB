import os,glob

import numpy as np

import ase.io as ase_IO

from qhab.calculator.tools import single_point_calculate_list, single_point_calculate # lets do this atomically
from qhab.logger import logger

def calculate_force(supercells_with_displacements, calc):
    supercell_atoms_list = []
    force_set = []
    for j, supercell in enumerate(supercells_with_displacements):
        logger.info(f'processing ')
        atoms = ase_IO.read(supercell)
        atoms = single_point_calculate(atoms, calc)
        force_set.append(atoms.get_force())
    return np.array(force_set)

def run_force_calculation(config, calc):
    name = config['io']['name']
    cwd = os.path.join(config["io"]["abswd"], config["supercell"]["save"])

    for i, eps in enumerate(config['strain']['eps']):
        logger.info(f'Processing one-shot force calculation of supercell for {name} with volumetric strain {eps}')
        supercells_with_displacements = glob.glob(f'{cwd}/{name}-{eps}-*')
        force_set = calculate_force(supercells_with_displacements, calc)
        np.save(file=f'{cwd}/{name}-{eps}-force_set', arr=force_set)
