import argparse, os, pprint, re, yaml
from ase.io import read

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

ROTATE_TARGETS = ['qhaB.info', 'qhaB.stdout', 'parsed_config.yaml']


def _archive_indices(abswd, basename):
    pattern = re.compile(rf'^{re.escape(basename)}\.(\d+)$')
    return sorted(
        int(m.group(1))
        for entry in os.listdir(abswd)
        if (m := pattern.match(entry))
    )


def rotate_previous(abswd):
    """
    Move any existing qhaB.info / qhaB.stdout / parsed_config.yaml in `abswd`
    to <file>.{N}, where N is one greater than the largest existing archive
    index across the rotated targets (so the oldest archive remains .0).

    Returns
    -------
    rerun_index : int
        Ordinal of the *current* run (0 for a fresh directory, 1 after the
        first re-run, …). Equals the number of completed prior runs.
    prev_config_path : str | None
        Path to the just-archived parsed_config.yaml.{N}, or None if there
        was no parsed_config.yaml to rotate.
    """
    existing = [t for t in ROTATE_TARGETS
                if os.path.isfile(os.path.join(abswd, t))]
    if not existing:
        return 0, None

    indices = []
    for t in ROTATE_TARGETS:
        indices.extend(_archive_indices(abswd, t))
    next_idx = max(indices) + 1 if indices else 0

    for t in existing:
        os.rename(os.path.join(abswd, t),
                  os.path.join(abswd, f'{t}.{next_idx}'))

    prev_config_path = (os.path.join(abswd, f'parsed_config.yaml.{next_idx}')
                        if 'parsed_config.yaml' in existing else None)
    return next_idx + 1, prev_config_path


def diff_config(new, old, prefix=''):
    """
    Recursively compare two parsed-config dicts and return a list of leaf
    differences as [{ 'dotted.path': {'old': ..., 'new': ...} }, ...].
    Branches present in only one side are reported with the literal
    string '<missing>' on the other side.
    """
    MISSING = '<missing>'
    if not (isinstance(new, dict) and isinstance(old, dict)):
        return [] if new == old else [{prefix or '<root>':
                                       {'old': old, 'new': new}}]

    diffs = []
    for k in sorted(set(new) | set(old)):
        path = f'{prefix}.{k}' if prefix else k
        nv = new.get(k, MISSING)
        ov = old.get(k, MISSING)
        if isinstance(nv, dict) and isinstance(ov, dict):
            diffs.extend(diff_config(nv, ov, prefix=path))
        elif nv != ov:
            diffs.append({path: {'old': ov, 'new': nv}})
    return diffs


def pre_record(config, rerun_index=0, prev_config_path=None):
    info = {k: os.environ.get(k, 'N/A') for k in SLURM_VARS}

    atoms = read(config["io"]["input"], **config["io"]["load_args"])
    atoms_info = {
        'name': atoms.get_chemical_formula(empirical=True, mode='metal'),
        'space group': get_spg(atoms),
        'natom': len(atoms),
        'uMLIP': config['calculator'].get('calc', '?'),
        'model': config['calculator'].get('model', '?'),
        'modal': config['calculator'].get('modal', 'N/A'),
    }

    info.update(atoms_info)

    if rerun_index > 0:
        rerun = {'rerun_index': rerun_index,
                 'previous_runs': rerun_index}
        if prev_config_path is not None and os.path.isfile(prev_config_path):
            with open(prev_config_path, 'r') as f:
                prev = yaml.safe_load(f)
            diffs = diff_config(config, prev)
            rerun['diff_from_previous'] = diffs if diffs else 'no changes'
            rerun['previous_config'] = os.path.basename(prev_config_path)
        info['rerun'] = rerun

    print('---Pre-run information---')
    pprint.pprint(info)
    pprint.pprint(config)
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

    config['io']['name'] = name
    config['io']['abswd'] = abswd = os.getcwd()
    os.makedirs(abswd, exist_ok=True)

    rerun_index, prev_config_path = rotate_previous(abswd)

    config = parse_config(config)
    dumpYAML(config, filename=f'{abswd}/parsed_config.yaml')
    logger.set_log_file(f'{abswd}/qhaB.stdout')
    logger.separator()
    if rerun_index:
        archived_idx = rerun_index - 1
        logger.info(
            f'Detected previous run(s); rotated existing artefacts to '
            f'qhaB.info.{archived_idx}, qhaB.stdout.{archived_idx}, '
            f'parsed_config.yaml.{archived_idx}'
        )
    logger.info(f'Initiating qhaB (run #{rerun_index})')
    pre_record(config, rerun_index=rerun_index,
               prev_config_path=prev_config_path)
    logger.separator()

    if any([config['unitcell']['run'], config['strain']['run'], config['supercell']['calc']]):
        from qhab.calculator.tools import load_calc
        logger.separator()
        logger.info('Loading uMLIP calculator')
        logger.separator()
        calc = load_calc(config)

        if config['unitcell']['run']:
            logger.separator()
            from qhab.structure.unitcell import run_unitcell_relaxation
            with logger.step("Structural Relaxation of Input Structure"):
                run_unitcell_relaxation(config, calc)

        if config['strain']['run']:
            logger.separator()
            from qhab.structure.strain import run_volume_fixed_relaxation
            with logger.step("Volume Fixed Relaxation of Strained Structures"):
                run_volume_fixed_relaxation(config, calc)

        if config['supercell']['generate']:
            logger.separator()
            from qhab.phonon.supercell import run_supercell_generation
            with logger.step("Generation of Supercells with Displacements for FC2 Computation"):
                run_supercell_generation(config)

        if config['supercell']['calc']:
            logger.separator()
            from qhab.structure.supercell import run_force_calculation
            with logger.step("Force Calculation of Supercell Structure"):
                run_force_calculation(config, calc)

    if config['fc2']['run']:
        logger.separator()
        from qhab.phonon.fc2 import run_fc2_computation
        with logger.step("FC2 Computation from Generated Force Sets"):
            run_fc2_computation(config)

    if config['mesh']['run']:
        logger.separator()
        from qhab.phonon.mesh import run_mesh_computation
        with logger.step("Harmonic Mesh Computation"):
            run_mesh_computation(config)

    if config['qha']['run']:
        logger.separator()
        from qhab.phonon.qha import run_qha
        with logger.step("QHA Computation"):
            run_qha(config)
    return

if __name__ == '__main__':
    main()
