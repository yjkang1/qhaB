import ase.io as ase_IO
import gc, os
from cte2bench.util.relax import get_relaxer
from cte2bench.util.utils import get_spgnum

from cte2bench.logger import logger

def run_unitcell_relaxation(config, calc):
    name = config['io']['name']
    cwd = os.path.join(config["io"]["abswd"], config["unitcell"]["save"])

    atoms = ase_IO.read(config['io']['input'], **config['io']['load_args'])
    logfile = f'{cwd}/unitcell_relaxation.log' 
    relaxer = get_relaxer(config, calc, opt_type='unitcell', logfile=logfile)
    init_sgn = get_spgnum(atoms)
    atoms = relaxer.run(atoms)
    atoms.calc = None
    post_sgn = get_spgnum(atoms)

    steps, force_conv = atoms.info['steps'], atoms.info['force_conv']
    ase_IO.write(f'{cwd}/{name}-unitcell_relaxed.extxyz', atoms, format='extxyz')

    if steps >= config['opt']['unitcell']['steps'] or not force_conv:
        logger.warning(f'{name} unit cell relaxation did not converge in {steps}')
    else:
        logger.info(f'{name} unit cell relaxation successfully converged in {steps}')

    if init_sgn != post_sgn:
        logger.warning(f'Symmetry of {name} changed from {init_sgn} to {post_sgn} during unitcell relaxation')
    else:
        logger.info(f'Symmetry of {name} did not break during unitcell relaxation')

    del relaxer, atoms
    gc.collect()
