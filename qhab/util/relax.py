from ase.constraints import FixSymmetry
from ase.filters import UnitCellFilter, FrechetCellFilter
from ase.optimize import LBFGS, FIRE, FIRE2
import numpy as np
# import torch

OPT_DCT = {'fire': FIRE, 'fire2':FIRE2,'lbfgs': LBFGS}
FILTER_DCT = {'frechet': FrechetCellFilter, 'unitcell': UnitCellFilter}

"""
modified based on Jaesun Kim's code
"""

class AseRelaxer:
    def __init__(
        self,
        calc,
        optimizer=FIRE2,
        cell_filter=FrechetCellFilter,
        mask=[1,1,1,1,1,1],
        fix_symm=True,
        symprec=1e-05,
        const_volume = False,
        fmax=0.00001,
        steps=5000,
        logfile='ase_relaxer.log',
        ):
        self.calc = calc
        self.optimizer = optimizer
        self.cell_filter = cell_filter
        self.mask = mask
        self.fix_symm = fix_symm
        self.symprec = symprec
        self.fmax = fmax
        self.steps = steps
        self.logfile = logfile
        self.constant_volume = const_volume

    def run(self, atoms):
        atoms = atoms.copy()
        if self.fix_symm:
            atoms.set_constraint(FixSymmetry(atoms, symprec=self.symprec))

        atoms.calc = self.calc
        cell_filter = self.cell_filter(atoms, constant_volume=self.constant_volume, mask=self.mask)
        optimizer = self.optimizer(cell_filter, logfile=self.logfile)
        optimizer.run(fmax=self.fmax, steps=self.steps)
        # torch.cuda.synchronize() # why did I add this line ..?
        atoms.info['steps'] = optimizer.get_number_of_steps()
        force_conv = check_atoms_conv(atoms.get_forces())
        atoms.info['force_conv'] = force_conv
        return atoms

def get_relaxer(config, calc, opt_type='unitcell', logfile='relax.log'):
    arr_args = config['opt'][f'{opt_type}'].copy()

    opt = OPT_DCT.get(arr_args['optimizer'].lower(), FIRE2)
    cell_filter = FILTER_DCT.get(arr_args['cell_filter'], FrechetCellFilter)

    arr_args['calc'] = calc
    arr_args['logfile'] = logfile
    arr_args.update({'optimizer': opt, 'cell_filter': cell_filter})

    return AseRelaxer(**arr_args)

def check_atoms_conv(forces: np.ndarray) -> bool:
    conv = True
    for i in range(forces.shape[-1]):
        if np.any(forces[:,i]) < 0:
            conv = False
    return conv


