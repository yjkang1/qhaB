import ase.io as ase_IO
from pymatgen.core import Structure
from pymatgen.io.vasp.sets import MPRelaxSet
from pymatgen.io.vasp import Potcar, Incar, Kpoints, Poscar
import os, subprocess, sys, yaml, shutil

from qhab.util.io import dumpYAML
from check_vasp import is_done

BASE_DIR="."
DFT_DIR="."

KPOINTS_MAP = {225: [11, 11, 11], 216: [11,11,11], 186: [11,11,9]}

def write_potcar(config, poscar_dir, path='.'):
    poscar = Poscar.from_file(poscar_dir)
    potcar_config=MPRelaxSet.CONFIG["POTCAR"]
    # symbols = [potcar_map[el] for el in poscar.site_symbols]

    full_potcar=[]
    for el in poscar.site_symbols:
        potcar_name_local=potcar_config[el]
        if el == 'Yb':
            potcar_name_local = 'Yb_3'
        if el == 'W':
            potcar_name_local = 'W_sv'
        potcar_path = os.path.join(config['potcar']['_dir'], potcar_name_local, "POTCAR")

        config['potcar']['el'] = potcar_name_local

        with open(potcar_path, "r") as f:
            data = f.readlines()
        full_potcar.extend(data)

    with open(os.path.join(path, "POTCAR"),"w") as f:
        f.write("".join(full_potcar))

    # poscar.write_file(f'{path}/POSCAR_pymatgen')
    return config


def write_input0_dirs(input_atoms, config0):
    for i, atoms in enumerate(input_atoms):
        config = config0.copy()
        atoms_dct = atoms.info.copy()

        config['unitcell']['mp-id'] = atoms_dct['material_id']
        config['unitcell']['name'] = name = atoms_dct['name']
        config['unitcell']['symm'] = symm =  int(atoms_dct['symm.no'])
        config['io']['name'] = label = f'{i}_{name}_{symm}'
        config['abswd'] = abswd = f'{DFT_DIR}/{label}'
        config['unitcell']['save0'] = unitcell_dir = f'{abswd}/unitcell/relax0'

        config['unitcell']['kpoints']['grid'] = grids = KPOINTS_MAP[symm]

        # os.makedirs(unitcell_dir, exist_ok=True)
        config['unitcell']['symm'] = int(symm)
        config['unitcell']['incar1']['EDIFF'] = 1e-08
        config['unitcell']['incar1']['ISYM'] = 1
        config['unitcell']['incar0']['ISYM'] = 1

        # ase_IO.write(f'{unitcell_dir}/POSCAR', atoms)
        # config = write_potcar(config, f'{unitcell_dir}/POSCAR', unitcell_dir)

        # incar = Incar.from_dict(config['incar'])
        # incar.update(config['unitcell']['incar0'])
        # incar.write_file(f'{unitcell_dir}/INCAR')

        # kpoints = Kpoints.gamma_automatic(kpts = grids)
        # kpoints.write_file(f'{unitcell_dir}/KPOINTS')

        dumpYAML(config, f'{abswd}/config.yaml')

def write_input1_dirs(input_atoms):
    for i, atoms in enumerate(input_atoms):
        atoms_dct = atoms.info.copy()

        name = atoms_dct['name']
        symm =  atoms_dct['symm.no']
        label = f'{i}_{name}_{symm}'
        abswd = f'{DFT_DIR}/{label}'

        with open(f'{abswd}/config.yaml', 'r') as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        unitcell_dir0 = f'{abswd}/unitcell/relax0'
        done, prob = is_done(unitcell_dir0)
        if done:
            config['unitcell']['save1'] = unitcell_dir1 = f'{abswd}/unitcell/relax1'
            os.makedirs(unitcell_dir1, exist_ok=True)

            incar = Incar.from_dict(config['incar'])
            incar.update(config['unitcell']['incar1'])
            incar.write_file(f'{unitcell_dir1}/INCAR')

            shutil.copy(f'{unitcell_dir0}/CONTCAR', f'{unitcell_dir1}/POSCAR')
            shutil.copy(f'{unitcell_dir0}/POTCAR', f'{unitcell_dir1}/POTCAR')
            shutil.copy(f'{unitcell_dir0}/KPOINTS', f'{unitcell_dir1}/KPOINTS')
        config['unitcell']['relax0'] = {'done': done, 'msg': prob}
        dumpYAML(config, f'{abswd}/config.yaml')

if __name__ == '__main__':
    input_atoms = ase_IO.read(f'{BASE_DIR}/inputs/phononDB-103-structures.extxyz', index=':')
    YAML_FILE=f'{BASE_DIR}/script/config.yaml'
    with open(YAML_FILE, 'r') as f:
        config0 = yaml.load(f, Loader=yaml.FullLoader)

    # write_input0_dirs(input_atoms, config0)
    write_input1_dirs(input_atoms)

