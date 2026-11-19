"""Inspect official teaching examples without executing their serialized objects."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import shutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
import converter as c

SHADOWS_EXAMPLE = 'b57a58f3e639757e6b8576f895cc3f6cfc8abd8952cf3ce22c7238df1da54dba'
SOLAR_EXAMPLE = '8b4ca4dbb37ec646ee9168f9cebe53905285f9693ae79191509d2a94eb31e0aa'


def inspect_examples(directory, report_path):
    directory, report_path = Path(directory).resolve(), Path(report_path).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    examples = sorted(directory.rglob('*.cex'))
    if not examples:
        raise RuntimeError('No se han encontrado ejemplos .cex en el paquete oficial')
    records = []
    for index, source in enumerate(examples):
        if source.stem.endswith('_CE3X2.3'):
            continue
        data = source.read_bytes()
        record = {'file': source.relative_to(directory).as_posix(), 'bytes': len(data),
                  'sha256': hashlib.sha256(data).hexdigest()}
        records.append(record)
        try:
            header = c.InertUnpickler(io.BytesIO(data.replace(b'\r\n', b'\n')), encoding='latin1').load()
            record['header'] = str(header)
            blocks = c.read_cex(source)
            record.update(blocks=len(blocks), envelope_count=len(blocks[3][0]),
                          window_count=len(blocks[3][1]), bridge_count=len(blocks[3][2]),
                          shadow_patterns=len(blocks[9]), shadow_names=c.json_value(blocks[10]),
                          general_surface=c.json_value(blocks[2][6]), general_extra_fields=c.json_value(blocks[2][21:]),
                          improvement_count=len(blocks[5]))
            record['envelope_types']=sorted({str(r[1])+'|'+str(r[-1]) for r in blocks[3][0]})
            record['zones']=[{'class':z.cls.module+'.'+z.cls.name,'fields':sorted(str(k) for k in z.state)}
                             for z in blocks[3][3] if isinstance(z,c.CexObject)]
            if str(header) != 'CE3Xv3.2 Residencial':
                record['conversion'] = 'not_32_residential'
                continue
            fixture_folder = report_path.parent / 'muestras_oficiales'
            fixture_folder.mkdir(exist_ok=True)
            fixture = fixture_folder / (record['sha256'] + '.cex')
            if not fixture.exists(): shutil.copyfile(source, fixture)
            # Only the two hash-pinned teaching examples have an approved omission
            # in this test. Exercise the same preflight and exact token as the UI.
            code, attempt = c.convert(source, c.ROOT / 'plantilla_23.cex')
            record['preflight'] = attempt.manifest['status']
            record['preflight_error'] = attempt.manifest.get('error_code')
            if code == 2 and record['sha256'] in (SHADOWS_EXAMPLE, SOLAR_EXAMPLE):
                if attempt.output.exists():
                    raise RuntimeError('La preinspeccion ha generado salida')
                selected = attempt.manifest['pending_plan']['options']['omit']
                record['loss_count'] = len(selected['losses'])
                code, attempt = c.convert(source, c.ROOT / 'plantilla_23.cex',
                                          solar_choices=selected['choices'], consent=selected['token'])
            record['conversion'] = attempt.manifest['status']
            record['source_unchanged'] = c.sha(source) == record['sha256']
            if code:
                record.update(error_code=attempt.manifest['error_code'],
                              error_path=attempt.manifest['error_path'], error_message=attempt.summary)
                attempt.export_diagnostic(report_path.parent / f'ejemplo_{index:02d}_diagnostico.zip')
            else:
                target = c.read_cex(attempt.output)
                normalized = c.repair_text(blocks, c.Audit(), 'source')
                record.update(output_sha256=c.sha(attempt.output), output_improvement_count=len(target[5]),
                              shadows_preserved=c.typed_value(normalized[9:11]) == c.typed_value(target[9:11]),
                              envelope_preserved=c.typed_value(normalized[3][0]) == c.typed_value(target[3][0]),
                              window_shadow_refs_preserved=
                              [w.state.get('patronSombras') for w in normalized[3][1]] ==
                              [w.state.get('patronSombras') for w in target[3][1]])
        except Exception as exc:
            record.update(inspection_error=type(exc).__name__ + ': ' + str(exc))
    report = {'source_url': 'https://efinova.es/CE3X',
              'installer_url': 'https://www.miteco.gob.es/content/dam/miteco/es/energia/eficiencia/certificacionenergetica/documentosreconocidos/procedimientoscertificacion/ce3x/CE3Xv3.2.zip',
              'installer_archive_sha256': 'd92bea9f25ebd60c30ef9043ffdd3339fc84065eb415b2629b8a77f948f6b9dd',
              'app_version': c.VERSION, 'examples': records}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    expected = [item for item in records if item['sha256']==SHADOWS_EXAMPLE]
    if not expected or not all(item.get('preflight_error')=='E_CONSENT_REQUIRED'
                               and item.get('conversion')=='CONVERSION_CON_OMISIONES'
                               and item.get('source_unchanged') and item.get('shadows_preserved')
                               and item.get('window_shadow_refs_preserved') and item.get('envelope_preserved')
                               and item.get('shadow_patterns')==2 and item.get('output_improvement_count')==3
                               for item in expected):
        raise RuntimeError('Ha fallado la regresion del ejemplo oficial 3.2 con sombras')
    solar = [item for item in records if item['sha256']==SOLAR_EXAMPLE]
    if not solar or not all(item.get('preflight')=='DECISION' and item.get('preflight_error')=='E_SOLAR_DECISION'
                              and item.get('conversion')=='CONVERSION_CON_OMISIONES' and item.get('source_unchanged')
                              and item.get('output_improvement_count')==2 for item in solar):
        raise RuntimeError('La omision solar explicita debe retirar solo el conjunto afectado')


    print(json.dumps(report, ensure_ascii=True, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory')
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    inspect_examples(args.directory, args.report)
