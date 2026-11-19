"""Prepare the public baseline and a disposable CE3X 3.2 copy for the blind trial."""

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
import converter as c

PUBLIC_EXAMPLE = 'b57a58f3e639757e6b8576f895cc3f6cfc8abd8952cf3ce22c7238df1da54dba'


def load_baseline(source):
    if c.sha(source) != PUBLIC_EXAMPLE:
        raise ValueError('Se requiere el ejemplo oficial 3.2 «2 Vivienda dentro de bloque»')
    blocks = c.read_cex(source)
    blocks[5] = []
    blocks[6][2] = []
    blocks[11][:3] = ['', '', '']
    window = next(w for w in blocks[3][1] if w.state['descripcion'] == 'V5')
    window.state.update(patronSombras='Sin patrón', tieneProteccionSolar=False, correctorFSCTE=1.,
                        correctorFSInvierno=1., correctorFSVerano=1.)
    window.state['elementosProteccionSolar'] = (
        [''] * 6 + [['', 0, 0], ['', 0, 0], '', False, False, '', False, False, '', '', '',
                    False, False, False, False, False, False, False, ['', '']])
    return blocks


def prepare(source, directory):
    blocks = load_baseline(source)
    directory.mkdir(parents=True)
    base = directory / 'base32.cex'
    base.write_bytes(c.encoded(blocks))
    shutil.copyfile(base, directory / 'persiana32.cex')
    template = c.ROOT / 'plantilla_23.cex'
    status, attempt = c.convert(base, template)
    c.require(status == 2, 'E_FIXTURE', attempt.summary)
    # The known omissions apply to this hash-pinned teaching example only.
    option = attempt.manifest['pending_plan']['options']['omit']
    status, attempt = c.convert(base, template, solar_choices=option['choices'], consent=option['token'])
    c.require(status == 0, 'E_FIXTURE', attempt.summary)
    native_base = directory / 'base23.cex'
    attempt.output.rename(native_base)
    shutil.copyfile(native_base, directory / 'referencia23.cex')
    return directory.resolve()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Ejemplo oficial «2 Vivienda dentro de bloque.cex»')
    parser.add_argument('directory', type=Path, help='Carpeta nueva de trabajo')
    args = parser.parse_args()
    print(prepare(args.source, args.directory))
