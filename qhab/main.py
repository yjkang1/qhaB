import argparse, warnings, sys, os, pprint, yaml
from ase.io import read
from pathlib import Path

from qhab.util.utils import get_spg
from qhab.util.parser import parse_config
from qhab.logger import logger
from qhab.util.io import dumpYAML

SLURM_VARS = [
    'SLURM_JOB_ID',
    'SLURM_JOB_NAME',
    'SLURM_CLUSTER_NAME',
    'SLURM_JOB_NODELIST',
    'SLURM_JOB_NUM_NODES',
    'SLURM_CPUS_ON_NODE',
]

def pre_record(config):
    info = {k: os.environ.get(k, 'N/A') for k in SLURM_VARS}

    atoms = read(config["io"]["input"], **config["io"]["load_args"])
    atoms_info = {
        'name': atoms.get_chemical_formula(empirical=True, mode='metal'),
        'space group': get_spg(atoms),
        'natom': len(atoms),
        'uMLIP': config['calculator'].get('calc', '?'),
        'model': config['calculator'].get('model', '?'),
        'modal': config['calculator'].get('calc', 'N/A'),
    }

    info.update(atoms_info)

    print('---Pre-run information---')
    pprint.pprint(info)
    print('... dumped at wd\n')
    dumpYAML(info, filename=f'{config["io"]["abswd"]}/qhaB.info')


def parse_args(argv: list[str]|None) -> None:
    parser = argparse.ArgumentParser(description= "cli tool")

    parser.add_argument('--config', type=str, default='./config.yaml',
            help='config yaml file directory')

    parser.add_argument('--name', type=str, default='PbTe_225',
            help='directory name for the run')

    return parser.parse_args(argv)

def main(argv: list[str] | None=None) -> None:
    args = parse_args(argv)
    config_dir, name = args.config, args.name

    with open(config_dir, 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    config['io']['wd'] = config['io']['name'] = name
    config['io']['abswd'] = abswd = os.path.abspath(name)
    os.makedirs(abswd, exist_ok=True)

    config = parse_config(config)
    dumpYAML(config, filename=f'{abswd}/parsed_config.yaml')
    logger.set_log_file(f'{abswd}/qhaB.stdout')
    logger.separator()
    logger.info('Initiating qhaB')
    pre_record(config)
    logger.separator()


    if any([config['unitcell']['run'], config['strain']['run'], config['supercell']['run']]):
        from qhab.calculator.tools import load_calc
        logger.separator()
        logger.info('Loading uMLIP calculator')
        logger.separator()
        calc = load_calc(config)

        if config['unitcell']['run']:
            from qhab.structure.unitcell import run_unitcell_relaxation
            with logger.step("Structural Relaxation of Input Structure"):
                run_unitcell_relaxation(config, calc)

        if config['strain']['run']:
            from qhab.structure.strain import run_volume_fixed_relaxation
            with logger.step("Volume Fixed Relaxation of Strained Structures"):
                run_volume_fixed_relaxation(config, calc)

        if config['supercell']['generate']:
            from qhab.phonon.supercell import run_supercell_generation
            with logger.step("Generation of Supercells with Displacements for FC2 Computation"):
                run_supercell_generation(config)

        if config['supercell']['calc']:
            from qhab.structure.supercell import run_force_calculation
            with logger.step("Force Calculation of Supercell Structure"):
                run_force_calculation(config, calc)

    if config['fc2']['run']:
        from qhab.phonon.fc2 import run_fc2_computation
        with logger.step("FC2 Computation from Generated Force Sets"):
            run_fc2_computation(config)

    if config['mesh']['run']:
        from qhab.phonon.mesh import run_mesh_computation
        with logger.step("Harmonic Mesh Computation"):
            run_mesh_computation(config)

    if config['qha']['run']:
        from qhab.phonon.qha import run_qha
        with logger.step("QHA Computation"):
            run_qha(config)

if __name__ == '__main__':
    main()
