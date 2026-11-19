"""Pruebas de regresion autonomas. Integracion opcional con archivos locales."""
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import converter as c

class ConverterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve()
        self.template=c.read_cex(c.ROOT/'plantilla_23.cex')
        self.profile=json.loads((c.ROOT/'profile.json').read_text(encoding='utf-8'))
        self.src=copy.deepcopy(self.template)
        self.src[0]=c.LegacyString('CE3Xv3.2 Residencial')
        self.src[1]=['']*29;self.src[2]+=['']*5;self.src[4]+=[[],[]]
        self.src[2][6]='86.31'
        self.src[3][0]=[['Partición superior','Partición Interior','46.10',1.19,120,'Espacio bajo cubierta inclinada','','Sin patrón','Estimadas',['Ligeramente Ventilado','52.27',False,'El cerramiento','Por defecto'],'','','','Edificio Objeto','horizontal superior']]
        self.src[3][1]=[c.CexObject(c.GlobalRef('Envolvente.objetosEnvolvente','HuecoConocidas'),{
            'descripcion':'Vñ','cerramientoAsociado':'Partición superior','superficie':'2',
            'elementosProteccionSolar':['']*25+[False,'',''],'id':c.CexObject(c.GlobalRef('uuid','UUID'),{'int':123},'reduce'),
            'Uvidrio':1.3,'Umarco':1.3,'Gvidrio':.7,'patronSombras':'Sin patrón'})]
        self.src[4][5]=[['Aerotermia','mixto3',[374.8,275.8,485.4],'Bomba de Calor','Electricidad',[['86.31','100']]*3,'Estimado según Instalación',[['359','487','710'],[True,False,False],[],1],[True,'190','80','60','5.1','Por defecto',''],['','',''],'Edificio Objeto']]
        self.source_path=self.root/'origen.cex';self.template_path=self.root/'nativo.cex'
    def tearDown(self):self.temp.cleanup()
    def fixture_measure(self,name='Placas fotovoltaicas'):
        cls=c.GlobalRef('MedidasDeMejora.objetoGrupoMejoras','grupoMedidasMejora')
        state={key:[] for key in c.mm_schema()[cls.module+'.'+cls.name]}
        state.update(nombre=name,caracteristicas='Instalación',otrosDatos='Amortización',
                     datosEdificioOriginal=None,datosNuevoEdificio=None,ahorro=[0,0,0,0,6.4,33.9],
                     datosInstalaciones=[[] for _ in range(14)],
                     mejoras=[[],['',[[] for _ in range(12)],True]],
                     analisisEconomico=c.CexObject(c.GlobalRef(cls.module,'AnalisisEconomicoConjuntoMM'),{
                         'inversionInicial':[8000.0],'costeMantenimiento':[150.0],'vidaUtil':[30.0],
                         'analisisTeorico':None,'analisisFacturas':None}))
        return c.CexObject(cls,state)
    def test_improvements_and_economic_inputs_preserved(self):
        self.src[5]=[self.fixture_measure(),self.fixture_measure('Aislamiento y aerotermia')]
        self.src[6][2]=[['Instalación','Placas fotovoltaicas','Instalaciones','30','8000','150']]
        self.src[11][:2]=[m.state['nombre'] for m in self.src[5]]
        code,run=self.run_convert();self.assertEqual(code,0)
        dst=c.read_cex(run.output)
        self.assertEqual(len(dst[5]),2)
        self.assertEqual(dst[11][:2],self.src[11][:2]);self.assertEqual(dst[6],self.src[6])
        for a,b in zip(self.src[5],dst[5]):
            for key in ('nombre','caracteristicas','otrosDatos','ahorro'):
                self.assertEqual(a.state[key],b.state[key])
            self.assertEqual(len(b.state['datosInstalaciones']),12)
            self.assertEqual(b.state['analisisEconomico'].state['inversionInicial'],[8000.0])
        manifest=run.manifest
        self.assertEqual(manifest['improvement_count'],2)
        self.assertFalse(manifest['target_results_recalculated'])
    def test_improvement_new_generator_rejected(self):
        measure=self.fixture_measure();measure.state['listadoGeneradoresElectricoMM']=[['generador nuevo']]
        self.src[5]=[measure];self.assertFailure('E_MM_GENERATOR')
    def test_automatic_repair_improvement_names_and_report_links(self):
        name='Aislamiento a\\xf1adido y partici\\u00f3n'
        self.src[5]=[self.fixture_measure(name)];self.src[11][0]=name
        code,run=self.run_convert();self.assertEqual(code,0)
        dst=c.read_cex(run.output)
        self.assertEqual(dst[5][0].state['nombre'],'Aislamiento añadido y partición')
        self.assertEqual(dst[11][0],dst[5][0].state['nombre'])
    def test_improvement_unknown_class_rejected(self):
        measure=self.fixture_measure();measure.state['datosNuevoEdificio']=c.CexObject(c.GlobalRef('models','Nuevo'))
        self.src[5]=[measure];self.assertFailure('E_MM_CLASS')
    def test_unknown_measure_not_silently_dropped(self):
        measure=self.fixture_measure();measure.state['mejoras'][0]=[['medida','Tipo nuevo',[]]]
        self.src[5]=[measure];self.assertFailure('E_MM_DEFINITION')
    def test_improvement_numeric_input_conversion(self):
        definition=[['Aislamiento','Adición de Aislamiento Térmico',[True,False,False,True,False,False,'0.27','','','',True,['0.01']*7,[False]*4]]]
        got=c.adapt_measure_definitions(definition,c.Audit(self.root),'medida')
        self.assertIsInstance(got[0][2][6],float);self.assertEqual(got[0][2][6],.27)
        self.assertEqual(definition[0][2][6],'0.27')
    def test_pv_contribution_native_type_and_energy_preserved(self):
        self.src[4][6]=[['Fotovoltaica','renovable',['','','',False],['632.3','','','','',''],[False,True],'Edificio Objeto']]
        code,run=self.run_convert();self.assertEqual(code,0)
        pv=c.read_cex(run.output)[4][6][0]
        self.assertEqual(pv[1],'Contribuciones energéticas');self.assertEqual(pv[3][0],'632.3')
    def test_repair_text_cycles_sharing_and_capital_accents(self):
        ob=c.CexObject(c.GlobalRef('datosEdificio','datosEdificio'))
        shared=[c.LegacyString('A\\u00d1O \\xDC \\xC1 \\u00fc')]
        ob.state={'parent':ob,'a':shared,'b':shared}
        fixed=c.repair_text(ob,c.Audit(self.root),'root')
        self.assertIs(fixed.state['parent'],fixed);self.assertIs(fixed.state['a'],fixed.state['b'])
        self.assertEqual(fixed.state['a'][0],'AÑO Ü Á ü')
        self.assertIsInstance(fixed.state['a'][0],c.LegacyString)
    def test_repair_key_collision_stops_conversion(self):
        with self.assertRaises(c.ConversionError) as ctx:
            c.repair_text({'Partición':1,'Partici\\xf3n':2},c.Audit(self.root),'root')
        self.assertEqual(ctx.exception.code,'E_TEXT_COLLISION')
    def run_convert(self,fix=False,source=None):
        self.source_path.write_bytes(c.encoded(source or self.src));self.template_path.write_bytes(c.encoded(self.template))
        return c.convert(self.source_path,self.template_path,fix_accents=fix)
    def assertFailure(self,code,source=None):
        status,run=self.run_convert(source=source)
        self.assertEqual(status,1);r=run.manifest
        self.assertEqual(r['error_code'],code);self.assertFalse((run.output).exists())
        self.assertTrue(run.traceback_text);self.assertFalse(list(self.root.glob('*.zip')))
    def accept(self, analysis, option='omit'):
        selected = analysis.manifest['pending_plan']['options'][option]
        return c.convert(self.source_path, self.template_path, solar_choices=selected['choices'],
                         consent=selected['token'])
    def test_roundtrip_accent_string_unicode(self):c.self_test()
    def test_scanner_latin1_raw_and_escaped(self):
        for literal in (b"S'Partici\xf3n y ni\xf1o'\n.", b"S'Partici\\xf3n y ni\\xf1o'\n."):
            ops=list(c.protocol0_ops(literal))
            self.assertEqual(ops[0][1],'Partición y niño')
            self.assertEqual(ops[-1][2],len(literal)-1)
    def test_python311_ascii_reader_never_used_for_string(self):
        # Reproduce el lector ASCII de pickletools 3.11, incluso con \xf1 escapado.
        def ascii_reader(stream):
            return c.codecs.escape_decode(c.pickletools.read_stringnl(stream,decode=False))[0].decode('ascii')
        descriptor=c.pickletools.code2op['S'].arg
        with mock.patch.object(descriptor,'reader',ascii_reader):
            with self.assertRaises(UnicodeDecodeError):
                list(c.pickletools.genops(b"S'ni\\xf1o'\n."))
            self.src[6][0]=[c.LegacyString('Año: partición, patrón y aislamiento')]
            code,run=self.run_convert()
            self.assertEqual(code,0,str(run.manifest))
            dst=c.read_cex(run.output)
            self.assertEqual(dst[5],[])
            self.assertEqual(dst[3][0][0][0],'Partición superior')
    def test_scanner_rejects_binary_before_reading_payload(self):
        with self.assertRaises(c.ConversionError) as ctx:
            list(c.protocol0_ops(b"S'ok'\nB"))
        self.assertEqual(ctx.exception.code,'E_PROTOCOL')
    def test_scanner_rejects_bad_string_quotes_and_truncation(self):
        for raw in (b"S'ni\\xf1o\n.",b"S'ni\\xf1o'",b"S'ok'\n"):
            with self.assertRaises((ValueError,c.ConversionError)):
                list(c.protocol0_ops(raw))
    def test_roundtrip_cyclic_cache(self):
        obj=c.CexObject(c.GlobalRef('datosEdificio','datosEdificio'))
        obj.state['self']=obj
        obj.state['shared']=[obj,obj]
        raw=c.encoded([obj]);other=c.InertUnpickler(io.BytesIO(raw.replace(b'\r\n',b'\n')),encoding='latin1').load()
        self.assertEqual(c.typed_value(obj),c.typed_value(other))
        self.assertIs(other.state['self'],other)
    def test_preserves_inst_style(self):
        raw=c.encoded([self.src[3][1][0]])
        self.assertIn(b'(iEnvolvente.objetosEnvolvente\nHuecoConocidas'.replace(b'\n',b'\r\n'),raw)
    def test_succeeds_preserves_thermal_values(self):
        status,run=self.run_convert();self.assertEqual(status,0)
        dst=c.read_cex(run.output)
        self.assertEqual(dst[3][0],self.src[3][0]);self.assertEqual(dst[4][5][0][2],[374.8,275.8,485.4])
        self.assertEqual(dst[4][5][0][6],'Estimado según Instalación')
        self.assertEqual(len(dst[4][5][0]),10);self.assertEqual(dst[4][5][0][8],self.src[4][5][0][8])
        self.assertEqual(dst[3][1][0].cls,self.src[3][1][0].cls)
        self.assertNotIn('id',dst[3][1][0].state)
        self.assertEqual(len(dst[3][1][0].state['elementosProteccionSolar']),25)
    def test_template_does_not_replace_systems(self):
        self.template[4][5]=[['equipo de otra vivienda','mixto3',[1,2,3]]]
        status,run=self.run_convert();self.assertEqual(status,0)
        dst=c.read_cex(run.output);self.assertEqual(dst[4][5][0][0],'Aerotermia')
    def test_input_hashes_unchanged(self):
        status,run=self.run_convert();r=run.manifest
        self.assertEqual(r['source_sha256'],c.sha(self.source_path));self.assertEqual(r['template_sha256'],c.sha(self.template_path))
    def test_two_runs_never_overwrite(self):
        _,a=self.run_convert();before=a.output.read_bytes();code,b=self.run_convert();self.assertEqual(code,1);self.assertEqual(b.manifest['error_code'],'E_OUTPUT_EXISTS');self.assertEqual(a.output.read_bytes(),before)
    def test_wrong_version(self):
        src=copy.deepcopy(self.src);src[0]='CEXv2.3 Residencial';self.assertFailure('E_SOURCE_VERSION',src)
    def test_active_new_system_group(self):
        src=copy.deepcopy(self.src);src[4][13]=[['nuevo']];self.assertFailure('E_NEW_SYSTEM',src)
    def blind_fixture(self):
        state=self.src[3][1][0].state
        state.update(elementosProteccionSolar=['']*6+[['',0,0],['',0,0],'',False,False,'',False,False,'','','',False,False,False,False,False,False,False,['',''],True,'Manuales','Blanco'],
                     tieneProteccionSolar=True,correctorFSCTE=.19575,correctorFSInvierno=1.0,correctorFSVerano=.19575)
    def test_new_window_protection_requires_explicit_decision(self):
        self.blind_fixture();code,run=self.run_convert();self.assertEqual(code,2);self.assertFalse(run.output.exists())
        self.assertEqual(run.manifest['pending_solar']['id'],'window-protection:building')
        self.assertTrue(run.manifest['pending_solar']['candidate']['experimental'])
    def test_omit_new_window_protection_resets_only_solar_properties(self):
        self.blind_fixture();windows=self.src[3][1];self.partition_fixture();self.src[3][1]=windows
        self.src[3][1][0].state['cerramientoAsociado']=self.src[3][0][0][0]
        self.source_path.write_bytes(c.encoded(self.src));before=self.source_path.read_bytes()
        code,analysis=c.convert(self.source_path,c.ROOT/'plantilla_23.cex')
        self.assertEqual(code,2,analysis.summary)
        selected=analysis.manifest['pending_plan']['options']['omit']
        code,run=c.convert(self.source_path,c.ROOT/'plantilla_23.cex',solar_choices=selected['choices'],consent=selected['token'])
        self.assertEqual(code,0,run.summary);dst=c.read_cex(run.output);state=dst[3][1][0].state
        self.assertEqual(len(state['elementosProteccionSolar']),25);self.assertFalse(state['tieneProteccionSolar'])
        for key in ('correctorFSCTE','correctorFSInvierno','correctorFSVerano'):self.assertEqual(state[key],1.0)
        self.assertEqual(c.json_value(dst[3][0]),c.json_value(self.src[3][0]));self.assertEqual(dst[3][2],self.src[3][2])
        self.assertEqual(self.source_path.read_bytes(),before)
        self.assertTrue(run.manifest['results_require_recalculation'])
    def test_new_window_protection_combined_shading_stays_blocked(self):
        self.blind_fixture();self.src[3][1][0].state['elementosProteccionSolar'][0]='1.5';self.assertFailure('E_ACTIVE_SOLAR')
    def test_window_protection_with_improvements_stays_blocked(self):
        self.blind_fixture();self.src[5]=[self.fixture_measure()];self.assertFailure('E_ACTIVE_SOLAR')
    def test_window_protection_cannot_be_adapted_silently(self):
        self.blind_fixture();self.source_path.write_bytes(c.encoded(self.src))
        code,run=c.convert(self.source_path,c.ROOT/'plantilla_23.cex',solar_choices={'window-protection:building':'adapt'})
        self.assertEqual(code,1);self.assertEqual(run.manifest['error_code'],'E_SOLAR_SCOPE');self.assertFalse(run.output.exists())
    def test_observed_ce3x_blind_needs_consent_and_keeps_window_thermal_values(self):
        evidence = json.loads((Path(__file__).parent/'fixtures'/'persiana_ce3x.json').read_text(encoding='utf-8'))
        source = self.src[3][1][0].state
        source.update(evidence['estado_32'])
        self.assertNotEqual(source['correctorFSCTE'], evidence['estado_23']['correctorFSCTE'])
        code, plan = self.run_convert()
        self.assertEqual(code, 2, plan.summary)
        self.assertEqual(set(plan.manifest['pending_plan']['options']), {'omit', 'experimental'})
        code, result = self.accept(plan)
        self.assertEqual(code, 0, result.summary)
        target = c.read_cex(result.output)[3][1][0].state
        for key in ('Gvidrio','Uvidrio','Umarco','superficie','cerramientoAsociado'):
            self.assertEqual(target[key], source[key])
        self.assertEqual(target['correctorFSVerano'], 1.0)
        self.assertEqual(c.sha(self.source_path), plan.manifest['source_sha256'])
        result.output.unlink()
        code, result = self.accept(plan, 'experimental')
        self.assertEqual(code, 0, result.summary)
        target = c.read_cex(result.output)[3][1][0].state
        self.assertEqual({key:target[key] for key in evidence['estado_23']}, evidence['estado_23'])
        self.assertIn('experimental', result.manifest['decision_summary'])

    def test_window_protection_cancel_does_not_write(self):
        self.blind_fixture();self.source_path.write_bytes(c.encoded(self.src));inp=io.StringIO(json.dumps({'command':'convert','source':str(self.source_path)})+'\n'+json.dumps({'command':'decision','id':'window-protection:building','choice':'cancel'})+'\n');out=io.StringIO()
        c.serve(inp,out);self.assertIn('DECISION_EXPERIMENTAL',out.getvalue());self.assertIn('CANCELADO',out.getvalue());self.assertFalse(c.output_path(self.source_path).exists())

    def test_manual_blind_reuses_stored_factors_regardless_of_color(self):
        self.blind_fixture()
        state = self.src[3][1][0].state
        state['correctorFSInvierno'] = 0.84
        state['correctorFSVerano'] = 0.27
        for color in ('Blanco', 'Oscuro', 'Gris'):
            with self.subTest(color=color):
                state['elementosProteccionSolar'][27] = color
                code, plan = self.run_convert()
                self.assertEqual(code, 2, plan.summary)
                code, result = self.accept(plan, 'experimental')
                self.assertEqual(code, 0, result.summary)
                converted = c.read_cex(result.output)[3][1][0].state
                self.assertEqual(converted['elementosProteccionSolar'][23:], [True, ['0.84', '0.27']])
                self.assertEqual(converted['correctorFSCTE'], 1)
                self.assertIn(color, result.manifest['decision_summary'])
                result.output.unlink()

    def test_blind_with_unknown_control_stays_omission_only(self):
        self.blind_fixture()
        self.src[3][1][0].state['elementosProteccionSolar'][26] = 'Automáticas'
        code, plan = self.run_convert()
        self.assertEqual(code, 2, plan.summary)
        self.assertNotIn('experimental', plan.manifest['pending_plan']['options'])
    def test_active_new_solar_option(self):
        src=copy.deepcopy(self.src);src[3][1][0].state['elementosProteccionSolar'][-1]='activo';self.assertFailure('E_ACTIVE_SOLAR',src)
    def test_new_general_field(self):
        src=copy.deepcopy(self.src);src[2][25]={'nuevo':'objeto'};self.assertFailure('E_NEW_GENERAL',src)
    def test_source_schema(self):
        src=copy.deepcopy(self.src);src[1].append('extra');self.assertFailure('E_SOURCE_SCHEMA',src)
    def partition_fixture(self):
        rows=json.loads((Path(__file__).parent/'fixtures/particiones_oficiales_23.json').read_text(encoding='utf-8'))['rows']
        self.src[3]=[copy.deepcopy(rows),[],[],[]]
        return rows
    def test_official_native_23_vertical_and_lower_partitions_preserved(self):
        rows=self.partition_fixture();code,run=self.run_convert();self.assertEqual(code,0,run.summary)
        dst=c.read_cex(run.output)
        self.assertEqual(c.json_value(dst[3][0]),rows)
        self.assertEqual(len(dst[3][0]),6)
        self.assertEqual({r[-1] for r in dst[3][0]},{'vertical','horizontal inferior'})
    def test_partition_known_and_estimated_payloads_preserved(self):
        self.src[3][1]=[]
        cases=[('vertical',['Poco Ventilado','50',True,'Ambos','Por defecto']),
               ('horizontal inferior',['Cámara Sanitaria','50',False,'El cerramiento','Por defecto'])]
        for contact,details in cases:
            with self.subTest(contact=contact):
                row=['Particion '+contact,'Partición Interior','23.45',0.55,60.0,'','','Sin patrón','Estimadas',details,'9.38','2.5','','Edificio Objeto',contact]
                self.src[3][0]=[row];code,run=self.run_convert();self.assertEqual(code,0,run.summary)
                self.assertEqual(c.json_value(c.read_cex(run.output)[3][0]),[row]);run.output.unlink()
    def test_partition_wrong_record_length_still_rejected(self):
        self.partition_fixture();self.src[3][0][0].insert(5,'campo desconocido');self.assertFailure('E_ENVELOPE_ROW',self.src)
    def test_unknown_partition_contact_still_rejected(self):
        self.partition_fixture();self.src[3][0][0][-1]='inclinado desconocido';self.assertFailure('E_ENVELOPE_UNKNOWN',self.src)
    def test_catalog_matches_all_native_23_panel_layouts(self):
        evidence=json.loads((Path(__file__).parent/'fixtures/envolvente_nativa_23.json').read_text(encoding='utf-8'))
        self.assertEqual(self.profile['envelope_lengths'],evidence['layouts'])
        self.assertEqual(self.profile['envelope_lengths']['Cubierta|terreno'],16)
    def test_all_ten_envelope_types_preserved(self):
        fixtures=[
            ['Fachada aire','Fachada','20',1.4,200,'Norte','','Sin patrón','Por defecto',[],'8','2.5','1','Edificio Objeto','aire'],
            ['Medianeria','Fachada','20',0,200,'','','Sin patrón','8','2.5','1','Edificio Objeto','edificio'],
            ['Muro enterrado','Fachada','20',1.4,200,'1','','Sin patrón','Conocidas',['1.4'],'8','2.5','1','Edificio Objeto','terreno'],
            ['Cubierta aire','Cubierta','20',1.0,344,'Techo','','Sin patrón','Por defecto',['Cubierta plana'],'5','4','1','Edificio Objeto','aire'],
            ['Cubierta enterrada','Cubierta','20',1.0,344,'Techo','','Sin patrón','Conocidas',['1.0'],'5','4','1','0.5','Edificio Objeto','terreno'],
            ['Suelo aire','Suelo','20',1.0,344,'Suelo','','Sin patrón','Conocidas',['1.0'],'5','4','1','Edificio Objeto','aire'],
            ['Suelo terreno','Suelo','20',1.0,750,'Suelo','','Sin patrón','Por defecto',True,'',[],'5','4','1','Edificio Objeto','terreno'],
        ]
        rows=json.loads((Path(__file__).parent/'fixtures/particiones_oficiales_23.json').read_text(encoding='utf-8'))['rows']
        fixtures += [copy.deepcopy(next(r for r in rows if r[-1]==contact)) for contact in ('vertical','horizontal inferior')]
        fixtures += [copy.deepcopy(self.src[3][0][0])]
        self.src[3]=[fixtures,[],[],[]]
        code,run=self.run_convert();self.assertEqual(code,0,run.summary)
        dst=c.read_cex(run.output);self.assertEqual(c.json_value(dst[3][0]),fixtures)
        self.assertEqual(len({(r[1],r[-1]) for r in dst[3][0]}),10)
        self.assertEqual(len(self.profile['envelope_lengths']),10)
    def test_native_nested_zones_preserved(self):
        zone=lambda name,parent,area:c.CexObject(c.GlobalRef('ventanaSubgrupo','claseZona'),
             {'nombre':name,'raiz':parent,'tipo':'Subgrupo','superficie':area})
        self.src[3][3]=[zone('Planta baja','Edificio Objeto','80'),zone('Vivienda','Planta baja','46.10')]
        self.src[3][0][0][-2]='Vivienda';self.src[3][1][0].state['subgrupo']='Vivienda'
        code,run=self.run_convert();self.assertEqual(code,0,run.summary)
        dst=c.read_cex(run.output)
        self.assertEqual(c.typed_value(dst[3][3]),c.typed_value(self.src[3][3]))
        self.assertEqual(dst[3][0][0][-2],'Vivienda');self.assertEqual(dst[3][1][0].state['subgrupo'],'Vivienda')
    def test_zones_inside_improvement_graph_preserved(self):
        zone=c.CexObject(c.GlobalRef('ventanaSubgrupo','claseZona'),
            {'nombre':'Zona propia','raiz':'Edificio Objeto','tipo':'Subgrupo','superficie':'45'})
        state={key:[] for key in c.mm_schema()['datosEdificio.datosEdificio']}
        state.update(datosGenerales=copy.deepcopy(self.src[2]),datosInstalaciones=[[] for _ in range(14)],subgrupos=[zone])
        measure=self.fixture_measure();measure.state['datosEdificioOriginal']=c.CexObject(c.GlobalRef('datosEdificio','datosEdificio'),state);self.src[5]=[measure]
        code,run=self.run_convert();self.assertEqual(code,0,run.summary)
        out=c.read_cex(run.output)[5][0].state['datosEdificioOriginal'].state['subgrupos'][0]
        self.assertEqual(c.typed_value(out),c.typed_value(zone))
    def test_unknown_envelope(self):
        src=copy.deepcopy(self.src);src[3][0][0][-1]='nuevo contacto';self.assertFailure('E_ENVELOPE_UNKNOWN',src)
    def test_unknown_system_shape(self):
        src=copy.deepcopy(self.src);src[4][5][0].append('nuevo');self.assertFailure('E_SYSTEM_ROW',src)
    def test_orphan_window(self):
        src=copy.deepcopy(self.src);src[3][1][0].state['cerramientoAsociado']='ausente';self.assertFailure('E_WINDOW_REFERENCE',src)
    def test_duplicate_envelope(self):
        src=copy.deepcopy(self.src);src[3][0].append(copy.deepcopy(src[3][0][0]));self.assertFailure('E_DUPLICATE',src)
    def test_invalid_number(self):
        src=copy.deepcopy(self.src);src[2][6]='nan';self.assertFailure('E_NUMBER',src)
    def test_reset_addons_preserves_economics(self):
        src=copy.deepcopy(self.src);src[6][0]=[['factura original',123]];src[12]={'Isover':'resultado viejo'}
        code,plan=self.run_convert(source=src)
        self.assertEqual(code,2,plan.summary)
        self.assertEqual([x['element'] for x in plan.audit.losses],['Isover'])
        code,run=self.accept(plan)
        self.assertEqual(code,0,run.summary)
        dst=c.read_cex(run.output)
        self.assertEqual(dst[6],src[6]);self.assertEqual(dst[12],{})
    def test_truncated_file_diagnostic(self):
        self.source_path.write_bytes(c.encoded(self.src)[:300]);self.template_path.write_bytes(c.encoded(self.template))
        code,run=c.convert(self.source_path,self.template_path);self.assertEqual(code,1)
        self.assertTrue(run.audit.events);self.assertFalse(run.output.exists());self.assertFalse(list(self.root.glob('*.log')))
    def test_refuse_nontext_format(self):
        self.source_path.write_bytes(b'\x80\x04N.');self.template_path.write_bytes(c.encoded(self.template))
        code,run=c.convert(self.source_path,self.template_path);self.assertEqual(code,1)
    def test_literal_accents_opt_in(self):
        src=copy.deepcopy(self.src)
        src[3][0][0][0]='Partici\\xf3n superior';src[3][0][0][1]='Partici\\xf3n Interior'
        src[3][1][0].state['cerramientoAsociado']='Partici\\xf3n superior'
        self.src=src;code,run=self.run_convert(fix=True);self.assertEqual(code,0)
        dst=c.read_cex(run.output);self.assertEqual(dst[3][0][0][0],'Partición superior')
        changes=run.audit.changes;self.assertTrue(any(x['code']=='FIX_ACCENT_ESCAPE' for x in changes))
    def test_automatic_literal_rewrite_even_with_false_legacy_flag(self):
        src=copy.deepcopy(self.src);src[3][1][0].state['descripcion']='V\\xf1'
        _,run=self.run_convert(source=src);dst=c.read_cex(run.output);self.assertEqual(dst[3][1][0].state['descripcion'],'Vñ')
    def test_inert_global_never_imports(self):
        r=c.InertUnpickler(io.BytesIO(b'cos\nsystem\n.'),encoding='latin1').load()
        self.assertEqual(r,c.GlobalRef('os','system'))
    def test_constructor_with_args_rejected(self):
        with self.assertRaises(c.ConversionError):c.InertUnpickler(io.BytesIO(b"(S'argumento'\nios\nsystem\n."),encoding='latin1').load()
    def test_diagnostic_export_includes_requested_evidence(self):
        _,run=self.run_convert();log=self.root/'cex.log';log.write_text('Error: partición',encoding='utf-8')
        path=run.export_diagnostic(self.root/'diagnostico.zip',notes='Al editar Partición superior',attachment=log)
        with zipfile.ZipFile(path) as z:
            observation=json.loads(z.read('errores_CE3X/observacion.json'))
            self.assertEqual(observation['notes'],'Al editar Partición superior')
            self.assertEqual(z.read('errores_CE3X/adjunto.log').decode(),'Error: partición')
            self.assertEqual(json.loads(z.read('resultado.json'))['status'],'REVISAR')
            self.assertIn('ROUNDTRIP_OK',z.read('conversion.log').decode())
        self.assertFalse((self.root/'errores_CE3X').exists())
    def test_snapshots_exclude_personal_blocks_and_images(self):
        self.src[1][0]='PERSONAL_SECRETO';self.src[2][17]='IMAGEN_BASE64_SECRETA'
        _,run=self.run_convert();snapshot=run.artifacts['modelo_origen_tecnico.json']
        self.assertNotIn('PERSONAL_SECRETO',snapshot);self.assertNotIn('IMAGEN_BASE64_SECRETA',snapshot)

    def test_decimal_roundtrip(self):
        fixture=[c.Decimal('0.1234567890123456789'),c.Decimal('123.00')]
        raw=c.encoded([fixture])
        other=c.InertUnpickler(io.BytesIO(raw.replace(b'\r\n',b'\n')),encoding='latin1').load()
        self.assertEqual(c.typed_value(fixture),c.typed_value(other))
    def test_decimal_nonfinite_rejected(self):
        raw=b"cdecimal\nDecimal\n(VNaN\ntR."
        with self.assertRaises(c.ConversionError):c.InertUnpickler(io.BytesIO(raw),encoding='latin1').load()
    def test_new_general_scalars_recorded(self):
        self.src[2][21:]=['','86.31','1','0','2']
        code,run=self.run_convert();self.assertEqual(code,2)
        self.assertFalse(run.output.exists())
        self.assertEqual({x['path']:x['value'] for x in run.audit.losses},
                         {'generales[22]':'86.31','generales[23]':'1','generales[24]':'0','generales[25]':'2'})
        self.assertEqual(self.accept(run)[0],0)
    def test_new_area_is_recorded_without_replacing_legacy_area(self):
        self.src[2][22]='200'
        code, analysis = self.run_convert()
        self.assertEqual(code, 2, analysis.summary)
        code, attempt = self.accept(analysis)
        self.assertEqual(code, 0, attempt.summary)
        target = c.read_cex(attempt.output)
        self.assertEqual(target[2][6], '86.31')
        self.assertTrue(any(item['path']=='generales[22]' and item['value']=='200'
                            for item in attempt.audit.omitted))
    def test_unknown_target_class_rejected(self):
        self.src[8].append(c.CexObject(c.GlobalRef('models','Material'),{'nombre':'nuevo'}))
        self.assertFailure('E_TARGET_CLASS')
    def test_window_thermal_corruption_detected(self):
        audit=c.Audit(self.root)
        dst=c.transfer(self.src,self.template,self.profile,audit)
        dst[3][1][0].state['Uvidrio']=99
        with self.assertRaises(c.ConversionError):c.compare_windows(self.src,dst,self.profile)
    def test_fix_accents_does_not_disable_preservation(self):
        audit=c.Audit(self.root);dst=c.transfer(self.src,self.template,self.profile,audit,True)
        dst[3][0][0][3]=99
        with self.assertRaises(c.ConversionError):c.check_preservation(self.src,dst,True)
    def test_syntax_roundtrip_all_spanish_accents(self):
        text='áéíóúüñ ÁÉÍÓÚÜÑ Partición Interior Sin patrón C:\\prueba'
        raw=c.encoded([[text,c.LegacyString(text)]])
        other=c.InertUnpickler(io.BytesIO(raw.replace(b'\r\n',b'\n')),encoding='latin1').load()
        self.assertEqual(c.typed_value(other),c.typed_value([text,c.LegacyString(text)]))

    def test_extra_empty_report_field_removed(self):
        self.src[11].append('')
        code,run=self.run_convert();self.assertEqual(code,0)
        self.assertEqual(len(c.read_cex(run.output)[11]),7)
    def test_extra_active_report_field_rejected(self):
        self.src[11].append('datos nuevos');self.assertFailure('E_REPORT_FIELDS')

    def test_success_creates_only_named_output_beside_source(self):
        self.source_path = self.root / 'Vivienda con tildes á.ensayo.cex'
        self.source_path.write_bytes(c.encoded(self.src))
        self.template_path.write_bytes(c.encoded(self.template))
        before = set(self.root.iterdir())
        code, attempt = c.convert(self.source_path, self.template_path)
        self.assertEqual(code, 0, attempt.summary)
        self.assertEqual(attempt.output, self.root / 'Vivienda con tildes á.ensayo_CE3X2.3.cex')
        self.assertEqual(set(self.root.iterdir()) - before, {attempt.output})

    def test_failed_conversion_creates_no_files(self):
        self.source_path.write_bytes(b'not a cex')
        self.template_path.write_bytes(c.encoded(self.template))
        before = set(self.root.iterdir())
        code, attempt = c.convert(self.source_path, self.template_path)
        self.assertEqual(code, 1)
        self.assertTrue(attempt.traceback_text)
        self.assertEqual(set(self.root.iterdir()), before)
        self.assertFalse(attempt.output.exists())

    def test_error_export_is_explicit_and_contains_traceback(self):
        self.source_path.write_bytes(b'not a cex')
        self.template_path.write_bytes(c.encoded(self.template))
        _, attempt = c.convert(self.source_path, self.template_path)
        destination = self.root / 'error.zip'
        self.assertFalse(destination.exists())
        attempt.export_diagnostic(destination)
        with zipfile.ZipFile(destination) as archive:
            self.assertIn('E_FORMAT', archive.read('traceback.txt').decode())
            self.assertEqual(json.loads(archive.read('resultado.json'))['status'], 'ERROR')
        self.assertFalse(list(self.root.glob('*.log')))
        self.assertFalse(list(self.root.glob('*.partial')))

    def test_existing_output_requires_explicit_overwrite(self):
        self.source_path.write_bytes(c.encoded(self.src))
        self.template_path.write_bytes(c.encoded(self.template))
        target = c.output_path(self.source_path)
        target.write_bytes(b'previous conversion')
        code, attempt = c.convert(self.source_path, self.template_path)
        self.assertEqual(code, 1)
        self.assertEqual(attempt.manifest['error_code'], 'E_OUTPUT_EXISTS')
        self.assertEqual(target.read_bytes(), b'previous conversion')
        code, attempt = c.convert(self.source_path, self.template_path, overwrite=True)
        self.assertEqual(code, 0, attempt.summary)
        self.assertEqual(len(c.read_cex(target)), 15)

    def test_failed_overwrite_preserves_previous_output(self):
        self.source_path.write_bytes(b'not a cex')
        self.template_path.write_bytes(c.encoded(self.template))
        target = c.output_path(self.source_path)
        target.write_bytes(b'previous conversion')
        code, _ = c.convert(self.source_path, self.template_path, overwrite=True)
        self.assertEqual(code, 1)
        self.assertEqual(target.read_bytes(), b'previous conversion')

    def test_roundtrip_failure_leaves_no_partial_output(self):
        self.source_path.write_bytes(c.encoded(self.src))
        self.template_path.write_bytes(c.encoded(self.template))
        before = set(self.root.iterdir())
        reader = c.read_cex
        def damaged(path, *args):
            value = reader(path, *args)
            if str(path).endswith('.partial'):
                value[2][6] = '999999'
            return value
        with mock.patch.object(c, 'read_cex', side_effect=damaged):
            code, attempt = c.convert(self.source_path, self.template_path)
        self.assertEqual(code, 1)
        self.assertEqual(attempt.manifest['error_code'], 'E_ROUNDTRIP')
        self.assertEqual(set(self.root.iterdir()), before)

    def test_changed_input_is_rejected_before_output_publication(self):
        self.source_path.write_bytes(c.encoded(self.src))
        self.template_path.write_bytes(c.encoded(self.template))
        before = set(self.root.iterdir())
        real_sha = c.sha
        seen = 0
        def changing(path):
            nonlocal seen
            if Path(path) == self.source_path:
                seen += 1
                if seen > 1:
                    return 'changed'
            return real_sha(path)
        with mock.patch.object(c, 'sha', side_effect=changing):
            code, attempt = c.convert(self.source_path, self.template_path)
        self.assertEqual(code, 1)
        self.assertEqual(attempt.manifest['error_code'], 'E_INPUT_CHANGED')
        self.assertEqual(set(self.root.iterdir()), before)

    def test_diagnostic_collision_preserves_previous_zip(self):
        _, attempt = self.run_convert()
        destination = self.root / 'diagnostico.zip'
        destination.write_bytes(b'existing diagnostic')
        with self.assertRaises(FileExistsError):
            attempt.export_diagnostic(destination)
        self.assertEqual(destination.read_bytes(), b'existing diagnostic')
        self.assertFalse(list(self.root.glob('*.partial')))

    def test_missing_attachment_does_not_create_diagnostic(self):
        _, attempt = self.run_convert()
        destination = self.root / 'diagnostico.zip'
        with self.assertRaises(c.ConversionError):
            attempt.export_diagnostic(destination, attachment=self.root / 'missing.log')
        self.assertFalse(destination.exists())

    def test_persistent_worker_exports_error_only_on_request(self):
        self.source_path.write_bytes(b'invalid')
        self.template_path.write_bytes(c.encoded(self.template))
        destination = self.root / 'error.zip'
        commands = [
            {'command': 'convert', 'source': str(self.source_path), 'template': str(self.template_path)},
            {'command': 'diagnostic', 'destination': str(destination), 'notes': 'Error con eñe y "comillas"\nAl abrir CE3X'},
            {'command': 'exit'},
        ]
        responses = io.StringIO()
        c.serve(io.StringIO(''.join(json.dumps(item) + '\n' for item in commands)), responses)
        lines = responses.getvalue().splitlines()
        self.assertTrue(lines[0].startswith('ERROR\t'))
        self.assertTrue(lines[1].startswith('GUARDADO\t'))
        with zipfile.ZipFile(destination) as archive:
            self.assertEqual(json.loads(archive.read('errores_CE3X/observacion.json'))['notes'], commands[1]['notes'])
        self.assertFalse(list(self.root.glob('*.log')))

    def test_worker_rejects_export_without_a_conversion(self):
        destination = self.root / 'no.zip'
        response = io.StringIO()
        c.serve(io.StringIO(json.dumps({'command': 'diagnostic', 'destination': str(destination)}) + '\n'), response)
        self.assertIn('Primero realiza una conversion', response.getvalue())
        self.assertFalse(destination.exists())

    def test_worker_subprocess_handles_unicode_paths_without_logs(self):
        import subprocess
        self.source_path = self.root / 'Origen á ñ.cex'
        self.source_path.write_bytes(c.encoded(self.src))
        self.template_path.write_bytes(c.encoded(self.template))
        commands = [{'command': 'convert', 'source': str(self.source_path), 'template': str(self.template_path)},
                    {'command': 'exit'}]
        result = subprocess.run([sys.executable, '-I', '-X', 'utf8', '-B', '-u', str(c.ROOT / 'converter.py'), 'serve'],
                                input=''.join(json.dumps(item) + '\n' for item in commands),
                                capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith('REVISAR\t'), result.stdout)
        self.assertIn('Origen á ñ_CE3X2.3.cex', result.stdout)
        self.assertEqual(set(self.root.iterdir()), {self.source_path, self.template_path, c.output_path(self.source_path)})


    def test_shadow_patterns_and_element_references_are_preserved(self):
        # Exact polygons and coefficients from the official 3.2 teaching example.
        fixture = Path(__file__).parent / 'fixtures/sombras_oficiales.json'
        self.src[9] = json.loads(fixture.read_text(encoding='utf-8'))['patterns']
        self.src[10] += ['Sombra Oeste','Sombra Sur']
        self.src[3][0][0][7] = 'Sombra Sur'
        self.src[3][1][0].state['patronSombras'] = 'Sombra Oeste'
        code, attempt = self.run_convert()
        self.assertEqual(code, 0, attempt.summary)
        target = c.read_cex(attempt.output)
        self.assertEqual(c.typed_value(target[9:11]),c.typed_value(self.src[9:11]))
        self.assertEqual(target[3][0][0][7],'Sombra Sur')
        self.assertEqual(target[3][1][0].state['patronSombras'],'Sombra Oeste')

    def test_bridge_improvement_preserves_native_text_values(self):
        values = [True,'0.20',True,'0.03'] + [False,'']*8
        definition = [['Trasdosado de pilares','Mejora de Puentes Térmicos',values]]
        result = c.adapt_measure_definitions(definition,c.Audit(),'prueba')
        self.assertEqual(result,definition)
        self.assertIsInstance(result[0][2][1],str)

    def test_bridge_improvement_rejects_invalid_selection_or_value(self):
        for values in ([True,'nan']+[False,'']*9, [True,'']+[False,'']*9,
                       [1,'0.2']+[False,'']*9, [True,'0.2']):
            with self.subTest(values=values),self.assertRaises(c.ConversionError):
                c.adapt_measure_definitions([['Pilar','Mejora de Puentes Térmicos',values]],c.Audit(),'prueba')

    def test_negative_new_area_is_rejected(self):
        self.src[2][22]='-1'
        self.assertFailure('E_NUMBER')

    def solar_fixture(self, monthly=None, ident=91):
        self.src[2][4]='D2';self.src[2][6]='100';self.src[2][9]='100'
        self.src[4]=[[] for _ in range(14)]
        self.src[4][0]=[['ACS','ACS',['100','',''],'Efecto Joule','Electricidad',
                        [['100','100'],['',''],['','']],'Conocido (Ensayado/justificado)',
                        ['100','',''],[False],'Edificio Objeto']]
        state=dict(zip(c.SOLAR_MONTHS,monthly or [117.7715]*12))
        state.update(nombre='Solar',zona='Edificio Objeto',potencia=1,servicio=None,tipo=None,
                     consumoMensual=None,id=c.CexObject(c.GlobalRef('uuid','UUID'),{'int':ident},'reduce'))
        self.src[4][12]=[c.CexObject(c.GlobalRef('models','GeneradorTermosolar'),state)]
        return self.src[4][12][0]
    def solar_convert(self, choices=None, *, accept=False):
        self.source_path.write_bytes(c.encoded(self.src));self.template_path.write_bytes(c.encoded(self.template))
        status, result = c.convert(self.source_path,self.template_path,solar_choices=choices)
        if accept:
            self.assertEqual(status, 2, result.summary)
            return self.accept(result, 'apply' if 'adapt' in choices.values() else 'omit')
        return status, result
    def test_solar_requires_choice_and_creates_no_output_or_log(self):
        self.solar_fixture();code,a=self.solar_convert()
        self.assertEqual(code,2);self.assertEqual(a.manifest['status'],'DECISION')
        self.assertAlmostEqual(a.manifest['pending_solar']['candidate']['percent'],70)
        self.assertEqual(set(self.root.iterdir()),{self.source_path,self.template_path})
    def test_solar_adaptation_preserves_annual_effect_of_tested_ce3x_cases(self):
        evidence = json.loads((Path(__file__).parent/'fixtures'/'solar_d2_ensayos.json').read_text(encoding='utf-8'))
        for case in evidence['casos']:
            values = case['produccion_mensual_kwh']
            expected = case['cobertura_calculada_pct']
            with self.subTest(case=case['nombre']):
                self.solar_fixture(values);code,a=self.solar_convert({'91':'adapt'}, accept=True)
                self.assertEqual(code,0,a.summary)
                dst=c.read_cex(a.output);self.assertAlmostEqual(float(dst[4][6][0][2][0]),expected,places=9)
                self.assertEqual(len(dst[4]),12);self.assertIn('Adaptado',a.manifest['decision_summary'])
                self.assertEqual(len(c.read_cex(self.source_path)[4][12]),1)
                trace = a.manifest['solar_decisions'][0]['candidate']
                self.assertAlmostEqual(trace['demand'], evidence['demanda_acs_kwh_ano'])
                self.assertEqual(list(trace['entrada']['produccion_mensual_kwh'].values()), values)
                self.assertEqual(trace['entrada']['parametros']['acs_litros_dia'], evidence['acs_litros_dia'])
                a.output.unlink()
    def test_solar_omission_is_explicit_and_preserves_main_equipment(self):
        self.solar_fixture();before=c.typed_value(self.src[4][0])
        code,a=self.solar_convert({'91':'omit'}, accept=True);self.assertEqual(code,0,a.summary)
        dst=c.read_cex(a.output);self.assertEqual(dst[4][6],[])
        self.assertEqual(c.typed_value(dst[4][0]),before)
        self.assertTrue(a.manifest['results_require_recalculation'])
    def test_solar_unsupported_storage_cannot_be_adapted_but_can_be_omitted(self):
        self.solar_fixture();self.src[4][0][0][8]=[True,'100','80','60','5','Por defecto']
        code,a=self.solar_convert();self.assertIsNone(a.manifest['pending_solar']['candidate'])
        code,a=self.solar_convert({'91':'adapt'});self.assertEqual(code,1);self.assertEqual(a.manifest['error_code'],'E_SOLAR_SCOPE')
        code,a=self.solar_convert({'91':'omit'}, accept=True);self.assertEqual(code,0,a.summary)
    def test_solar_unvalidated_climate_or_excess_is_not_offered(self):
        self.solar_fixture();self.src[2][4]='Zona desconocida'
        self.assertIsNone(c.solar_issues(self.src)[0]['candidate'])
        self.solar_fixture([1000]*12)
        self.assertIsNone(c.solar_issues(self.src)[0]['candidate'])
    def test_solar_overflow_does_not_offer_adaptation(self):
        self.solar_fixture([1e308]*12);self.src[2][9]='1e308'
        self.assertIsNone(c.solar_issues(self.src)[0]['candidate'])

    def test_solar_scope_requires_observed_area_demand_and_equipment(self):
        for case in ('cobertura_inconsistente', 'acumulacion_inactiva_con_valores', 'calefaccion', 'consumo_mensual'):
            with self.subTest(case=case):
                self.solar_fixture()
                acs = self.src[4][0][0]
                if case == 'cobertura_inconsistente':
                    acs[5][0][0] = '99'
                elif case == 'acumulacion_inactiva_con_valores':
                    acs[8] = [False, '100', '80', '60', '5', 'Por defecto']
                elif case == 'consumo_mensual':
                    self.src[4][12][0].state['consumoMensual'] = [12]*12
                else:
                    heater = copy.deepcopy(acs)
                    heater[0:2] = ['Calefaccion adicional', 'calefaccion']
                    self.src[4][1].append(heater)
                code, result = self.solar_convert()
                self.assertEqual(code, 2, result.summary)
                self.assertEqual(set(result.manifest['pending_plan']['options']), {'omit'})
                self.assertFalse(result.output.exists())

    def test_solar_experimental_uses_actual_climate_and_flow(self):
        for zone, area, flow, demand in [('D1',150,112,2284.6208), ('D2',85,75,1514.205), ('C3',110,135,2629.638)]:
            with self.subTest(zone=zone):
                self.solar_fixture([40]*12)
                self.src[2][4], self.src[2][6], self.src[2][9] = zone, str(area), str(flow)
                self.src[2][22] = '175'
                self.src[4][0][0][5][0][0] = str(area)
                code, plan = self.solar_convert()
                self.assertEqual(code, 2, plan.summary)
                self.assertEqual(set(plan.manifest['pending_plan']['options']), {'omit','experimental'})
                self.assertAlmostEqual(plan.manifest['pending_solar']['candidate']['demand'], demand)
                self.assertEqual(self.solar_convert({'91':'adapt'})[0], 1)
                code, converted = self.accept(plan, 'experimental')
                self.assertEqual(code, 0, converted.summary)
                target = c.read_cex(converted.output)
                self.assertAlmostEqual(float(target[4][6][0][2][0]), 48000/demand, places=9)
                self.assertEqual(target[4][0], self.src[4][0])
                converted.output.unlink()

    def test_monthly_electric_generation_and_active_ventilation_are_blocked(self):
        generator = c.CexObject(c.GlobalRef('models','GeneradorElectrico'),
                                {'nombre':'Generacion electrica mensual','enero':100,'consumoMensual':[12]*12})
        self.src[4][13] = [generator]
        code, result = self.run_convert()
        self.assertEqual(code, 1)
        self.assertEqual(result.manifest['error_code'], 'E_NEW_SYSTEM')
        self.assertIn('autoconsumo computable por servicio', result.summary)
        self.assertFalse(result.output.exists())
        self.src[4][13] = []
        self.src[4][8] = [['Recuperador de calor','ventilacion','250','0.8']]
        code, result = self.run_convert()
        self.assertEqual(code, 1)
        self.assertEqual(result.manifest['error_code'], 'E_SYSTEM_UNSUPPORTED')
        self.assertIn('caudal, recuperacion y consumo', result.summary)
        self.assertFalse(result.output.exists())

    def test_electric_monthly_epb_sum_requires_experimental_consent(self):
        monthly = [35.5, 0, 12.25, 0, 20, 0, 80, 0, 0, 1.25, 0, 0]
        state = dict(zip(c.SOLAR_MONTHS, monthly), nombre='Autoconsumo', zona='Edificio Objeto',
                     potencia=3.5, tipo=None, consumoMensual=list(monthly))
        self.src[4][13] = [c.CexObject(c.GlobalRef('models', 'GeneradorElectrico'), state)]
        code, plan = self.run_convert()
        self.assertEqual(code, 2, plan.summary)
        self.assertFalse(plan.output.exists())
        self.assertEqual(set(plan.manifest['pending_plan']['options']), {'omit', 'experimental'})
        code, adapted = self.accept(plan, 'experimental')
        self.assertEqual(code, 0, adapted.summary)
        rows = c.read_cex(adapted.output)[4][6]
        self.assertEqual(rows[0][2:], [['', '', '', False], ['149', '', '', '', '', ''],
                                      [False, True], 'Edificio Objeto'])
        self.assertEqual(c.sha(self.source_path), plan.manifest['source_sha256'])
        self.assertIn('reparto mensual', adapted.manifest['decision_summary'])
        adapted.output.unlink()
        code, omitted = self.accept(plan)
        self.assertEqual(code, 0, omitted.summary)
        self.assertEqual(c.read_cex(omitted.output)[4][6], [])
        omitted.output.unlink()
        state['consumoMensual'][6] = 2
        self.assertFailure('E_NEW_SYSTEM')

    def test_acs_deposit_retains_native_modes_and_multiplier(self):
        for tank in ([True,'200','60','50','51.9','Por defecto','10'],
                     [True,'200','60','50','7.5','Conocido'],
                     [True,'1000','80','60','1.7','Estimado','0.065','Poliuretano Rígido','2.5']):
            with self.subTest(tank=tank):
                self.src[4][5][0][8] = tank
                code, result = self.run_convert()
                self.assertEqual(code, 0, result.summary)
                self.assertEqual(c.read_cex(result.output)[4][5][0][8], tank)
                result.output.unlink()
        self.src[4][5][0][8] = [True,'200','60','50','51.9','Modo desconocido','10']
        self.assertFailure('E_SYSTEM_TAIL')
    def test_solar_stale_choice_and_changed_file_rejected(self):
        self.solar_fixture();code,a=self.solar_convert({'unknown':'omit'})
        self.assertEqual(code,1)
        code,a=c.convert(self.source_path,self.template_path,solar_choices={'91':'adapt'},expected_source_sha='old')
        self.assertEqual(a.manifest['error_code'],'E_INPUT_CHANGED');self.assertFalse(a.output.exists())
    def test_empty_report_is_native_and_preserved(self):
        self.src[11]=[];code,a=self.run_convert();self.assertEqual(code,0,a.summary)
        self.assertEqual(c.read_cex(a.output)[11],[])
    def solar_measure_fixture(self):
        self.solar_fixture();systems=copy.deepcopy(self.src[4]);self.src[4][12]=[]
        m=self.fixture_measure('MM Solar');m.state['mejoras'][1][1]=systems
        m.state['datosInstalaciones']=systems
        for key,entries in zip(c.MM_SYSTEM_KEYS,systems):m.state[key]=entries
        m.state['listadoGeneradoresTermosolarMM']=systems[12]
        self.src[5]=[m]
        self.src[6][2]=[['Instalacion','MM Solar','Instalaciones','20','1500','0']]
        self.src[11][0]='MM Solar'
        return m
    def test_solar_measure_adapts_all_definition_copies(self):
        self.solar_measure_fixture();code,a=self.solar_convert({'91':'adapt'}, accept=True)
        self.assertEqual(code,0,a.summary);m=c.read_cex(a.output)[5][0]
        for rows in [m.state['sistemasContribucionesMM'],m.state['datosInstalaciones'][6],m.state['mejoras'][1][1][6]]:
            self.assertEqual(len(rows),1);self.assertEqual(rows[0][2][0],'70')
        self.assertEqual(len(m.state['datosInstalaciones']),12)

    def test_experimental_solar_measure_keeps_costs_and_contribution_copies(self):
        self.solar_measure_fixture()
        self.src[2][4]='D1'
        self.src[2][9]='112'
        code, plan = self.solar_convert()
        self.assertEqual(code, 2, plan.summary)
        code, attempt = self.accept(plan, 'experimental')
        self.assertEqual(code, 0, attempt.summary)
        dest = c.read_cex(attempt.output)
        self.assertEqual(dest[6], self.src[6])
        self.assertEqual(dest[11], self.src[11])
        measure = dest[5][0].state
        rows = measure['sistemasContribucionesMM']
        self.assertEqual(rows, measure['datosInstalaciones'][6])
        self.assertEqual(rows, measure['mejoras'][1][1][6])
        self.assertAlmostEqual(float(rows[0][2][0]), 100 * 1413.258 / 2284.6208, places=9)

    def test_solar_measure_combines_with_a_native_envelope_definition(self):
        group = self.solar_measure_fixture()
        envelope = ['Aislamiento', 'Adición de Aislamiento Térmico',
                    [True, False, False, False, '', '', '0.03', '0.04', '', '', False, [], '']]
        group.state['mejoras'][0] = [envelope]
        group.state['medidasMejoraEnvolvente'] = [envelope]
        code, plan = self.solar_convert()
        self.assertEqual(code, 2, plan.summary)
        code, result = self.accept(plan, 'experimental')
        self.assertEqual(code, 0, result.summary)
        target = c.read_cex(result.output)
        measures = target[5][0].state
        self.assertEqual(measures['mejoras'][0][0][1], envelope[1])
        self.assertEqual(measures['mejoras'][1][1][6][0][2][0], '70')
        self.assertEqual(target[6:7], self.src[6:7])
        self.assertEqual(target[11], self.src[11])

    def test_solar_omit_measure_removes_report_and_cost_references(self):
        self.solar_measure_fixture();code,a=self.solar_convert({'91':'omit'})
        self.assertEqual(code,2,a.summary)
        code,a=self.accept(a)
        self.assertEqual(code,0,a.summary);dst=c.read_cex(a.output)
        self.assertEqual(dst[5],[]);self.assertEqual(dst[6][2],[]);self.assertEqual(dst[11][0],'')
    def test_solar_pipe_cancel_produces_no_file(self):
        self.solar_fixture();self.solar_convert()
        responses=io.StringIO()
        commands=[{'command':'convert','source':str(self.source_path),'template':str(self.template_path)},
                  {'command':'decision','id':'91','choice':'cancel'}]
        c.serve(io.StringIO(''.join(json.dumps(x)+'\n' for x in commands)),responses)
        self.assertIn('DECISION_ADAPT\t91\t',responses.getvalue())
        self.assertIn('CANCELADO\t\t',responses.getvalue());self.assertFalse(c.output_path(self.source_path).exists())
    def test_solar_pipe_adapt_summary_and_diagnostic_decision(self):
        self.solar_fixture();self.solar_convert();responses=io.StringIO()
        dest=self.root/'diagnostic.zip'
        commands=[{'command':'convert','source':str(self.source_path),'template':str(self.template_path)},
                  {'command':'decision','id':'91','choice':'adapt'},
                  {'command':'diagnostic','destination':str(dest)}]
        c.serve(io.StringIO(''.join(json.dumps(x)+'\n' for x in commands)),responses)
        self.assertIn('REVISAR_CAMBIOS\t',responses.getvalue());self.assertIn('Adaptado: Solar',responses.getvalue())
        with zipfile.ZipFile(dest) as z:
            manifests=[n for n in z.namelist() if n.endswith('resultado.json')]
            self.assertTrue(manifests)
            manifest=json.loads(z.read(manifests[0]));self.assertEqual(manifest['solar_decisions'][0]['choice'],'adapt')

    def test_active_measure_metadata_preserves_measure_and_references(self):
        measure = self.fixture_measure('Mejora priorizada')
        measure.state.update(justificacion='Indicación del técnico', seRecomienda=False)
        self.src[5] = [measure]
        self.src[6][2] = [['Instalación','Mejora priorizada','Instalaciones','30','8000','150']]
        self.src[11][0] = 'Mejora priorizada'
        code, analysis = self.run_convert()
        self.assertEqual(code, 2, analysis.summary)
        self.assertEqual({x['path'] for x in analysis.audit.losses},
                         {'medidas_mejora[0].justificacion', 'medidas_mejora[0].seRecomienda'})
        code, result = self.accept(analysis)
        self.assertEqual(code, 0, result.summary)
        dest = c.read_cex(result.output)
        self.assertEqual(dest[5][0].state['nombre'], 'Mejora priorizada')
        self.assertNotIn('justificacion', dest[5][0].state)
        self.assertEqual(dest[6:7], self.src[6:7])
        self.assertEqual(dest[11], self.src[11])

    def test_simultaneous_losses_need_one_worker_decision_and_match_summary(self):
        self.blind_fixture()
        self.src[1][26] = 'Clasificación adicional'
        self.src[2][22] = '200'
        system = self.src[4][5][0]
        system[9] = ['200', '200', '200']
        system[8][6] = '1'
        self.src[12]['Icaen'] = 'Configuración que se perderá'
        code, analysis = self.run_convert()
        self.assertEqual(code, 2, analysis.summary)
        before = c.sha(self.source_path)
        self.assertFalse(analysis.output.exists())
        expected = {'edificio.solar', 'administrativos[26]', 'generales[22]',
                    'instalaciones[5][0][9]', 'complementos.Icaen'}
        self.assertEqual({item['path'] for item in analysis.audit.losses}, expected)
        commands = [{'command':'convert','source':str(self.source_path),'template':str(self.template_path)},
                    {'command':'decision','id':analysis.manifest['pending_plan']['id'],'choice':'omit'}]
        responses = io.StringIO()
        c.serve(io.StringIO(''.join(json.dumps(x)+'\n' for x in commands)), responses)
        preview, result = responses.getvalue().strip('\n').split('\n')
        self.assertTrue(preview.startswith('DECISION_EXPERIMENTAL\t'))
        self.assertTrue(result.startswith('REVISAR_CAMBIOS\t'))
        self.assertIn('CONVERSION_CON_OMISIONES', result)
        for path in expected:
            self.assertIn(path, preview)
            self.assertIn(path, result)
        self.assertEqual(c.sha(self.source_path), before)
        self.assertTrue(analysis.output.exists())

    def test_consent_does_not_authorize_modified_source_or_other_option(self):
        self.solar_fixture()
        self.src[2][23] = '1'
        code, analysis = self.run_convert()
        self.assertEqual(code, 2, analysis.summary)
        selected = analysis.manifest['pending_plan']['options']['omit']
        code, result = c.convert(self.source_path, self.template_path, solar_choices={'91':'adapt'},
                                 consent=selected['token'])
        self.assertEqual(result.manifest['error_code'], 'E_CONSENT_CHANGED')
        self.assertFalse(result.output.exists())
        self.src[2][23] = '2'
        self.source_path.write_bytes(c.encoded(self.src))
        code, result = self.accept(analysis)
        self.assertEqual(result.manifest['error_code'], 'E_CONSENT_CHANGED')
        self.assertFalse(result.output.exists())

    def test_unknown_field_blocks_even_when_other_losses_are_known(self):
        self.src[2][22] = '200'
        measure = self.fixture_measure()
        measure.state['campo_inesperado'] = {'activo':'dato'}
        self.src[5] = [measure]
        code, result = self.run_convert()
        self.assertEqual(code, 1)
        self.assertIn('campo_inesperado', result.summary)
        self.assertNotIn('pending_plan', result.manifest)
        self.assertFalse(result.output.exists())

    def test_solar_omission_blocks_unrecognized_measure_references(self):
        self.solar_measure_fixture()
        retained = self.fixture_measure('Otra mejora')
        retained.state['datosEdificioOriginal'] = self.src[5][0]
        self.src[5].append(retained)
        self.assertFailure('E_MM_REFERENCE')

    def test_unknown_solar_class_cannot_be_omitted(self):
        generator = self.solar_fixture()
        generator.cls = c.GlobalRef('models', 'GeneradorNuevo')
        self.assertFailure('E_SOLAR_SCHEMA')

    def test_unknown_reserved_payload_cannot_be_replaced(self):
        self.src[14] = 'Información auxiliar de forma desconocida'
        self.assertFailure('E_RESERVED_BLOCK')


if __name__=='__main__':unittest.main(verbosity=2)

