IO = {
    "wd": '.',
    "input": "./aln.extxyz",
    "load_args": {
        "format": "extxyz",
        "index": 0,
                },
    "format": {
        "fig": "png",
        "fc2": "hdf5",
        "atom": "extxyz",
        "mesh": "hdf5",
        "band": "yaml",
        "tdos": "dat",
        "qha": {
            "dat": True,
            "fig": True
                },
            },
    }

CALCULATOR = {
    "calc": "7net",
    "model": "zero",
    "modal": False,
    "batch": False,
    "d3": False,
    "calc_args": {
        "enable_flash": True
    },
    "tag": "7net_0"
            }

UNITCELL = {
    "run": True,
    "save": "./unitcell"
            }

STRAIN = {
    "run": True,
    "restart": False,
    "save": "./strain",
    "eps": [-0.04, -0.02, 0.00, 0.02, 0.04, 0.06, 0.08]
        }

SUPERCELL = {
    "generate": True,
    "calc": True,
    "restart": False,
    "matrix": [4, 4, 4],
    "primitive": [[1,0,0],[0,1,0],[0,0,1]],
    "distance": 0.01,
    "random_seed": 42,
    "save": "./supercell"
        }

FC2 = {
    "run": True,
    "restart": False,
    "save": "./fc2"
    }

MESH= {
    "run": True,
    "restart": False,
    "mesh": {
        "run": True,
        "numbers": [48, 48, 48]
            },
    "thermal": {
        "run": True,
        "t_min": 0,
        "t_max": 1201,
        "t_step": 1
            },
    "tdos": {"run": True},
    "pdos": {"run": True},
    "band": {"run": True},
    "save": "./mesh"
    }

QHA = {
    "run": True,
    "t_max": 1201,
    "thin_number": 50,
    "eos": "birch_murnaghan",
    "save": "./qha"
    }

RELAX = {
    "unitcell": {
        "fmax": 1.0e-5,
        "steps": 5000,
        "optimizer": "fire2",
        "fix_symm": True,
        "cell_filter": "frechet",
        "mask": [1, 1, 1, 1, 1, 1]
                },
    "strain": {
        "fmax": 1.0e-5,
        "steps": 5000,
        "optimizer": "fire2",
        "fix_symm": True,
        "const_volume": True,
        "cell_filter": "frechet",
        "mask": [1, 1, 1, 1, 1, 1]
                },
    }

if __name__ == '__main__':
    print('nothing wrong')
