from nequip.ase import NequIPCalculator

CALC_DCT = {
        'l': '/path/to/mir-group__NequIP-OAM-L__0.1.nequip.pt2',
        'xl': '/path/to/mir-group__NequIP-OAM-XL__0.1.nequip.pt2',
        } # TODO; find env path ?


def return_calc(config):
    conf = config['calculator']
    calc, model, modal = conf['calc'].lower(), conf['model'].lower(), conf['modal'].lower()
    model_path = CALC_DCT[modal]
    calc = NequIPCalculator.from_compiled_model(compile_path=model_path,device='cuda')
    print(f"INFO.CALC: [NequIP] model={model}, modal={modal}")
    return calc


