"""Prepare matched native CE3X models to test annual PV autoconsumption."""

import argparse
from copy import deepcopy
from pathlib import Path
from uuid import UUID

from validar_bateria_final import c, run_case


def prepare(source, directory):
    base = c.read_cex(source)
    systems = base[4]
    candidate, reason = c.solar_candidate(systems[12], systems, base[2])
    if base[0] != 'CE3Xv3.2 Residencial' or base[5] or not candidate or base[2][4] != 'D1':
        raise ValueError(f'Se requiere el origen del ensayo termosolar D1. {reason}')

    if len(systems[0][0]) == 10:
        systems[0][0].insert(9, ['2', '', ''])
    directory.mkdir(parents=True)
    (directory / 'origenes').mkdir()
    (directory / 'iniciales').mkdir()
    systems[12] = []
    for name, series in (
        ('fv_control', None),
        ('fv_distribuida', [10] * 12),
        ('fv_concentrada', [0] * 6 + [120] + [0] * 5),
    ):
        scenario = deepcopy(base)
        if series is not None:
            generator = dict(zip(c.SOLAR_MONTHS, series))
            generator.update(nombre='FV de ensayo', zona='Edificio Objeto', potencia=1.0,
                             tipo=None, consumoMensual=None)
            identifier = UUID('5bcb2d88-049b-4327-baba-4ad68fb1fa15')
            generator['id'] = c.CexObject(c.GlobalRef('uuid', 'UUID'), {'int': identifier.int}, 'reduce')
            scenario[4][13] = [c.CexObject(c.GlobalRef('models', 'GeneradorElectrico'), generator)]
        (directory / f'{name}32.cex').write_bytes(c.encoded(scenario))

    run_case(directory, 'fv_control', base, 'omit')
    systems[6] = [['Fotovoltaica anual de ensayo', 'renovable', ['', '', '', False],
                   ['120', '', '', '', '', ''], [False, True], 'Edificio Objeto']]
    run_case(directory, 'fv_anual', base, 'omit')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='origenes/acs_D132.cex del ensayo de ACS')
    parser.add_argument('directory', type=Path, help='directorio nuevo de trabajo')
    args = parser.parse_args()
    prepare(args.source, args.directory)
