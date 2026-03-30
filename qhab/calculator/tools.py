import numpy as np
from tqdm import tqdm

from ase.calculators.singlepoint import SinglePointCalculator

CALC_DCT = {
        'sevenn': 'sevenn',
        '7': 'sevenn',
        'esen': 'esen',
        'pet': 'pet',
        'upet': 'pet',
        'nequip': 'nequip',
        'mace': 'mace',
        }

def load_calc(config): # TODO
    import importlib.util
    from pathlib import Path
    script = f'{CALC_DCT.get(config["calculator"]["calc"], "sevenn")}_calculator.py'
    file_path = Path(script).resolve()
    spec = importlib.util.spec_from_file_location('return_calc', file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    calc = module.return_calc(config)
    return calc

def single_point_calculate(atoms, calc):
    atoms.calc = calc
    energy = atoms.get_potential_energy()
    forces = atoms.get_forces()
    stress = atoms.get_stress()
    calc_results = {"energy": energy, "forces": forces, "stress": stress}
    calculator = SinglePointCalculator(atoms, **calc_results)
    new_atoms = calculator.get_atoms()
    return new_atoms


def single_point_calculate_list(atoms_list, calc, desc=None):
    calculated = []
    for atoms in tqdm(atoms_list, desc=desc, leave=False):
        calculated.append(single_point_calculate(atoms, calc))
    return calculated
