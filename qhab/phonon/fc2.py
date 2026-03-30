from phonopy import load
import numpy as np
import os

import phonopy.file_IO as ph_IO

from cte2bench.logger import logger

def run_fc2_computation(config):
    name = config['io']['name']
    cwd = os.path.join(config["io"]["abswd"], config["fc2"]["save"])
    prev_wd = os.path.join(config["io"]["abswd"], config["supercell"]["save"])

    for i, eps in enumerate(config['strain']['eps']):
        logger.info(f'Computing 2nd-order force constants for volumetric strain {eps} [{i+1}/{len(config["strain"]["eps"]}]')
        ph = load(f'{prev_wd}/{name}-{eps}-phonopy.yaml.xz')
        force_set = np.load(f'{prev_wd}/{name}-{eps}-force_set.npy')
        ph.forces = force_set
        ph.produce_force_constants()
        fc2 = ph.force_constants
        ph_IO.write_force_constants_to_hdf5(force_constants=fc2, filename=f'{cwd}/{name}-{eps}-force_constants.hdf5')

