"""Prepare public test projects for paired CE3X 3.2 and 2.3 DHW runs."""

import argparse
from pathlib import Path

from preparar_ensayo_persianas import load_baseline
from validar_bateria_final import c, run_case, thermal_solar


def prepare(source, root):
    baseline = load_baseline(source)
    root.mkdir(parents=True)
    (root / 'origenes').mkdir()
    (root / 'iniciales').mkdir()
    for zone, area, flow, province, city, postal, radiation, monthly in (
        ('D1', 150, 112, 'Navarra', 'Pamplona', '31001', 'II', 40),
        ('D2', 85, 75, 'La Rioja', 'Logroño', '26001', 'III', 62),
    ):
        blocks = thermal_solar(baseline)
        name = f'acs_{zone}'
        blocks[1][:5] = [f'Ensayo {zone}', 'Calle de prueba 1', city, province, postal]
        blocks[1][26:] = ['Ninguna', [], 'ResidencialPrivado']
        blocks[2][2:7] = [province, city, zone, radiation, str(area)]
        blocks[2][9] = str(flow)
        blocks[2][22] = str(area)
        blocks[2][23:26] = ['1', '0', '1']
        blocks[4][0][0][5][0][0] = str(area)
        solar = blocks[4][12][0].state
        solar.update(dict.fromkeys(c.SOLAR_MONTHS, monthly))
        solar['id'] = c.CexObject(c.GlobalRef('uuid','UUID'), {'int': 9114}, 'reduce')
        record = run_case(root, name, blocks, 'experimental')
        (root / f'{name}32.cex').write_bytes((root / 'origenes' / f'{name}32.cex').read_bytes())
        print(record['destino'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    prepare(args.source, args.directory)
