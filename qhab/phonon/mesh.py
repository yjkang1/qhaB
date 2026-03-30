from phonopy import load
import phonopy.file_IO as ph_IO

import os, gc, warnings
import ase.io as ase_IO
import numpy as np

from cte2bench.logger import logger
from cte2bench.util.utils import load_mesh_yaml, load_mesh_hdf5, imag_dos_frac, aseatoms2phonoatoms, check_imaginary_freqs

def run_mesh_computation(config):
    name = config['io']['name']
    cwd = os.path.join(config["io"]["abswd"], config["mesh"]["save"])
    sc_wd = os.path.join(config["io"]["abswd"], config["supercell"]["save"])
    fc2_wd = os.path.join(config["io"]["abswd"], config["fc2"]["save"])

    thermal_kwargs = {'t_min': config['mesh']['thermal']['t_min'],
                      't_max': config['mesh']['thermal']['t_max'],
                      't_step': config['mesh']['thermal']['t_step']}
   
    for i, eps enumerate(config['strain']['eps']):
        logger.info(f'Computing mesh and mesh properties for volumetric strain {eps} [{i+1}/{len(config["strain"]["eps"])}]')
        ph = load(f'{sc_wd}/{name}-{eps}-phonopy.yaml.xz')
        ph.force_constants = ph_IO.read_force_constants_hdf5(f'{fc2_wd}/{name}-{eps}-force_constants.hdf5')

        if config['mesh']['mesh']['run']:
            ph.run_mesh(config['mesh']['mesh'])
            phonon.write_hdf5_mesh(filename=f'{cwd}/mesh-{name}-{eps}.hdf5')
            # freqs, weights = ph.get_mesh_dict()['frequencies'], ph.get_mesh_dict['weights']
            # TODO; check imag freqs

        else:
            pass # TODO; parse mesh dict


        if config['mesh']['thermal']['run']:
            ph.run_thermal_properties(**thermal_kwargs)
            ph.write_yaml_thermal_properties(f'{cwd}/thermal_properties-{name}-{eps}.yaml')
            thermal_plt = ph.plot_thermal_properties()
            thermal_plt.savefig(f'{cwd}/thermal_properties-{name}-{eps}.png')
            thermal_plt.close()

        if config['mesh']['tdos']['run']:
            # no difference with auto_total_dos(mesh=mesh_numbers)
            ph.run_total_dos()
            phonon.write_total_dos(f'{cwd}/tdos-{name}-{eps}.dat')

            if config['mesh']['band']['run']:
                ph.auto_band_structure(write_yaml=True, filename=f'{cwd}/band-{name}-{eps}.yaml')
                band_dos_plt = ph.plot_band_structure_and_dos()
                band_dos_plt.savefig(f'{cwd}/band_dos-{name}-{eps}.png')
                band_dos_plt.close()
