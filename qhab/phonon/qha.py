import os, gc
import os.path as osp
from phonopy.api_qha import PhonopyQHA
from phonopy import load
from phonopy.file_IO import read_thermal_properties_yaml
from contextlib import redirect_stdout, redirect_stderr
import numpy as np
import ase.io as ase_IO
import matplotlib
import pandas as pd
from qhab.logger import logger

#TODO: rcparams

def process_qha(config):
    name = config['io']['name']
    logger.info(f'Preprocessing inputs for QHA of {name}')

    cwd = os.path.join(config["io"]["abswd"], config["qha"]["save"])
    strain_wd = os.path.join(config["io"]["abswd"], config["strain"]["save"])
    sc_wd = os.path.join(config["io"]["abswd"], config["supercell"]["save"])
    fc2_wd = os.path.join(config["io"]["abswd"], config["fc2"]["save"])
    mesh_wd = os.path.join(config["io"]["abswd"], config["mesh"]["save"])

    ph = load(f'{fc2_wd}/{name}-{eps}-phonopy.yaml.xz')
    primitive_matrix = ph.primitive_matirx
    primitive_factor = np.linalg.norm(np.linalg.det(primitive_matrix))

    strained_atoms = ase_IO.read(f'{strain_wd}/{name}-strained_relaxed.extxyz', index=':')
    energies = np.array([atoms.info['energy'] for atoms in strained_atoms]) * primitive_factor
    volumes = np.array([atoms.get_volume() for atoms in strained_atoms]) * primitive_factor

    thermal_filenames= []

    #TODO ; imaginary freqs

    logger.info(f'Collected volumes and energies .. primitive factor: {primitive_factor}')

    for i, eps in enumerate(config['strain']['eps']):
        thermal_filenames.append(f'{mesh_wd}/{name}-{eps}-thermal_properties.yaml')

    logger.info(f'Collected thermal properties !')

    temperatures, cv, entropy, fe_phonon, _, _ = read_thermal_properties_yaml(filenames=thermal_filenames)
    temperatures = np.array(temperatures, dtype=float)
    cv = np.array(cv, dtype=float)
    entropy = np.array(entropy, dtype=float)
    fe_phonon = np.array(fe_phonon, dtype=float)

    qha_kwargs = {'volumes': volumes, 'electronic_energies': free_energies,
                    'temperatures': temperatures, 'free_energy': fe_phonon,
                    'cv': cv, 'entropy': entropy, 'eos': conf['eos'], 't_max': conf['t_max'],
                    'verbose': True}

    if len(volumes) < 5:
        logger.warning('At least 5 volume points needed for EOS fitting .. returning')
        continue

    os.chdir(cwd)
    qha = PhonopyQHA(**qha_kwargs)
   
    logger.info(f'Plotting QHA results ...')
    # qha.plot_qha(thin_number=thin_number).savefig(f'{cwd}/qha_plot.png')
    qha.plot_qha(thin_number=thin_number).savefig(f'qha_plot.pdf')
    matplotlib.pyplot.close()

    qha.plot_helmholtz_volume(thin_number=thin_number).savefig('helmholtz_volume.png')
    qha.plot_volume_temperature().savefig('volume_temperature.png')
    qha.plot_thermal_expansion().savefig('thermal_expansion.png')
    matplotlib.pyplot.close()

    qha.plot_gibbs_temperature().savefig('gibbs_temperature.png')
    qha.plot_bulk_modulus_temperature().savefig('bulk_modulus.png')
    matplotlib.pyplot.close()

    try:
        qha.plot_heat_capacity_P_polyfit().savefig('heat_capacity_P_poly.png')
        qha.plot_heat_capacity_P_numerical().savefig('heat_capacity_P_numer.png')

    except Exception as exc:
        print(exc)

    qha.plot_gruneisen_temperature().savefig('gruneisen_temperature.png')
    matplotlib.pyplot.close()

    # save dat files at once
    logger.info('writting down qha data')
    qha.write_helmholtz_volume()
    qha.write_helmholtz_volume_fitted(thin_number=thin_number)
    qha.write_volume_temperature()
    qha.write_thermal_expansion()
    qha.write_gibbs_temperature()
    qha.write_bulk_modulus_temperature()

    try:
        qha.write_heat_capacity_P_numerical()
        qha.write_heat_capacity_P_polyfit()
    except Exception as exc:
        print(exc)

    qha.write_gruneisen_temperature()

    qha.write_helmholtz_volume_fitted(filename='helmhotz_volume_full.dat', thin_number=config['harmonic']['t_step'])
    qha.plot_pdf_helmholtz_volume(filename='helmhotz_volume_full.png', thin_number=config['harmonic']['t_step'])

    qha._bulk_modulus.plot().savefig(f'{conf["eos"]}.png')
    matplotlib.pyplot.close()
