import ase.io as ase_IO
import gc, os

# import torch

from qhab.logger import logger
from qhab.util.utils import get_spgnum, apply_isometric_strain
from qhab.util.relax import get_relaxer

def run_volume_fixed_relaxation(config, calc):
    name = config['io']['name']
    cwd = os.path.join(config["io"]["abswd"], config["strain"]["save"])
    prev_wd = os.path.join(config["io"]["abswd"], config["unitcell"]["save"])

    atoms = ase_IO.read(f'{prev_wd}/{name}-unitcell_relaxed.extxyz')
    logfile = f'{cwd}/volume_fixed_relaxation.log'
    relaxer = get_relaxer(config, calc, opt_type='strain', logfile=logfile)
    init_sgn = get_spgnum(atoms)

    strained_output = []
    for i, eps in enumerate(config['strain']['eps']):
        logger.info(f'Relaxing structure with volumetric strain {eps}')
        strained = apply_isometric_strain(atoms, eps)
        init_vol = round(strained.get_volume()/len(strained), 4)

        relaxer.run(strained)
        strained.calc = None

        steps, force_conv = strained.info['steps'], strained.info['force_conv']
        post_vol = round(strained.get_volume()/len(strained), 4)
        ase_IO.write(f'{cwd}/{name}-{eps}_relaxed.extxyz', strained, format='extxyz')

        strained_output.append(strained)

        if steps >= config['opt']['strain']['steps'] or not force_conv:
            logger.warning(f'{name} volume-fixed relaxation of {eps} strain did not converge in {steps}')
        else:
            logger.info(f'Volume-fixed relaxation of {name} with {eps} strain was successfully converged in {steps}')

        if init_sgn != (post_sgn := get_spgnum(strained)):
            logger.warning(f'Symmetry of {name} w/ {eps} strain changed from {init_sgn} to {post_sgn} during relaxation')
        else:
            logger.info(f'Symmetry of {name} w/ {eps} did not break during relaxation')

        if init_vol != post_vol:
            logger.warning(f'Volume/atom of {name} w/ {eps} strain changed from {init_vol} to {post_vol} during relaxation')
        else:
            logger.info(f'Volume/atom of {name} w/ {eps} did not change during relaxation ({init_vol} \AA^3/atom)')

    ase_IO.write(f'{cwd}/{name}-strained_relaxed.extxyz', strained_output, format='extxyz')

    # torch.cuda.empty_cache()
