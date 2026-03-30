import os

from qhab.config import IO, CALCULATOR, UNITCELL, STRAIN, SUPERCELL, FC2, MESH, QHA, RELAX

DEFAULT_CONFIG = {
    'io': IO,
    'calculator': CALCULATOR,
    "unitcell": UNITCELL,
    "strain": STRAIN,
    "fc2": FC2,
    "mesh": MESH,
    "supercell": SUPERCELL,
    "qha": QHA,
    "relax": RELAX,
}

def _is_defined(x):
    return x is not None and x is not False

def override_default(override: dict, default: dict = DEFAULT_CONFIG) -> dict:
    merged = default.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = override_default(value, merged[key])
        else:
            merged[key] = value
    return merged

def finalize_default(config):
    conf = config['calculator']

    calc, model, modal = conf.get('calc', 'sevennet'), conf.get('model', 'zero'), conf.get('modal', None)
    assert any([calc, model, modal]), 'At least one of uMLIP Calcualtor, Model, or Modal must be provided.'

    tag = '_'.join(map(str, filter(_is_defined, [calc, model, modal])))
    config['calculator']['tag'] = tag

    # wd = '/'.join(map(str, filter(_is_defined, [calc, model, modal])))
    assert os.path.isfile(input_file := config['io']['input']), f'Input file {input_file} N/A !'
    
    for key in DEFAULT_CONFIG.keys():
        if config[key].get('save'):
            os.makedirs(cwd := os.path.join(config['io']['abswd'], config[key]['save']), exist_ok=True)
            config[key]['save'] = cwd

    return config

def parse_config(config):
    config = override_default(config)
    config = finalize_default(config)
    return config

if __name__ == '__main__':
    import sys, yaml
    from qhab.util.io import dumpYAML

    config_yaml = sys.argv[1]

    with open(config_yaml, 'r') as f:
        config0 = yaml.safe_load(f)

    config = parse_config(config)

    parsed_yaml = f'{config["io"]["abswd"]}/parsed.yaml'
    dumpYAML(config, parsed_yaml)
