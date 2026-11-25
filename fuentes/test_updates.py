"""Consulta de versiones sin depender de la red en las pruebas."""
import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'app'))
import converter as c


class UpdateTests(unittest.TestCase):
    def release(self, tag):
        return {'tag_name':tag, 'draft':False, 'prerelease':False,
                'assets':[{'name':'Conversor_CE3X_Windows_'+tag[1:].replace('.', '_')+'.zip',
                           'state':'uploaded', 'size':100}]}

    def check(self, payload):
        with mock.patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(payload).encode())) as fetch:
            result = c.check_updates()
            request = fetch.call_args.args[0]
            self.assertEqual(request.full_url, c.UPDATE_API)
            self.assertIsNone(request.data)
            self.assertEqual(fetch.call_args.kwargs['timeout'], 4)
            return result

    def test_numeric_version_order_and_no_downgrades(self):
        with mock.patch.object(c, 'VERSION', '1.9.0'):
            self.assertEqual(self.check(self.release('v1.10.0')), 'UPDATE\t1.10.0')
            self.assertEqual(self.check(self.release('v1.9.0')), 'CURRENT\t1.9.0')
            self.assertEqual(self.check(self.release('v1.8.5')), 'CURRENT\t1.8.5')

    def test_ignore_drafts_previews_and_missing_packages(self):
        for changed in ({'draft':True}, {'prerelease':True}, {'assets':[]},
                        {'tag_name':'v9.0.0-beta'}, {'tag_name':'v9.0.0\nUPDATE\tmalicious'},
                        {'assets':[{'name':'Conversor_CE3X_Windows_9_0_0.zip','size':1,'state':'new'}]}):
            with self.subTest(changed=changed):
                release = self.release('v9.0.0'); release.update(changed)
                self.assertEqual(self.check(release), 'UNAVAILABLE\t')

    def test_offline_rate_limit_and_invalid_json_are_nonfatal(self):
        for error in (TimeoutError(), OSError('sin conexión')):
            with mock.patch('urllib.request.urlopen', side_effect=error):
                self.assertEqual(c.check_updates(), 'UNAVAILABLE\t')
        for body in (b'not json', b'[]', b'x'*131073):
            with mock.patch('urllib.request.urlopen', return_value=io.BytesIO(body)):
                self.assertEqual(c.check_updates(), 'UNAVAILABLE\t')


class HumanReportTests(unittest.TestCase):
    def test_real_element_names_and_fields_without_internal_paths(self):
        audit = c.Audit(); audit.measure_names[0] = 'Aislar cubierta'
        path = 'medidas_mejora[0].datosNuevoEdificio.datosIniciales.listadoCerramientos[0]'
        audit.subjects[path] = 'Cerramiento "Cubierta de prueba"'
        c.audit_measure_extra(audit, 'datosEdificio.Cerramiento', 'nombreSistemaConstructivo',
                             'Solución de prueba', path+'.nombreSistemaConstructivo', 'Aislar cubierta')
        text = c.describe_losses(audit.losses)
        for name in ('Aislar cubierta', 'Edificio con la mejora', 'Cubierta de prueba', 'solución constructiva'):
            self.assertIn(name, text)
        for internal in ('datosNuevoEdificio', 'listadoCerramientos', 'nombreSistemaConstructivo', 'Modelo |'):
            self.assertNotIn(internal, text)
        self.assertEqual(audit.losses[0]['path'], path+'.nombreSistemaConstructivo')

    def test_duplicate_general_fields_grouped_without_hiding_consequences(self):
        audit = c.Audit()
        for i in (22,23,24,25):
            audit.loss(f'generales[{i}]', str(i), 'Campo general exclusivo de CE3X 3.2',
                       element='Edificio', dependencies='Se conserva la superficie común')
        text = c.describe_losses(audit.losses)
        self.assertEqual(text.count('Se omite:'), 1)
        self.assertIn('4 campos', text)
        self.assertIn('Se conserva la superficie común', text)
        self.assertEqual(len(audit.losses), 4)
