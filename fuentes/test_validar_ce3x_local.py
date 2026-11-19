"""Regression tests for the local validation harness and the observed XML shapes."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
import sys

import test_converter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import validar_ce3x_local as validation


class LocalValidationTests(unittest.TestCase):
    def test_compare_current_and_legacy_xml_by_service_and_unit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / 'target.xml'
            new = root / 'source.xml'
            old.write_text('''<DatosEnergeticosDelEdificio>
                <Demanda><EdificioObjeto><Calefaccion>118.25</Calefaccion>
                <Refrigeracion>0.83</Refrigeracion><Conjunta08>99999999</Conjunta08></EdificioObjeto></Demanda>
                <Consumo><EnergiaPrimariaNoRenovable><Global>189.22</Global></EnergiaPrimariaNoRenovable>
                <EnergiaFinalVectores><GasNatural><ACS>26.53</ACS><Global>157.23</Global></GasNatural>
                </EnergiaFinalVectores></Consumo>
                <EmisionesCO2><Global>40.04</Global></EmisionesCO2>
                <Calificacion><EmisionesCO2><Global>E</Global></EmisionesCO2></Calificacion>
                </DatosEnergeticosDelEdificio>''', encoding='utf-8')
            new.write_text('''<DatosEnergeticosDelEdificio xmlns="urn:example">
                <Indicadores><Demanda><Cal>120</Cal><Ref>0</Ref></Demanda>
                <EnergiaPrimariaNoRenovable><Tot>190</Tot></EnergiaPrimariaNoRenovable>
                <EnergiaFinal><Tot>150</Tot></EnergiaFinal><Emisiones><Tot>42</Tot></Emisiones></Indicadores>
                <Calificacion><Emisiones><Tot>F</Tot></Emisiones></Calificacion>
                </DatosEnergeticosDelEdificio>''', encoding='utf-8')
            cases = {'origen32': {'indicadores': validation.collect_xml(new)},
                     'convertido23': {'indicadores': validation.collect_xml(old)}}
            legacy = cases['convertido23']['indicadores']
            self.assertEqual(legacy['EnergiaFinalPorVectores/GasNatural/Acs'],
                             {'valor': 26.53, 'unidad': 'kWh/m²·año'})
            rows = {row[2]: row[3:] for row in validation.comparisons(cases)}
            self.assertEqual(len(rows), 5)
            self.assertEqual(rows['Indicadores/Demanda/Ref'], ('kWh/m²·año', 0, 0.83, 0.83, None))
            self.assertEqual(rows['Calificacion/Emisiones/Tot'], ('letra', 'F', 'E', None, None))
            self.assertAlmostEqual(rows['Indicadores/Emisiones/Tot'][3], -1.96)
            self.assertNotIn('Indicadores/EnergiaFinal/Tot', rows)

    def test_resume_public_fixture_without_overwriting_the_sources(self):
        fixture = test_converter.ConverterTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        fixture.src[2][22] = '200'
        fixture.source_path.write_bytes(validation.c.encoded(fixture.src))
        before = validation.c.sha(fixture.source_path)
        root = fixture.root / 'ensayo'
        with contextlib.redirect_stdout(io.StringIO()) as log:
            self.assertEqual(validation.prepare(root, fixture.source_path, None), 2)
            session = validation.read_plan(root)
            self.assertFalse((root / 'exportar').exists())
            self.assertEqual(validation.convert(root, session, session['opciones']['omit']), 0)
            session = validation.read_plan(root)
            validation.verify_originals(root, session)
            validation.collect(root, session)
        self.assertIn('Pendiente: guardar', log.getvalue())
        self.assertEqual(validation.c.sha(fixture.source_path), before)
        self.assertTrue((root / 'exportar' / 'convertido23.cex').is_file())
        self.assertTrue((root / 'resumen.json').is_file())
        self.assertFalse(validation.case_evidence(root, 'convertido23')['cex_modificado'])

    def test_matches_improvements_by_name_and_separates_native_reference(self):
        a = {'Indicadores/Emisiones/Tot': {'valor': 40.0, 'unidad': 'kgCO₂/m²·año'},
             'MedidaMejora/A/Indicadores/Emisiones/Tot': {'valor': 30.0, 'unidad': 'kgCO₂/m²·año'}}
        b = {'Indicadores/Emisiones/Tot': {'valor': 38.0, 'unidad': 'kgCO₂/m²·año'},
             'MedidaMejora/B/Indicadores/Emisiones/Tot': {'valor': 31.0, 'unidad': 'kgCO₂/m²·año'}}
        cases = {'origen32': {'indicadores': a}, 'nativo23': {'indicadores': b},
                 'convertido23': {'indicadores': b}}
        rows = validation.comparisons(cases)
        self.assertEqual({(r[0], r[1]) for r in rows}, {('origen32', 'nativo23'), ('nativo23', 'convertido23')})
        self.assertFalse(any('MedidaMejora/A/' in r[2] for r in rows))


if __name__ == '__main__':
    unittest.main()
