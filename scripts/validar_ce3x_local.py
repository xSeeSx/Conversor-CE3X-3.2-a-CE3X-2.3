"""Prepare CE3X files and collect local evidence without executing CEX objects."""

import argparse
import csv
import json
import math
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'app'))
import converter as c

ORIGINAL = 'origen32.cex'
CASES = {'origen32': '3.2', 'convertido23': '2.3', 'nativo23': '2.3'}
ARCHIVED = {'origen32': ORIGINAL, 'convertido23': 'origen32_CE3X2.3.cex', 'nativo23': 'nativo23.cex'}
RATE_UNIT = 'kWh/m²·año'
METRIC_UNITS = {'Demanda': RATE_UNIT, 'EnergiaFinal': RATE_UNIT, 'EnergiaPrimariaNoRenovable': RATE_UNIT,
                'Emisiones': 'kgCO₂/m²·año'}
MEASURES = {
    **{name: name for name in METRIC_UNITS},
    'DemandaEdificioObjeto': 'Demanda', 'ConsumoEnergiaFinal': 'EnergiaFinal',
    'ConsumoEnergiaPrimariaNoRenovable': 'EnergiaPrimariaNoRenovable', 'EmisionesCO2': 'Emisiones',
    'CalificacionDemanda': 'Demanda', 'CalificacionEnergiaPrimariaNoRenovable': 'EnergiaPrimariaNoRenovable',
    'CalificacionEmisionesCO2': 'Emisiones',
}
SERVICES = {
    'cal': 'Cal', 'calefaccion': 'Cal', 'ref': 'Ref', 'refrigeracion': 'Ref', 'acs': 'Acs',
    'ilu': 'Ilu', 'iluminacion': 'Ilu', 'ven': 'Ven', 'ventilacion': 'Ven',
    'tot': 'Tot', 'total': 'Tot', 'global': 'Tot',
}
LEGACY_SERVICES = {'DemandaCalefaccion': 'Cal', 'DemandaRefrigeracion': 'Ref', 'DemandaACS': 'Acs'}


def header(path, version):
    blocks = c.read_cex(path)
    expected = {'2.3': 'CEXv2.3 Residencial', '3.2': 'CE3Xv3.2 Residencial'}[version]
    if blocks[0] != expected:
        raise ValueError(f'{path.name}: se esperaba {expected}, se obtuvo {blocks[0]}')
    return blocks


def read_plan(root):
    return json.loads((root / 'sesion.json').read_text(encoding='utf-8'))


def prepare(root, source, native):
    if source is None:
        raise ValueError('Indica -Origen32')
    header(source, '3.2')
    if native:
        header(native, '2.3')
    root.mkdir(parents=True)
    session = {'archivos': {'origen32': c.sha(source)}, 'opciones': {}}
    shutil.copyfile(source, root / ORIGINAL)
    if native:
        session['archivos']['nativo23'] = c.sha(native)
        shutil.copyfile(native, root / ARCHIVED['nativo23'])
    return convert(root, session)


def convert(root, session, selected=None):
    options = {} if selected is None else {'solar_choices': selected['choices'], 'consent': selected['token']}
    code, attempt = c.convert(root / ORIGINAL, c.ROOT / 'plantilla_23.cex', **options)
    session['conversion'] = attempt.manifest['status']
    if code == 2:
        session['opciones'] = attempt.manifest['pending_plan']['options']
        print(attempt.summary)
        for name, option in session['opciones'].items():
            print(f'{name}  -Consentimiento {option["token"]}')
    elif code == 0:
        session['opciones'] = {}
        session['archivos']['convertido23'] = c.sha(attempt.output)
        session['perdidas'] = len(attempt.audit.losses)
        mutable = root / 'exportar'
        mutable.mkdir(exist_ok=True)
        for case in session['archivos']:
            shutil.copyfile(root / ARCHIVED[case], mutable / f'{case}.cex')
    else:
        print(attempt.summary, file=sys.stderr)
    c.write_json(root / 'sesion.json', session)
    if code == 0:
        status(root, session)
    return code


def verify_originals(root, session):
    for case, digest in session['archivos'].items():
        if c.sha(root / ARCHIVED[case]) != digest:
            raise ValueError(f'Ha cambiado el archivo conservado de {case}')


def local_name(tag):
    return tag.rsplit('}', 1)[-1]


def children(element, tag):
    return [item for item in element if local_name(item.tag) == tag]


def collect_xml(path):
    with path.open('rb') as stream:
        data = stream.read(16 * 1024 * 1024 + 1)
    if len(data) > 16 * 1024 * 1024 or b'<!doctype' in data.replace(b'\x00', b'').lower():
        raise ValueError('XML demasiado grande o con DTD')
    doc = ET.fromstring(data)
    if local_name(doc.tag) != 'DatosEnergeticosDelEdificio':
        raise ValueError(f'Raíz de XML CE3X desconocida: {local_name(doc.tag)}')
    metrics = {}

    def add(key, text, unit):
        text = (text or '').strip()
        if not text:
            return
        value = text if unit == 'letra' else float(text.replace(',', '.'))
        if unit == 'letra' and value not in set('ABCDEFG'):
            return
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f'Indicador no finito: {key}')
        if key in metrics:
            raise ValueError(f'Ruta de indicador repetida: {key}')
        metrics[key] = {'valor': value, 'unidad': unit}

    def indicators(model, prefix):
        groups = [('Indicadores', list(model) + [item for group in ('Indicadores', 'Consumo')
                                                   for node in children(model, group) for item in node]),
                  ('Calificacion', [item for node in children(model, 'Calificacion') for item in node])]
        for scope, sections in groups:
            for section in sections:
                family = MEASURES.get(local_name(section.tag))
                if not family:
                    continue
                values = children(section, 'EdificioObjeto') if family == 'Demanda' and scope == 'Indicadores' else []
                for part in values[0] if values else section:
                    tag = local_name(part.tag)
                    service = SERVICES.get(tag.lower()) or LEGACY_SERVICES.get(tag)
                    if service:
                        unit = 'letra' if scope == 'Calificacion' else METRIC_UNITS[family]
                        add(f'{prefix}{scope}/{family}/{service}', part.text, unit)

    indicators(doc, '')
    # Legacy 2.3 exports final energy by carrier. Keep these figures distinct from
    # the aggregate final-energy indicators published by the current XML schema.
    for consumption in children(doc, 'Consumo'):
        for vectors in children(consumption, 'EnergiaFinalVectores'):
            for vector in vectors:
                for part in vector:
                    service = SERVICES.get(local_name(part.tag).lower())
                    if service and not list(part):
                        add(f'EnergiaFinalPorVectores/{local_name(vector.tag)}/{service}', part.text, RATE_UNIT)
    for section in children(doc, 'MedidasMejora'):
        for measure in children(section, 'MedidaMejora'):
            names = children(measure, 'Nombre')
            if len(names) == 1 and names[0].text:
                indicators(measure, f'MedidaMejora/{names[0].text.strip()}/')
    for family in ('OtrosIndicadores', 'DatosGeneralesyGeometria'):
        for section in children(doc, family):
            for item in children(section, 'Compacidad'):
                add('Geometria/Compacidad', item.text, 'm')
    if not metrics:
        raise ValueError('El XML no contiene demanda, consumo, emisiones o calificación reconocidos')
    return metrics


def structural_summary(blocks):
    env, windows, bridges, zones = blocks[3]
    envelope_ids = {row[0]: i for i, row in enumerate(env)}
    zone_ids = {'Edificio Objeto': 'edificio'}
    zone_ids.update((zone.state['nombre'], i) for i, zone in enumerate(zones) if isinstance(zone, c.CexObject))
    shadow_ids = {name: i for i, name in enumerate(blocks[10])}
    return {
        'superficie_util_m2': c.as_num(blocks[2][6], 'generales[6]'),
        'cerramientos': [{'tipo': f'{row[1]}|{row[-1]}', 'm2': c.as_num(row[2], 'cerramiento.area'),
                          'U_W_m2K': c.as_num(row[3], 'cerramiento.U'), 'zona': zone_ids.get(row[-2]),
                          'sombra': shadow_ids.get(row[7])} for row in env],
        'huecos': [{'cerramiento': envelope_ids.get(w.state['cerramientoAsociado']),
                    'zona': zone_ids.get(w.state.get('subgrupo')),
                    'sombra': shadow_ids.get(w.state.get('patronSombras')),
                    **{key: c.as_num(w.state[key], 'hueco.'+key)
                       for key in ('superficie', 'Uvidrio', 'Umarco', 'Gvidrio') if key in w.state}} for w in windows],
        'puentes': [{'psi_W_mK': c.as_num(row[3], 'puente.psi'),
                     'longitud_m': c.as_num(row[4], 'puente.longitud'),
                     'cerramiento': envelope_ids.get(row[7])} for row in bridges],
        'zonas': len(zones), 'patrones': len(blocks[9]), 'mejoras': len(blocks[5]),
        'grupos_instalaciones': [len(group) for group in blocks[4]],
        'equipos_comunes': [[{'tipo': row[1], 'rendimiento': c.json_value(row[2]), 'combustible': row[4],
                              'cobertura': c.json_value(row[5]), 'modo': row[6], 'zona': zone_ids.get(row[-1])}
                             for row in group] for group in blocks[4][:6]],
    }


def case_evidence(root, case):
    source = root / ARCHIVED[case]
    working = root / 'exportar' / f'{case}.cex'
    xml = working.with_suffix('.xml')
    indicators = collect_xml(xml) if xml.is_file() else {}
    saved = working.is_file() and c.sha(working) != c.sha(source)
    return {'estructura_inicial': structural_summary(header(source, CASES[case])),
            'cex_modificado': saved,
            'estructura_guardada': structural_summary(header(working, CASES[case])) if saved else None,
            'sha256_xml': c.sha(xml) if indicators else None, 'indicadores': indicators}


def status(root, session):
    if session['opciones']:
        print('Pendiente: revisar las omisiones y aceptar un token antes de preparar las copias.')
        return
    if 'convertido23' not in session['archivos']:
        print('Conversión bloqueada. No se han preparado copias para CE3X.')
        return
    for case in CASES:
        if case not in session['archivos']:
            continue
        evidence = case_evidence(root, case)
        project = root / 'exportar' / f'{case}.cex'
        pending = []
        if not evidence['cex_modificado']:
            pending.append('guardar la copia tras recalcular')
        if not evidence['sha256_xml']:
            pending.append(f'exportar el XML como {project.with_suffix(".xml")}')
        print(f'CE3X {CASES[case]}  {project}\n  ' +
              ('Pendiente: ' + ' y '.join(pending) if pending else 'CEX modificado y XML recogido.'))


def comparisons(cases):
    pairs = [('origen32', 'convertido23')]
    if 'nativo23' in cases:
        pairs = [('origen32', 'nativo23'), ('nativo23', 'convertido23')]
    rows = []
    for baseline, target in pairs:
        a, b = cases[baseline]['indicadores'], cases[target]['indicadores']
        for metric in sorted(a.keys() & b.keys()):
            x, y = a[metric]['valor'], b[metric]['valor']
            unit = a[metric]['unidad']
            if unit != b[metric]['unidad']:
                continue
            numeric = unit not in (None, 'letra') and isinstance(x, float) and isinstance(y, float)
            delta = y-x if numeric else None
            rows.append((baseline, target, metric, unit, x, y, delta, delta*100/x if numeric and x else None))
    return rows


def collect(root, session):
    if 'convertido23' not in session['archivos']:
        raise ValueError('Primero completa la conversión del ensayo')
    cases = {case: case_evidence(root, case) for case in session['archivos']}
    c.write_json(root / 'resumen.json', {
        'conversion': session['conversion'], 'perdidas': session['perdidas'], 'sha256_entradas': session['archivos'],
        'referencia_nativa_23': 'nativo23' in cases,
        'comparacion': ('comparaciones con la referencia aportada' if 'nativo23' in cases
                       else 'diferencias observadas entre versiones y conversión sin referencia nativa 2.3'),
        'casos': cases,
    })
    with (root / 'indicadores.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.writer(stream)
        writer.writerow(('base', 'destino', 'indicador', 'unidad', 'valor_base', 'valor_destino', 'delta', 'delta_pct'))
        writer.writerows(comparisons(cases))
    status(root, session)
    print(f'Resumen {root / "resumen.json"}')
    print(f'Indicadores {root / "indicadores.csv"}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('preparar', 'aceptar', 'estado', 'recoger'))
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--source32', type=Path)
    parser.add_argument('--native23', type=Path)
    parser.add_argument('--consent')
    parser.add_argument('--public-fixture', action='store_true')
    args = parser.parse_args()
    root = args.directory.resolve()
    try:
        if root.is_relative_to(REPO) and not args.public_fixture:
            raise ValueError('Usa una carpeta fuera del repositorio o indica -MuestraPublica para una muestra pública')
        if args.mode == 'preparar':
            return prepare(root, args.source32, args.native23)
        session = read_plan(root)
        verify_originals(root, session)
        if args.mode == 'aceptar':
            matches = [x for x in session['opciones'].values() if x['token'] == args.consent]
            if len(matches) != 1:
                raise ValueError('El consentimiento no coincide con una opción pendiente')
            return convert(root, session, matches[0])
        if args.mode == 'estado':
            status(root, session)
        else:
            collect(root, session)
        return 0
    except (OSError, ValueError, c.ConversionError, ET.ParseError) as exc:
        print(f'Validación: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
