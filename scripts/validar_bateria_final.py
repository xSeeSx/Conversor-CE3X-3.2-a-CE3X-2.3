"""Build public CE3X release checks and collect the files saved by CE3X 2.3."""

import argparse
import copy
import csv
import io
import json
import shutil
from pathlib import Path
from xml.etree.ElementTree import ParseError

from preparar_ensayo_persianas import load_baseline
import converter as c
from validar_ce3x_local import collect_xml, comparisons, header, structural_summary

FIXTURES = c.ROOT.parent / 'fuentes' / 'fixtures'
TEMPLATE = c.ROOT / 'plantilla_23.cex'


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))


def simple(baseline):
    result = copy.deepcopy(baseline)
    result[1][26:] = ['', [], '']
    result[2][21:] = [''] * 5
    return result


def thermal_solar(baseline):
    result = simple(baseline)
    # Synthetic D2 trial. No data of the teaching building are attributed to Logroño.
    result[1][:5] = ['Ensayo D2', 'Calle de prueba 1', 'Logroño', 'La Rioja', '26001']
    result[2][2:7] = ['La Rioja', 'Logroño', 'D2', 'III', '100']
    result[2][9] = '100'
    result[4] = [[] for _ in range(14)]
    result[4][0] = [['ACS', 'ACS', ['100', '', ''], 'Efecto Joule', 'Electricidad',
                     [['100', '100'], ['', ''], ['', '']], 'Conocido (Ensayado/justificado)',
                     ['100', '', ''], [False], 'Edificio Objeto']]
    production = fixture('solar_d2_ensayos.json')['casos'][0]['produccion_mensual_kwh']
    state = dict(zip(c.SOLAR_MONTHS, production))
    state.update(nombre='Solar', zona='Edificio Objeto', potencia=1, servicio='ACS',
                 tipo=None, consumoMensual=None)
    result[4][12] = [c.CexObject(c.GlobalRef('models', 'GeneradorTermosolar'), state)]
    return result


def envelope_and_pv(baseline):
    result = simple(baseline)
    env, windows, _, zones = result[3]
    env.extend([
        ['Medianería', 'Fachada', '20', 0, 200, '', '', 'Sin patrón', '8', '2.5', '1', 'Edificio Objeto', 'edificio'],
        ['Muro enterrado', 'Fachada', '20', 1.4, 200, '1', '', 'Sin patrón', 'Conocidas', ['1.4'], '8', '2.5', '1', 'Edificio Objeto', 'terreno'],
        ['Cubierta exterior', 'Cubierta', '20', 1.0, 344, 'Techo', '', 'Sin patrón', 'Por defecto', ['Cubierta plana'], '5', '4', '1', 'Edificio Objeto', 'aire'],
        ['Cubierta enterrada', 'Cubierta', '20', 1.0, 344, 'Techo', '', 'Sin patrón', 'Conocidas', ['1.0'], '5', '4', '1', '0.5', 'Edificio Objeto', 'terreno'],
        ['Suelo exterior', 'Suelo', '20', 1.0, 344, 'Suelo', '', 'Sin patrón', 'Conocidas', ['1.0'], '5', '4', '1', 'Edificio Objeto', 'aire'],
        ['Suelo terreno', 'Suelo', '20', 1.0, 750, 'Suelo', '', 'Sin patrón', 'Por defecto', True, '', [], '5', '4', '1', 'Edificio Objeto', 'terreno'],
        ['Partición alta', 'Partición Interior', '20', 1.19, 120, 'Espacio bajo cubierta inclinada', '', 'Sin patrón', 'Estimadas', ['Ligeramente Ventilado', '52.27', False, 'El cerramiento', 'Por defecto'], '', '', '', 'Edificio Objeto', 'horizontal superior'],
    ])
    partitions = fixture('particiones_oficiales_23.json')['rows']
    for kind in ('vertical', 'horizontal inferior'):
        row = next(row for row in partitions if row[-1] == kind)
        row[2], row[-2] = '20', 'Zona interior'
        env.append(row)
    zone_class = c.GlobalRef('ventanaSubgrupo', 'claseZona')
    zones.extend([
        c.CexObject(zone_class, dict(nombre='Planta baja', raiz='Edificio Objeto', tipo='Subgrupo', superficie='70')),
        c.CexObject(zone_class, dict(nombre='Zona interior', raiz='Planta baja', tipo='Subgrupo', superficie='30')),
    ])
    cls = 'Envolvente.objetosEnvolvente.HuecoConocidas'
    attrs = {k: v for k, v in windows[0].state.items() if k in c.mm_schema()[cls]}
    attrs.update(__tipo__='HuecoConocidas', UvidrioConocido=str(attrs['Uvidrio']),
                 UmarcoConocido=str(attrs['Umarco']), GvidrioConocido=str(attrs['Gvidrio']),
                 marcoSeleccionado='', vidrioSeleccionado='')
    windows[0] = c.CexObject(c.GlobalRef('Envolvente.objetosEnvolvente', 'HuecoConocidas'), attrs)
    area = result[2][6]
    result[4][2] = [['Refrigeración eléctrica', 'refrigeracion', ['', '', '300'], 'Bomba de Calor',
                     'Electricidad', [['', ''], ['', ''], [area, '100']], 'Conocido (Ensayado/justificado)',
                     ['', '', '300'], [], 'Edificio Objeto']]
    result[4][6] = [['Fotovoltaica anual de prueba', 'renovable', ['', '', '', False],
                     ['2', '', '', '', '', ''], [False, True], 'Edificio Objeto']]
    return result


def run_case(root, name, blocks, choice):
    source = root / 'origenes' / f'{name}32.cex'
    source.write_bytes(c.encoded(blocks))
    digest = c.sha(source)
    code, attempt = c.convert(source, TEMPLATE)
    record = {'origen_sha256': digest, 'preinspeccion': attempt.manifest['status'], 'decision': choice}
    if choice:
        options = attempt.manifest.get('pending_plan', {}).get('options', {})
        if code != 2 or attempt.output.exists() or (choice != 'cancelar' and choice not in options):
            raise ValueError(f'{name}: decisión inesperada: {attempt.summary}')
        if choice == 'cancelar':
            plan = attempt.manifest['pending_plan']
            commands = [{'command': 'convert', 'source': str(source)},
                        {'command': 'decision', 'id': plan['id'], 'choice': 'cancel'}]
            responses = io.StringIO()
            c.serve(io.StringIO(''.join(json.dumps(command) + '\n' for command in commands)), responses)
            if '\nCANCELADO\t' not in responses.getvalue() or attempt.output.exists() or c.sha(source) != digest:
                raise ValueError(f'{name}: cancelación o integridad inesperada')
            record['estado'] = 'CANCELADO'
            return record
        option = options[choice]
        code, attempt = c.convert(source, TEMPLATE, solar_choices=option['choices'], consent=option['token'])
    if code != 0 or c.sha(source) != digest:
        raise ValueError(f'{name}: {attempt.summary}')
    target = f'{name}23.cex'
    archived = root / 'iniciales' / target
    attempt.output.rename(archived)
    shutil.copyfile(archived, root / target)
    record.update(destino=target, destino_sha256=c.sha(archived), estado=attempt.manifest['status'],
                  perdidas=len(attempt.audit.losses))
    return record


def prepare(source, root, native_blind=None):
    baseline = load_baseline(source)
    blind = copy.deepcopy(baseline)
    blind_evidence = fixture('persiana_ce3x.json')
    if native_blind:
        if c.sha(native_blind) != blind_evidence['cex32_sha256']:
            raise ValueError('El CEX de persiana debe ser el ensayo 3.2 registrado por SHA256')
        blind = c.read_cex(native_blind)
    else:
        next(w for w in blind[3][1] if w.state['descripcion'] == 'V5').state.update(blind_evidence['estado_32'])
    solar = thermal_solar(baseline)
    cases = [
        ('directo', simple(baseline), None), ('persiana_omitida', blind, 'omit'),
        ('solar_adaptada', solar, 'adapt'), ('solar_omitida', solar, 'omit'),
        ('solar_cancelada', solar, 'cancelar'), ('envolvente_pv', envelope_and_pv(baseline), None),
        ('mejoras', c.read_cex(source), 'omit'),
    ]
    root.mkdir(parents=True)
    (root / 'origenes').mkdir()
    (root / 'iniciales').mkdir()
    report = {name: run_case(root, name, blocks, choice) for name, blocks, choice in cases}
    shutil.copyfile(root / 'origenes' / 'directo32.cex', root / 'directo32_recalculado.cex')
    c.write_json(root / 'bateria.json', report)
    print(root.resolve())


def measure_results(blocks):
    reports = {}
    fields = ('ddaBrutaCal', 'ddaBrutaRef', 'ddaBrutaACS', 'enPrimNoRen', 'emisiones')
    for measure in blocks[5]:
        building = measure.state.get('datosNuevoEdificio')
        native = building.state.get('datosResultados') if isinstance(building, c.CexObject) else None
        if isinstance(native, c.CexObject):
            reports[measure.state['nombre']] = {key: native.state[key] for key in fields if key in native.state}
    return reports


def collect(root, exports):
    report = json.loads((root / 'bateria.json').read_text(encoding='utf-8'))
    for name, case in report.items():
        source = root / 'origenes' / f'{name}32.cex'
        if c.sha(source) != case['origen_sha256']:
            raise ValueError(f'{name}: cambió el origen archivado')
        if not case.get('destino'):
            continue
        target = case['destino']
        initial = root / 'iniciales' / target
        if c.sha(initial) != case['destino_sha256']:
            raise ValueError(f'{name}: cambió la conversión archivada')
        saved = exports / target
        xml = saved.with_suffix('.xml')
        before_blocks = header(initial, '2.3')
        before = structural_summary(before_blocks)
        orig_blocks = header(source, '3.2')
        orig = structural_summary(orig_blocks)
        case['cambios_conversion'] = [key for key in orig if orig[key] != before[key]]
        case['tipologias'] = sorted({wall['tipo'] for wall in before['cerramientos']})
        case['clases_huecos'] = sorted({window.cls.name for window in before_blocks[3][1]})
        case['zonas'] = before['zonas']
        case['mejoras'] = before['mejoras']
        case['costes_mejora'] = len(before_blocks[6][2])
        case['costes_mejora_preservados'] = c.typed_value(orig_blocks[6][2]) == c.typed_value(before_blocks[6][2])
        case['selecciones_informe_preservadas'] = c.typed_value(orig_blocks[11][:3]) == c.typed_value(before_blocks[11][:3])
        case['sombras_preservadas'] = c.typed_value(orig_blocks[9:11]) == c.typed_value(before_blocks[9:11])
        case['cex_guardado'] = saved.is_file() and c.sha(saved) != c.sha(initial)
        try:
            if case['cex_guardado']:
                after_blocks = header(saved, '2.3')
                after = structural_summary(after_blocks)
                case['cambios_estructura'] = [key for key in before if before[key] != after[key]]
                case['costes_guardados_preservados'] = before_blocks[6][2] == after_blocks[6][2]
                before_geometry = [row[:2] + row[3:] for row in before_blocks[9]]
                after_geometry = [row[:2] + row[3:] for row in after_blocks[9]]
                case['geometria_sombra_guardada_preservada'] = (before_geometry == after_geometry
                                                              and before_blocks[10] == after_blocks[10])
                case['coeficientes_sombra_actualizados'] = [
                    a[0] for a, b in zip(before_blocks[9], after_blocks[9]) if a[:2] == b[:2] and a[2] != b[2]]
                if before_blocks[5]:
                    initial_results = measure_results(before_blocks)
                    saved_results = measure_results(after_blocks)
                    case['indicadores_mejoras_guardadas'] = saved_results
                    case['mejoras_resultados_actualizados'] = [
                        name for name, metrics in saved_results.items() if metrics != initial_results.get(name)]
                case['cex_guardado_sha256'] = c.sha(saved)
            if xml.is_file():
                case['indicadores'] = collect_xml(xml)
                case['xml_sha256'] = c.sha(xml)
        except (OSError, ValueError, c.ConversionError, KeyError, ParseError) as exc:
            case['error_evidencia'] = str(exc)
    control = exports / 'directo32_recalculado.cex'
    control_xml = control.with_suffix('.xml')
    if control.is_file():
        archived = root / 'origenes' / 'directo32.cex'
        blocks = header(control, '3.2')
        original = header(archived, '3.2')
        control_report = {'cex_guardado': c.sha(control) != c.sha(archived),
                          'estructura_preservada': structural_summary(blocks) == structural_summary(original),
                          'generales_comunes_preservados': blocks[2][:21] == original[2][:21],
                          'sombras_preservadas': blocks[9:11] == original[9:11]}
        if control_xml.is_file():
            try:
                control_report.update(indicadores=collect_xml(control_xml), xml_sha256=c.sha(control_xml))
            except (OSError, ValueError, ParseError) as exc:
                control_report['error_evidencia'] = str(exc)
        report['directo32_recalculado'] = control_report
    c.write_json(root / 'resultados.json', report)
    with (root / 'comparacion.csv').open('w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerow(('base', 'destino', 'indicador', 'unidad', 'valor_base', 'valor_destino', 'delta', 'delta_pct'))
        pairs = [('directo', 'persiana_omitida'), ('solar_omitida', 'solar_adaptada')]
        if 'directo32_recalculado' in report:
            pairs.append(('directo32_recalculado', 'directo'))
        for base, target in pairs:
            cases = {'origen32': {'indicadores': report[base].get('indicadores', {})},
                     'convertido23': {'indicadores': report[target].get('indicadores', {})}}
            writer.writerows((base, target, *row[2:]) for row in comparisons(cases))
    for name, case in report.items():
        if case.get('destino') or name == 'directo32_recalculado':
            print(name, 'guardado' if case['cex_guardado'] else 'guardado pendiente',
                  'con XML' if case.get('indicadores') else 'XML pendiente',
                  case.get('error_evidencia', ''))
        else:
            print(name, 'sin salida')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modo', choices=('preparar', 'recoger'))
    parser.add_argument('directory', type=Path)
    parser.add_argument('--oficial32', type=Path)
    parser.add_argument('--persiana32', type=Path)
    parser.add_argument('--exportaciones', type=Path)
    args = parser.parse_args()
    if args.modo == 'preparar':
        if args.oficial32 is None:
            parser.error('preparar requiere --oficial32')
        prepare(args.oficial32, args.directory, args.persiana32)
    else:
        collect(args.directory, args.exportaciones or args.directory)
