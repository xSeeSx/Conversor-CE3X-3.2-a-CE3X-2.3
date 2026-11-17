"""Conversor experimental CE3X 3.2 -> 2.3, motor sin dependencias externas.
No importa clases de CE3X ni ejecuta funciones contenidas en los pickle.
"""
from __future__ import annotations
import argparse
import codecs
import copy
import datetime as dt
from decimal import Decimal
import hashlib
import io
import json
import math
import os
from pathlib import Path
import pickle
import pickletools
import platform
import re
import sys
import traceback
import tempfile
import zipfile
from dataclasses import dataclass, field

VERSION = '1.4.0'
ROOT = Path(__file__).resolve().parent
MAX_BYTES = 64 * 1024 * 1024
BLOCK_NAMES = ['version', 'administrativos', 'generales', 'envolvente', 'instalaciones',
               'medidas_mejora', 'analisis_economico', 'subgrupos', 'composiciones',
               'sombras', 'nombres_sombras', 'informe', 'complementos', 'reservado_13', 'reservado_14']

class ConversionError(Exception):
    def __init__(self, code, message, path=''):
        super().__init__(message)
        self.code, self.path = code, path

class LegacyString(str):
    """STRING de Python 2, separado de UNICODE para conservar la codificacion."""

@dataclass(frozen=True)
class GlobalRef:
    module: str
    name: str

@dataclass
class CexObject:
    cls: GlobalRef
    state: dict = field(default_factory=dict)
    style: str = 'inst'

RECONSTRUCTOR = GlobalRef('copy_reg', '_reconstructor')
OBJECT = GlobalRef('__builtin__', 'object')

class InertUnpickler(pickle._Unpickler):
    """Solo crea datos inertes. GLOBAL nunca resuelve ni importa codigo."""
    dispatch = pickle._Unpickler.dispatch.copy()

    def find_class(self, module, name):
        return GlobalRef(module, name)

    def _decode_string(self, value):
        return LegacyString(value.decode('latin1'))

    def load_reduce(self):
        args = self.stack.pop()
        func = self.stack.pop()
        if func == RECONSTRUCTOR and isinstance(args, tuple) and len(args) == 3:
            cls, base, state = args
            if isinstance(cls, GlobalRef) and base == OBJECT and state is None:
                self.append(CexObject(cls, style="reduce"))
                return
        if func == GlobalRef('decimal', 'Decimal') and isinstance(args, tuple) and len(args)==1 and isinstance(args[0], str):
            require(len(args[0]) <= 1000, 'E_DECIMAL', 'Decimal demasiado largo')
            value=Decimal(args[0])
            require(value.is_finite(), 'E_DECIMAL', 'Decimal no finito')
            self.append(value)
            return
        raise ConversionError('E_PICKLE_REDUCE', 'Funcion serializada no admitida: %r' % (func,))
    dispatch[pickle.REDUCE[0]] = load_reduce

    def load_inst(self):
        module = self.readline()[:-1].decode("ascii")
        name = self.readline()[:-1].decode("ascii")
        args = self.pop_mark()
        if args:
            raise ConversionError("E_PICKLE_INST_ARGS", "Constructor INST con argumentos no admitido")
        self.append(CexObject(GlobalRef(module, name), style="inst"))
    dispatch[pickle.INST[0]] = load_inst

    def load_build(self):
        state = self.stack.pop()
        obj = self.stack[-1]
        if not isinstance(obj, CexObject) or not isinstance(state, dict):
            raise ConversionError('E_PICKLE_STATE', 'Estado de objeto no reconocido')
        obj.state.update(state)
    dispatch[pickle.BUILD[0]] = load_build

    def forbidden(self):
        raise ConversionError('E_PICKLE_OPCODE', 'Operacion pickle no admitida')
    for _op in (pickle.OBJ, pickle.NEWOBJ, pickle.NEWOBJ_EX,
                pickle.EXT1, pickle.EXT2, pickle.EXT4, pickle.PERSID, pickle.BINPERSID):
        dispatch[_op[0]] = forbidden

class LegacyPickler(pickle._Pickler):
    dispatch = pickle._Pickler.dispatch.copy()

    def save_legacy_string(self, obj):
        # repr(bytes) produce escapes para S; nunca aplicar esos escapes a V.
        try:
            raw = str(obj).encode('latin1')
        except UnicodeEncodeError as exc:
            raise ConversionError('E_ENCODING', 'Cadena STRING fuera de Latin-1') from exc
        self.write(b'S' + repr(raw)[1:].encode('ascii') + b'\n')
        self.memoize(obj)
    dispatch[LegacyString] = save_legacy_string

    def save_decimal(self, obj):
        self.save(GlobalRef('decimal', 'Decimal'))
        self.save((str(obj),))
        self.write(pickle.REDUCE)
        self.memoize(obj)
    dispatch[Decimal] = save_decimal

    def save_ref(self, obj):
        if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9.]*', obj.module) or not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', obj.name):
            raise ConversionError('E_GLOBAL_NAME', 'Nombre de clase invalido')
        self.write(b'c' + obj.module.encode('ascii') + b'\n' + obj.name.encode('ascii') + b'\n')
        self.memoize(obj)
    dispatch[GlobalRef] = save_ref

    def save_object(self, obj):
        if obj.style == "inst":
            self.write(b"(i" + obj.cls.module.encode("ascii") + b"\n" + obj.cls.name.encode("ascii") + b"\n")
        elif obj.style == "reduce":
            self.save(RECONSTRUCTOR)
            self.save((obj.cls, OBJECT, None))
            self.write(pickle.REDUCE)
        else:
            raise ConversionError("E_OBJECT_STYLE", "Estilo de objeto desconocido")
        self.memoize(obj)
        self.save(obj.state)
        self.write(pickle.BUILD)
    dispatch[CexObject] = save_object


def encoded(blocks):
    out = io.BytesIO()
    for value in blocks:
        LegacyPickler(out, protocol=0, fix_imports=False).dump(value)
    return out.getvalue().replace(b'\n', b'\r\n')


def protocol0_ops(data):
    """Inspeccion con STRING Latin-1 explicito en todas las versiones de Python.

    pickletools de Python 3.11 decodifica STRING como ASCII, mientras versiones
    posteriores usan Latin-1. CE3X guarda bytes de Python 2, tambien escapados.
    Se conserva el flujo original y sus offsets, sin parches globales a stdlib.
    """
    stream = io.BytesIO(data)
    while True:
        pos = stream.tell()
        code = stream.read(1)
        op = pickletools.code2op.get(code.decode('latin1'))
        if op is None:
            raise ConversionError('E_TRUNCATED' if not code else 'E_PICKLE_OPCODE',
                                  f'Operacion ausente o desconocida en offset {pos}: {code!r}')
        if op.proto > 0:
            raise ConversionError('E_PROTOCOL', 'Solo se admite pickle protocolo 0')
        if op.name == 'STRING':
            literal = pickletools.read_stringnl(stream, decode=False)
            arg = codecs.escape_decode(literal)[0].decode('latin1')
        else:
            arg = op.arg.reader(stream) if op.arg is not None else None
        yield op, arg, pos
        if op.name == 'STOP':
            return


def read_cex(path, audit=None, label='source'):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ConversionError('E_SIZE', 'El archivo supera 64 MiB', str(path))
    original = path.read_bytes()
    # Perfil observado: protocolo 0 textual, con CRLF al guardarse en Windows.
    if original[:1] not in (b'S', b'V'):
        raise ConversionError('E_FORMAT', 'No es un CEX textual del perfil compatible', str(path))
    raw = original.replace(b'\r\n', b'\n')
    stream = io.BytesIO(raw)
    blocks = []
    while stream.tell() < len(raw):
        offset = stream.tell()
        if len(blocks) >= 15:
            raise ConversionError('E_BLOCK_COUNT', 'Hay datos despues del bloque 14', f'{label}[15]')
        if audit:
            audit.stage = f'leer {label} bloque {len(blocks)} ({BLOCK_NAMES[len(blocks)]}), offset LF {offset}'
        try:
            # Preinspeccion independiente. Rechaza protocolos binarios antes de leer.
            end = None
            for op, arg, pos in protocol0_ops(raw[offset:]):
                if op.name == 'STOP':
                    end = offset + pos + 1
            if end is None:
                raise ConversionError('E_TRUNCATED', 'Bloque incompleto')
            obj = InertUnpickler(stream, encoding='latin1').load()
            if stream.tell() != end:
                raise ConversionError('E_OFFSET', 'La lectura y la preinspeccion no coinciden')
            blocks.append(obj)
            if audit:
                audit.event('INFO', 'BLOCK_READ', audit.stage, size_lf=end-offset)
        except Exception as exc:
            if isinstance(exc, ConversionError):
                raise
            raise ConversionError('E_READ', f'No se puede leer el bloque {len(blocks)}: {exc}', f'{label}[{len(blocks)}] @ {offset}') from exc
    if len(blocks) != 15:
        raise ConversionError('E_BLOCK_COUNT', f'Se esperaban 15 bloques; encontrados {len(blocks)}')
    return blocks


def json_value(value, depth=0):
    if depth > 120:
        raise ConversionError('E_DEPTH', 'Anidamiento excesivo')
    if isinstance(value, Decimal): return {'decimal':str(value)}
    if isinstance(value, CexObject):
        return {'class': value.cls.module + '.' + value.cls.name,
                'state': json_value(value.state, depth+1)}
    if isinstance(value, GlobalRef):
        return {'global': value.module + '.' + value.name}
    if isinstance(value, dict):
        return {str(k): json_value(v, depth+1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(v, depth+1) for v in value]
    if isinstance(value, str):
        return str(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise ConversionError('E_TYPE', f'Tipo no soportado: {type(value).__name__}')


def typed_value(value, seen=None):
    """Representacion tipada de un grafo, incluidas referencias compartidas/ciclos."""
    if seen is None: seen = {}
    if isinstance(value, Decimal): return ['DECIMAL', str(value)]
    if isinstance(value, LegacyString): return ['STRING', str(value)]
    if isinstance(value, str): return ['UNICODE', value]
    if isinstance(value, GlobalRef): return ['GLOBAL', value.module, value.name]
    if isinstance(value, (CexObject, dict, list, tuple)):
        identity = id(value)
        if identity in seen: return ['REF', seen[identity]]
        number = len(seen)
        seen[identity] = number
        child = lambda x: typed_value(x, seen)
        if isinstance(value, CexObject):
            return ['OBJECT', number, value.style, child(value.cls), child(value.state)]
        if isinstance(value, dict): return ['DICT', number, [[child(k), child(v)] for k,v in value.items()]]
        if isinstance(value, list): return ['LIST', number, [child(v) for v in value]]
        if isinstance(value, tuple): return ['TUPLE', number, [child(v) for v in value]]
    return [type(value).__name__, value]


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, code, text, path=''):
    if not condition: raise ConversionError(code, text, path)


def empty(value):
    return value is None or value is False or value == '' or value == []


def as_num(value, path, minimum=None):
    try:
        require(not isinstance(value, bool), 'E_NUMBER', 'Un booleano no es un numero', path)
        result = float(str(value).replace(',', '.'))
        require(math.isfinite(result), 'E_NUMBER', 'Numero no finito', path)
        if minimum is not None:
            require(result >= minimum, 'E_NUMBER', f'Valor menor que {minimum}', path)
        return result
    except (TypeError, ValueError) as exc:
        raise ConversionError('E_NUMBER', f'Valor numerico invalido: {value!r}', path) from exc


class Audit:
    def __init__(self, run=None):
        self.stage = 'inicio'
        self.events, self.changes, self.omitted = [], [], []

    def event(self, level, code, message, **data):
        self.events.append({'time': dt.datetime.now().astimezone().isoformat(), 'level': level,
                            'code': code, 'stage': self.stage, 'message': message, **data})

    def change(self, code, path, before, after, reason):
        self.changes.append({'code': code, 'path': path, 'before': json_value(before),
                             'after': json_value(after), 'reason': reason})
        self.event('INFO', code, reason, path=path)

    def omit(self, path, value, reason):
        self.omitted.append({'path': path, 'value': json_value(value), 'reason': reason})

    def log_text(self):
        lines = [f'CE3X Conversor {VERSION}']
        for record in self.events:
            lines.append(f"{record['time']} [{record['level']}] {record['code']} | {record['stage']} | {record['message']}")
            extra = {key: value for key, value in record.items()
                     if key not in ('time', 'level', 'code', 'stage', 'message')}
            if extra:
                lines.append(json.dumps(extra, ensure_ascii=False))
        return '\n'.join(lines) + '\n'


def repair_text(value, audit, path, memo=None):
    """Repara solo escapes literales de caracteres espanoles, no escapes arbitrarios."""
    if memo is None: memo={}
    if id(value) in memo: return memo[id(value)]
    if isinstance(value, str):
        def replace(match):
            char=chr(int(match.group(1) or match.group(2),16))
            return char if char in 'áéíóúüñÁÉÍÓÚÜÑ' else match.group(0)
        fixed=re.sub(r'\\(?:x([0-9a-fA-F]{2})|u([0-9a-fA-F]{4}))',replace,str(value))
        if fixed != value:
            result = LegacyString(fixed) if isinstance(value, LegacyString) else fixed
            audit.change('FIX_ACCENT_ESCAPE',path,value,result,'Escape literal de acento o ene reparado automaticamente')
            return result
        return value
    if isinstance(value,list):
        result=[];memo[id(value)]=result
        result.extend(repair_text(v,audit,f'{path}[{i}]',memo) for i,v in enumerate(value));return result
    if isinstance(value,tuple):
        values=[repair_text(v,audit,f'{path}[{i}]',memo) for i,v in enumerate(value)]
        if id(value) not in memo: memo[id(value)]=tuple(values)
        return memo[id(value)]
    if isinstance(value,dict):
        result={};memo[id(value)]=result
        for k,v in value.items():
            key=repair_text(k,audit,path+'.key',memo)
            require(key not in result,'E_TEXT_COLLISION','La reparacion crea claves duplicadas',path)
            result[key]=repair_text(v,audit,path+'.'+str(k),memo)
        return result
    if isinstance(value,CexObject):
        result=CexObject(value.cls,style=value.style);memo[id(value)]=result
        result.state=repair_text(value.state,audit,path+'.state',memo);return result
    return value


def validate(blocks, audit, profile, target=False):
    audit.stage = 'validar destino' if target else 'validar origen'
    require(len(blocks)==15,'E_BLOCK_COUNT','Numero de bloques incorrecto')
    for i in (1,2,3,4,5,6,7,8,9,10,11):
        require(isinstance(blocks[i],list),'E_BLOCK_TYPE','Se esperaba una lista',f'blocks[{i}]')
    require(isinstance(blocks[12],dict),'E_BLOCK_TYPE','Se esperaba un diccionario','blocks[12]')
    require(len(blocks[3])==4,'E_ENVELOPE','Envolvente con estructura desconocida','blocks[3]')
    require(all(isinstance(g,list) for g in blocks[3]),'E_ENVELOPE','Grupos de envolvente invalidos')
    require(len(blocks[1]) >= 26 and len(blocks[2]) >= 21,'E_FIELDS','Datos generales incompletos')
    if target:
        require(len(blocks[1])==26 and len(blocks[2])==21,'E_FIELDS','Longitud de destino incorrecta')
        require(len(blocks[4])==12,'E_SYSTEM_GROUPS','Se esperaban 12 grupos en 2.3')
    as_num(blocks[2][6],'generales.superficie',minimum=.01)
    as_num(blocks[2][7],'generales.altura',minimum=.01)
    env, windows, bridges, subs = blocks[3]
    names=[]
    compositions={str(x.state.get('nombre')) for x in blocks[8] if isinstance(x,CexObject)}
    shadows={str(x) for x in blocks[10]}
    for i,e in enumerate(env):
        p=f'envolvente.cerramientos[{i}]'
        require(isinstance(e,list) and len(e)>=13,'E_ENVELOPE_ROW','Cerramiento incompleto',p)
        key=str(e[1])+'|'+str(e[-1])
        expected=profile['envelope_lengths'].get(key)
        if expected is None:
            raise ConversionError('E_ENVELOPE_UNKNOWN', f'Tipo de cerramiento sin regla contrastada: {key}',p)
        require(len(e)==expected,'E_ENVELOPE_ROW',f'{key}: esperados {expected} campos; hay {len(e)}',p)
        require(isinstance(e[0],str) and e[0],'E_NAME','Nombre de cerramiento vacio',p)
        names.append(e[0])
        as_num(e[2],p+'.superficie',minimum=0)
        as_num(e[3],p+'.U',minimum=0)
        if e[8]=='Conocidas' and e[6] and e[6] not in compositions:
            audit.event('WARNING','W_COMPOSITION',f'Composicion no encontrada: {e[6]}',path=p)
        if e[7] and e[7] not in shadows:
            raise ConversionError('E_SHADOW_REFERENCE',f'Patron de sombras no encontrado: {e[7]}',p)
    require(len(set(names))==len(names),'E_DUPLICATE','Nombres de cerramiento duplicados')
    window_names=[]
    for i,w in enumerate(windows):
        p=f'envolvente.huecos[{i}]'
        require(isinstance(w,CexObject) and w.cls.module=='Envolvente.objetosEnvolvente' and w.cls.name in ('HuecoConocidas','HuecoEstimadas'),
                'E_WINDOW_CLASS','Clase de hueco desconocida',p)
        state=w.state
        for key in ('descripcion','cerramientoAsociado','superficie','elementosProteccionSolar'):
            require(key in state,'E_WINDOW_FIELD',f'Falta {key}',p)
        require(state['cerramientoAsociado'] in names,'E_WINDOW_REFERENCE','Hueco sin cerramiento asociado',p)
        as_num(state['superficie'],p+'.superficie',minimum=0)
        for key in ('Uvidrio','Umarco','Gvidrio'):
            if key in state: as_num(state[key],p+'.'+key,minimum=0)
        if state.get('patronSombras') and state['patronSombras'] not in shadows:
            raise ConversionError('E_SHADOW_REFERENCE','Hueco con patron de sombras inexistente',p)
        window_names.append(state['descripcion'])
        if target:
            require('id' not in state,'E_UUID','UUID 3.2 todavia presente',p)
            require(len(state['elementosProteccionSolar'])==profile['window_solar_fields'],
                    'E_SOLAR_FIELDS','Proteccion solar de longitud incorrecta',p)
    require(len(set(window_names))==len(window_names),'E_DUPLICATE','Nombres de hueco duplicados')
    for i,b in enumerate(bridges):
        p=f'envolvente.puentes[{i}]'
        require(isinstance(b,list) and len(b)==9,'E_BRIDGE','Puente termico de formato desconocido',p)
        require(b[7] in names,'E_BRIDGE_REFERENCE','Puente termico sin cerramiento asociado',p)
        as_num(b[3],p+'.psi')
        as_num(b[4],p+'.longitud',minimum=0)
    audit.event('INFO','MODEL_COUNTS','Inventario validado',cerramientos=len(env),huecos=len(windows),puentes=len(bridges),subgrupos=len(subs))


def adapt_systems(source, audit, profile, path_prefix='instalaciones'):
    require(len(source) in (12,14),'E_SYSTEM_GROUPS',f'Numero de grupos no reconocido: {len(source)}')
    if len(source)>12:
        extra=source[12:]
        audit.omit(path_prefix+'[12:]',extra,'Grupos nuevos de CE3X 3.2 sin equivalente contrastado')
        require(all(empty(x) for x in extra),'E_NEW_SYSTEM','Hay instalaciones nuevas no compatibles en grupos 12/13',path_prefix+'[12:]')
        audit.change('SYSTEM_GROUPS',path_prefix+'.length',len(source),12,'Retirados dos grupos adicionales vacios de 3.2')
    output=copy.deepcopy(source[:12])
    for g,group in enumerate(output):
        require(isinstance(group,list),'E_SYSTEM_GROUP','Grupo de instalaciones invalido',f'{path_prefix}[{g}]')
        for i,entry in enumerate(group):
            p=f'{path_prefix}[{g}][{i}]'
            require(isinstance(entry,list),'E_SYSTEM_ROW','Registro de instalacion invalido',p)
            if g==6:
                require(len(entry)==6 and entry[1] in ('renovable','Contribuciones energéticas'),
                        'E_CONTRIBUTION','Contribucion sin equivalencia contrastada',p)
                require([len(entry[j]) if isinstance(entry[j],list) else -1 for j in (2,3,4)]==[4,6,2],
                        'E_CONTRIBUTION','Estructura de contribucion desconocida',p)
                if entry[1]=='renovable':
                    entry[1]=LegacyString('Contribuciones energéticas')
                    audit.change('CONTRIBUTION_TYPE',p+'[1]','renovable',entry[1],'Tipo nativo de contribucion energetica en 2.3')
                continue
            if g>5:
                # No se inventan conversiones para contribuciones/terciario no contrastadas.
                raise ConversionError('E_SYSTEM_UNSUPPORTED','Grupo activo sin regla contrastada; se necesita muestra nativa 2.3',p)
            require(len(entry) in (10,11),'E_SYSTEM_ROW',f'Esperados 10/11 campos; hay {len(entry)}',p)
            require(entry[1] in ('ACS','calefaccion','refrigeracion','climatizacion','mixto2','mixto3'),
                    'E_SYSTEM_TYPE',f'Tipo de instalacion no contrastado: {entry[1]}',p)
            if len(entry)==11:
                removed=entry.pop(9)
                require(isinstance(removed,list) and len(removed)==3,'E_SYSTEM_TAIL','Campo adicional de instalacion inesperado',p+'[9]')
                audit.omit(p+'[9]',removed,'Campo adicional 3.2, sin equivalente en 2.3')
                audit.change('SYSTEM_FIELD',p+'.length',11,10,'Adaptado registro de instalacion al formato nativo 2.3')
            require(isinstance(entry[-1],str),'E_SYSTEM_SUBGROUP','Subgrupo de instalacion no valido',p)
            accumulation=entry[8]
            if isinstance(accumulation,list) and len(accumulation)==7:
                removed=accumulation.pop()
                audit.omit(p+'[8][6]',removed,'Campo adicional de acumulacion de CE3X 3.2')
                audit.event('WARNING','W_DHW_FIELD','Retirado campo adicional de acumulacion. Revisar el deposito y su UA en CE3X 2.3.',path=p)
                audit.change('DHW_ACCUMULATION',p+'[8].length',7,6,'Adaptado deposito ACS al formato 2.3')
            if str(entry[6]).startswith('Estimado'):
                audit.event('WARNING','W_ESTIMATED_SYSTEM',f'{entry[0]} conserva modo y rendimientos estimados. Recalcular en 2.3.',path=p,mode=entry[6],efficiency=json_value(entry[2]))
            # Deliberadamente no se toman rendimientos ni UA de la plantilla.
    return output


MM_SYSTEM_KEYS=['sistemasACSMM','sistemasCalefaccionMM','sistemasRefrigeracionMM',
                'sistemasClimatizacionMM','sistemasMixto2MM','sistemasMixto3MM',
                'sistemasContribucionesMM','sistemasIluminacionMM','sistemasVentilacionMM',
                'sistemasVentiladoresMM','sistemasBombasMM','sistemasTorresRefrigeracionMM']


def mm_schema():
    return json.loads((ROOT/'mm_schema_23.json').read_text(encoding='utf-8'))['classes']


def adapt_measure_definitions(definitions,audit,path):
    output=copy.deepcopy(definitions)
    require(isinstance(output,list),'E_MM_DEFINITION','Definicion de mejora desconocida',path)
    for i,item in enumerate(output):
        p=f'{path}[{i}]'
        require(isinstance(item,list) and len(item)==3 and isinstance(item[2],list),
                'E_MM_DEFINITION','Medida incompleta',p)
        data=item[2]
        if item[1]=='Adición de Aislamiento Térmico':
            require(len(data)==13,'E_MM_DEFINITION','Aislamiento con campos desconocidos',p)
            indices=(6,7,8,9)
        elif item[1]=='Sustitución/mejora de Huecos':
            require(len(data)==21,'E_MM_DEFINITION','Sustitucion de huecos con campos desconocidos',p)
            indices=(3,4,12,15)
        else:
            raise ConversionError('E_MM_DEFINITION','Tipo de medida sin regla contrastada: '+str(item[1]),p)
        for j in indices:
            if isinstance(data[j],str) and data[j]!='':
                before=data[j];data[j]=as_num(before,p+f'[2][{j}]')
                audit.change('MM_NUMBER',p+f'[2][{j}]',before,data[j],'Campo numerico nativo 2.3 de medida de mejora')
    return output


def convert_measures(measures,economics,profile,audit):
    """Proyecta el grafo completo al esquema 2.3, manteniendo ciclos y referencias.

    El esquema contiene solo nombres de campos contrastados en un nativo 2.3.
    Nunca aporta valores ni resultados de otro edificio. Los calculos conservados
    son caches de origen 3.2 y deben recalcularse con el motor de destino.
    """
    schema=mm_schema();memo={};names=[];keepalive=[]
    required_fields=json.loads((ROOT/'mm_schema_23.json').read_text(encoding='utf-8'))['required_fields']
    group_cls=GlobalRef('MedidasDeMejora.objetoGrupoMejoras','grupoMedidasMejora')
    for i,m in enumerate(measures):
        p=f'medidas_mejora[{i}]'
        require(isinstance(m,CexObject) and m.cls==group_cls,'E_MM_CLASS','Conjunto de medidas desconocido',p)
        require(isinstance(m.state.get('nombre'),str) and m.state['nombre'],
                'E_MM_NAME','Nombre del conjunto vacio',p)
        names.append(m.state['nombre'])
        for key in ('listadoGeneradoresElectricoMM','listadoGeneradoresTermosolarMM'):
            require(empty(m.state.get(key)),'E_MM_GENERATOR','Generador nuevo sin equivalencia 2.3',p+'.'+key)
    require(len(set(names))==len(names),'E_MM_NAME','Conjuntos con nombres duplicados')

    def project(value,path):
        if id(value) in memo:return memo[id(value)]
        if isinstance(value,CexObject):
            cls=value.cls.module+'.'+value.cls.name
            require(cls in schema,'E_MM_CLASS','Clase sin equivalencia 2.3: '+cls,path)
            result=CexObject(value.cls,style=value.style);memo[id(value)]=result
            state=dict(value.state)
            keepalive.append(state)
            extras=set(state)-set(schema[cls])
            if extras:
                # No serializar grafos ciclicos completos dentro del JSON del log.
                audit.omit(path+'.campos_32',sorted(extras),'Campos exclusivos 3.2, fuente original intacta')
            if value.cls==group_cls:
                for key in ('ordenPrioridad','seRecomienda','justificacion'):
                    if key in state:audit.omit(path+'.'+key,state[key],'Metadato nuevo sin casilla 2.3; orden de lista conservado')
                require(isinstance(state.get('mejoras'),list) and len(state['mejoras'])==2,
                        'E_MM_DEFINITION','Definicion de conjunto desconocida',path)
                defs=state['mejoras'];systems=defs[1]
                require(isinstance(systems,list) and len(systems)==3 and isinstance(systems[1],list),
                        'E_MM_DEFINITION','Definicion de instalaciones de mejora desconocida',path)
                state['medidasMejoraEnvolvente']=adapt_measure_definitions(state['medidasMejoraEnvolvente'],audit,path+'.medidasMejoraEnvolvente')
                state['mejoras']=[adapt_measure_definitions(defs[0],audit,path+'.mejoras[0]'),
                                  [systems[0],adapt_systems(systems[1],audit,profile,path+'.mejoras[1][1]'),systems[2]]]
                adapted=adapt_systems([state[k] for k in MM_SYSTEM_KEYS],audit,profile,path+'.sistemasMM')
                for key,entries in zip(MM_SYSTEM_KEYS,adapted):state[key]=entries
            if 'datosInstalaciones' in state:
                state['datosInstalaciones']=adapt_systems(state['datosInstalaciones'],audit,profile,path+'.datosInstalaciones')
            if cls=='datosEdificio.datosEdificio':
                require(len(state['datosGenerales']) in (21,26),'E_MM_GENERAL','Datos generales de mejora desconocidos',path)
                state['datosGenerales']=state['datosGenerales'][:21]
            if cls=='datosEdificio.datosEdificioIniciales':
                keys=[key[:-2] for key in MM_SYSTEM_KEYS]
                adapted=adapt_systems([state[key] for key in keys],audit,profile,path+'.sistemas')
                for key,entries in zip(keys,adapted):state[key]=entries
            if cls=='datosEdificio.Cerramiento' and 'superficieHuecos' not in state:
                state['superficieHuecos']=as_num(state['superficieBruta'],path+'.superficieBruta')-as_num(state['superficieNeta'],path+'.superficieNeta')
                require(state['superficieHuecos']>=-0.00001,'E_MM_AREA','Superficie neta mayor que bruta',path)
            if value.cls.module=='Envolvente.objetosEnvolvente':
                protection=state.get('elementosProteccionSolar');n=profile['window_solar_fields']
                require(isinstance(protection,list) and len(protection) in (n,n+3),'E_SOLAR_FIELDS','Proteccion de hueco mejorado desconocida',path)
                require(all(empty(x) for x in protection[n:]),'E_ACTIVE_SOLAR','Proteccion nueva activa en hueco mejorado',path)
                state['elementosProteccionSolar']=protection[:n]
            missing=set(required_fields.get(cls,()))-set(state)
            require(not missing,'E_MM_FIELD','Faltan campos nativos: '+str(sorted(missing)),path)
            result.state={k:project(v,path+'.'+str(k)) for k,v in state.items() if str(k) in schema[cls]}
            return result
        if isinstance(value,list):
            result=[];memo[id(value)]=result
            result.extend(project(v,f'{path}[{i}]') for i,v in enumerate(value));return result
        if isinstance(value,dict):
            result={};memo[id(value)]=result
            for k,v in value.items():result[project(k,path+'.key')]=project(v,path+'.'+str(k))
            return result
        if isinstance(value,tuple):
            values=[project(v,f'{path}[{i}]') for i,v in enumerate(value)]
            if id(value) not in memo:memo[id(value)]=tuple(values)
            return memo[id(value)]
        require(not isinstance(value,GlobalRef),'E_MM_GLOBAL','Referencia global suelta en medidas',path)
        return value
    output=project(measures,'medidas_mejora');economic=project(economics,'analisis_economico')
    audit.change('MM_CONVERTED','medidas_mejora',names,[m.state['nombre'] for m in output],
                 'Conjuntos, definiciones, equipos, datos economicos y caches adaptados al esquema nativo 2.3')
    if measures:
        audit.event('WARNING','W_MM_RECALCULATE','Resultados de mejoras y amortizaciones conservados como cache de 3.2. Recalcular en CE3X 2.3 antes de emitir informes.',conjuntos=names)
    return output,economic


def transfer(source, template, profile, audit, fix_accents=True):
    audit.stage='adaptar estructuras'
    require(len(source[1])==29 and len(source[2])==26, 'E_SOURCE_SCHEMA',
            'El perfil 3.2 espera 29 campos administrativos y 26 generales')
    if any(not empty(x) for x in source[2][21:]):
        require(all(isinstance(x,(str,bool,int,float)) or x is None for x in source[2][21:]),
                'E_NEW_GENERAL', 'Campos nuevos con estructura no reconocida', 'generales[21:]')
        # La superficie adicional no debe contradecir la superficie comun de 2.3.
        extra_area=source[2][22]
        if not empty(extra_area):
            require(abs(as_num(extra_area,'generales[22]')-as_num(source[2][6],'generales[6]'))<0.005,
                    'E_AREA_32', 'Las dos superficies generales difieren; revisar antes de convertir', 'generales[22]')
        audit.event('WARNING','W_GENERAL_32',
                    'Campos generales exclusivos 3.2 sin casilla en 2.3: registrados en datos_no_transferidos.json. Revisar datos generales al abrir.',
                    path='generales[21:]', values=json_value(source[2][21:]))
    out=copy.deepcopy(source)
    out[0]=copy.deepcopy(template[0])
    audit.change('HEADER','version',source[0],out[0],'Cabecera nativa 2.3 de la plantilla')
    for index,count in ((1,26),(2,21)):
        audit.omit(f'blocks[{index}][{count}:]',source[index][count:],'Campos adicionales 3.2')
        out[index]=copy.deepcopy(source[index][:count])
        audit.change('FIELDS_23',f'blocks[{index}].length',len(source[index]),count,'Longitud nativa 2.3; valores comunes del origen conservados')
    for i,w in enumerate(out[3][1]):
        require(isinstance(w,CexObject),'E_WINDOW_CLASS','Registro de hueco invalido',f'huecos[{i}]')
        for key in profile['window_removed_attributes']:
            if key in w.state:
                audit.omit(f'huecos[{i}].{key}',w.state.pop(key),'Identificador UUID 3.2')
                audit.change('REMOVE_UUID',f'huecos[{i}].{key}','presente','retirado','Retirado identificador de la version nueva')
        protection=w.state.get('elementosProteccionSolar')
        n=profile['window_solar_fields']
        require(isinstance(protection,list) and len(protection) in (n,n+3),
                'E_SOLAR_FIELDS','Proteccion solar de longitud no contrastada',f'huecos[{i}]')
        if len(protection)>n:
            tail=protection[n:]
            audit.omit(f'huecos[{i}].elementosProteccionSolar[{n}:]',tail,'Opciones adicionales 3.2')
            require(all(empty(v) for v in tail),'E_ACTIVE_SOLAR','Hay protecciones solares nuevas activas sin equivalente contrastado',f'huecos[{i}]')
            w.state['elementosProteccionSolar']=protection[:n]
            audit.change('SOLAR_FIELDS',f'huecos[{i}].elementosProteccionSolar.length',len(protection),n,'Retirados tres campos adicionales vacios')
    out[4]=adapt_systems(source[4],audit,profile)
    require(len(source[6])==4,'E_ECONOMIC','Formato economico de origen desconocido')
    out[5],out[6]=convert_measures(source[5],source[6],profile,audit)
    require(len(out[11]) in (7,8),'E_REPORT_FIELDS','Configuracion de informe desconocida')
    if len(out[11])==8:
        require(empty(out[11][7]),'E_REPORT_FIELDS','Campo adicional de informe activo sin equivalencia 2.3','informe[7]')
        audit.omit('informe[7]',out[11][7],'Campo adicional vacio de 3.2')
        out[11]=out[11][:7]
        audit.change('REPORT_FIELDS','informe.length',8,7,'Retirado campo adicional vacio de informe 3.2')
    audit.omit('complementos',list(source[12]),'Configuraciones/resultados de complementos a regenerar')
    out[12]={}
    audit.change('RESET_ADDONS','blocks[12]','configuracion de complementos','reiniciada','Regenerar complementos en CE3X 2.3')
    # Dos bloques reservados observados en ficheros nativos. No se interpretan.
    out[13:15]=copy.deepcopy(template[13:15])
    audit.event('WARNING','W_RESERVED_BLOCKS','Bloques reservados 13/14 conservados de la plantilla nativa; significado interno no verificado.')
    audit.event('WARNING','W_RECALCULATE','El destino requiere apertura, revision y recalculo en CE3X 2.3. No certifica HE0/HE1.')
    return out


def technical_snapshot(blocks):
    # No incluye datos del promotor/tecnico, fotografia, plano, comentarios ni firmas.
    return {'version':str(blocks[0]),'general':json_value(blocks[2][:17]+blocks[2][19:21]),
            'envelope':json_value(blocks[3]),'systems':json_value(blocks[4]),
            'compositions':json_value(blocks[8]),'shadows':json_value(blocks[9]),
            'shadow_names':json_value(blocks[10]),
            'improvements':[{'name':m.state.get('nombre'),
                             'definitions':json_value(m.state.get('mejoras')),
                             'costs':{k:json_value(m.state['analisisEconomico'].state.get(k))
                                      for k in ('inversionInicial','costeMantenimiento','vidaUtil')}}
                            for m in blocks[5] if isinstance(m,CexObject) and 'analisisEconomico' in m.state]}


def check_preservation(src,dst,fix_accents):
    # Transformaciones estructurales aparte, nunca mezclar instalaciones de la plantilla.
    require(json_value(src[1][:26])==json_value(dst[1]),'E_PRESERVATION','Datos administrativos alterados')
    require(json_value(src[2][:21])==json_value(dst[2]),'E_PRESERVATION','Datos generales alterados')
    for index in (7,8,9,10):
        require(typed_value(src[index])==typed_value(dst[index]),'E_PRESERVATION','Bibliotecas, sombras o subgrupos alterados',f'blocks[{index}]')
    require(len(src[3][1])==len(dst[3][1]),'E_PRESERVATION','Numero de huecos alterado')
    for i in (0,2,3):
        require(json_value(src[3][i])==json_value(dst[3][i]),'E_PRESERVATION','Cerramientos, puentes o subgrupos alterados')
    for g in range(min(6,len(src[4]))):
        require(len(src[4][g])==len(dst[4][g]),'E_PRESERVATION','Numero de equipos alterado')
        for a,b in zip(src[4][g],dst[4][g]):
            for index in (1,2,3,4,5,6,7):
                require(json_value(a[index])==json_value(b[index]),'E_PRESERVATION','Datos termicos de instalaciones alterados',f'instalaciones[{g}][{index}]')


def validate_target_classes(blocks):
    # No dejar clases exclusivas de 3.2 en bloques que 2.3 tiene que importar.
    allowed={
        ('Envolvente.objetosEnvolvente','HuecoConocidas'),
        ('Envolvente.objetosEnvolvente','HuecoEstimadas'),
        ('LibreriasCE3X.menuCerramientos','composicionCerramiento'),
    }
    allowed.update(tuple(name.rsplit('.',1)) for name in mm_schema())
    visited=set()
    def visit(value,path):
        if isinstance(value,(CexObject,dict,list,tuple)):
            if id(value) in visited:return
            visited.add(id(value))
        if isinstance(value,CexObject):
            require((value.cls.module,value.cls.name) in allowed,'E_TARGET_CLASS',
                    'Clase sin equivalencia contrastada en 2.3: '+value.cls.module+'.'+value.cls.name,path)
            visit(value.state,path+'.state')
        elif isinstance(value,GlobalRef):
            raise ConversionError('E_TARGET_GLOBAL','Referencia global suelta no admitida',path)
        elif isinstance(value,dict):
            for k,v in value.items():visit(k,path+'.key');visit(v,path+'.'+str(k))
        elif isinstance(value,(list,tuple)):
            for i,v in enumerate(value):visit(v,f'{path}[{i}]')
    for i,value in enumerate(blocks):visit(value,f'blocks[{i}]')


def compare_windows(src,dst,profile):
    for i,(a,b) in enumerate(zip(src[3][1],dst[3][1])):
        expected=copy.deepcopy(a.state)
        for key in profile['window_removed_attributes']:expected.pop(key,None)
        expected['elementosProteccionSolar']=expected['elementosProteccionSolar'][:profile['window_solar_fields']]
        require(a.cls==b.cls and a.style==b.style and typed_value(expected)==typed_value(b.state),
                'E_PRESERVATION','Propiedades o tipo de hueco alterados',f'huecos[{i}]')


@dataclass
class ConversionAttempt:
    source: Path
    output: Path
    audit: Audit
    manifest: dict
    artifacts: dict = field(default_factory=dict)
    summary: str = ''
    traceback_text: str = ''

    def export_diagnostic(self, destination, notes='', attachment=None, overwrite=False):
        """Write diagnostic data only after an explicit user request."""
        destination = Path(destination).resolve()
        require(destination.suffix.lower() == '.zip', 'E_DIAGNOSTIC_PATH', 'El diagnostico debe guardarse como ZIP')
        protected = {self.source, self.output, Path(self.manifest['template'])}
        require(destination not in protected, 'E_OVERWRITE', 'El diagnostico coincide con un archivo del proyecto')
        files = dict(self.artifacts)
        files.update({
            'conversion.log': self.audit.log_text(),
            'eventos.json': json_text(self.audit.events),
            'cambios.json': json_text(self.audit.changes),
            'datos_no_transferidos.json': json_text(self.audit.omitted),
            'resultado.json': json_text(self.manifest),
        })
        if self.traceback_text:
            files['traceback.txt'] = self.traceback_text
        observation = {'date': dt.datetime.now().astimezone().isoformat(), 'notes': notes}
        if attachment:
            attached = Path(attachment).resolve()
            require(attached.is_file(), 'E_EXTERNAL_LOG', 'El archivo adjunto no existe')
            require(attached.stat().st_size <= MAX_BYTES, 'E_EXTERNAL_LOG', 'El archivo adjunto supera 64 MiB')
            contents = attached.read_bytes()
            name = 'adjunto' + attached.suffix[:12]
            files['errores_CE3X/' + name] = contents
            observation.update(original_name=attached.name, attached_name=name,
                               sha256=hashlib.sha256(contents).hexdigest())
        if notes or attachment:
            files['errores_CE3X/observacion.json'] = json_text(observation)
        files['LEEME_RESULTADO.txt'] = (
            'CONVERSOR CE3X ' + VERSION + '\n\n' + self.summary + '\n\n'
            'Estado: ' + self.manifest['status'] + '\n'
            'Salida: ' + str(self.output) + '\n\n'
            'Revisar y recalcular el edificio, las mejoras y el analisis economico en CE3X 2.3.\n'
            'Los resultados guardados proceden del origen 3.2 y no se han recalculado en destino.\n'
            'Este ZIP puede contener datos tecnicos del proyecto y los adjuntos seleccionados.\n'
        )
        # No folder, log or ZIP is created before this explicit export operation.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(prefix='.ce3x_diagnostico_', suffix='.partial',
                                             dir=destination.parent, delete=False) as stream:
                temporary = Path(stream.name)
            with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
                for name, contents in sorted(files.items()):
                    archive.writestr(name, contents)
            publish_file(temporary, destination, overwrite)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return destination


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def output_path(source):
    source = Path(source).resolve()
    return source.with_name(source.stem + '_CE3X2.3.cex')


def publish_file(temporary, destination, overwrite=False):
    if overwrite:
        os.replace(temporary, destination)
    elif os.name == 'nt':
        # Windows rename refuses to replace an existing destination, including on FAT.
        os.rename(temporary, destination)
    else:
        # Atomic no-replace publication on POSIX, including concurrent conversions.
        os.link(temporary, destination)
        temporary.unlink()


def convert(source, template, profile_path=None, fix_accents=True, overwrite=False):
    source, template = Path(source).resolve(), Path(template).resolve()
    destination = output_path(source)
    audit = Audit()
    manifest = {'app_version': VERSION, 'python': platform.python_version(),
                'platform': platform.platform(), 'started': dt.datetime.now().astimezone().isoformat(),
                'source': str(source), 'template': str(template), 'output': str(destination),
                'application_verified': False, 'fix_literal_accents': True}
    attempt = ConversionAttempt(source, destination, audit, manifest)
    status, exit_code = 'ERROR', 1
    temporary = None
    try:
        audit.stage = 'comprobar entradas'
        require(source.is_file(), 'E_SOURCE', 'No existe el archivo de origen', str(source))
        require(template.is_file(), 'E_TEMPLATE', 'No existe la plantilla 2.3', str(template))
        require(destination not in (source, template), 'E_OVERWRITE', 'La salida coincide con una entrada')
        require(overwrite or not destination.exists(), 'E_OUTPUT_EXISTS',
                'Ya existe el archivo de salida. Confirma su sustitucion para continuar.', str(destination))
        profile_path = Path(profile_path) if profile_path else ROOT / 'profile.json'
        profile_bytes = profile_path.read_bytes()
        profile = json.loads(profile_bytes)
        schema_bytes = (ROOT / 'mm_schema_23.json').read_bytes()
        manifest.update(source_sha256=sha(source), template_sha256=sha(template),
                        profile_sha256=hashlib.sha256(profile_bytes).hexdigest(),
                        profile_version=profile['profile_version'],
                        improvements_schema_sha256=hashlib.sha256(schema_bytes).hexdigest())
        attempt.artifacts.update({'perfil_utilizado.json': profile_bytes,
                                  'esquema_mejoras_23.json': schema_bytes,
                                  'motor_utilizado.py': Path(__file__).read_bytes()})
        audit.event('INFO', 'START', 'Inicio de conversion; archivos de entrada solo lectura',
                    version=VERSION, python=platform.python_version(), platform=platform.platform(),
                    string_encoding='latin1', scanner='protocol0_ops')
        src = read_cex(source, audit, 'origen')
        require(str(src[0]) == profile['source_header'], 'E_SOURCE_VERSION', f'Version no compatible: {src[0]}')
        native = read_cex(template, audit, 'plantilla')
        require(str(native[0]) == profile['target_header'], 'E_TEMPLATE_VERSION', f'La plantilla no es CE3X 2.3 Residencial: {native[0]}')
        require(len(native[1]) == 26 and len(native[2]) == 21 and len(native[4]) == 12,
                'E_TEMPLATE_SCHEMA', 'La plantilla 2.3 tiene una estructura inesperada')
        attempt.artifacts['modelo_origen_tecnico.json'] = json_text(technical_snapshot(src))
        src = repair_text(src, audit, 'blocks')
        validate(src, audit, profile)
        dst = transfer(src, native, profile, audit, fix_accents)
        validate(dst, audit, profile, target=True)
        check_preservation(src, dst, fix_accents)
        compare_windows(src, dst, profile)
        validate_target_classes(dst)
        attempt.artifacts['modelo_destino_tecnico.json'] = json_text(technical_snapshot(dst))
        audit.stage = 'escribir y releer'
        with tempfile.NamedTemporaryFile(prefix='.ce3x_conversion_', suffix='.partial',
                                         dir=source.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(encoded(dst))
        reread = read_cex(temporary, audit, 'relectura')
        require(typed_value(dst) == typed_value(reread), 'E_ROUNDTRIP',
                'La relectura ha cambiado valores, clases o tipos STRING/UNICODE')
        # Check both originals before making the validated result visible.
        for name, path in (('source', source), ('template', template)):
            require(path.is_file() and sha(path) == manifest[name + '_sha256'], 'E_INPUT_CHANGED',
                    'Una entrada ha cambiado durante el proceso; repetir con CE3X cerrado.', str(path))
        try:
            publish_file(temporary, destination, overwrite)
        except FileExistsError as exc:
            raise ConversionError('E_OUTPUT_EXISTS', 'Ya existe el archivo de salida.', str(destination)) from exc
        manifest.update(output_sha256=sha(destination), structural_validation=True,
                        envelope_count=len(dst[3][0]), window_count=len(dst[3][1]), bridge_count=len(dst[3][2]),
                        improvement_count=len(dst[5]), improvement_names=[m.state['nombre'] for m in dst[5]],
                        cached_results_origin_version='3.2', target_results_recalculated=False)
        audit.event('INFO', 'ROUNDTRIP_OK', '15 bloques releidos; clases, acentos, valores y tipos conservados')
        status, exit_code = 'REVISAR', 0
        attempt.summary = (f'Archivo generado. {len(dst[3][0])} cerramientos, {len(dst[3][1])} huecos, '
                           f'{len(dst[3][2])} puentes y {len(dst[5])} conjuntos de mejora. '
                           'Revisar y recalcular en CE3X 2.3.')
    except Exception as exc:
        code, path = (exc.code, exc.path) if isinstance(exc, ConversionError) else ('E_UNEXPECTED', '')
        audit.event('ERROR', code, str(exc), path=path, exception_type=type(exc).__name__)
        attempt.traceback_text = traceback.format_exc()
        manifest.update(structural_validation=False, error_code=code, error_path=path,
                        error_message=str(exc), error_stage=audit.stage)
        attempt.summary = code + ': ' + str(exc)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        manifest.update(status=status, finished=dt.datetime.now().astimezone().isoformat())
    return exit_code, attempt


def serve(stream_in=None, stream_out=None):
    """Keep the last attempt in memory until the GUI requests an export or closes."""
    stream_in, stream_out = stream_in or sys.stdin, stream_out or sys.stdout
    last_attempt = None
    def reply(status, path, message):
        clean = lambda text: str(text).replace('\t', ' ').replace('\r', ' ').replace('\n', ' ')
        stream_out.write('\t'.join(map(clean, (status, path, message))) + '\n')
        stream_out.flush()
    for line in stream_in:
        try:
            request = json.loads(line)
            command = request['command']
            if command == 'exit':
                return
            if command == 'convert':
                code, last_attempt = convert(request['source'], request.get('template', ROOT / 'plantilla_23.cex'),
                                             overwrite=request.get('overwrite', False))
                reply(last_attempt.manifest['status'], last_attempt.output if not code else '', last_attempt.summary)
            elif command == 'diagnostic':
                require(last_attempt is not None, 'E_RUN', 'Primero realiza una conversion')
                path = last_attempt.export_diagnostic(request['destination'], request.get('notes', ''),
                                                      request.get('attachment'), request.get('overwrite', False))
                reply('GUARDADO', path, 'Diagnostico guardado. Revisa su contenido antes de compartirlo.')
            elif command == 'self-test':
                self_test()
                reply('OK', '', 'Motor y codificacion correctos')
            else:
                raise ConversionError('E_COMMAND', 'Operacion no reconocida')
        except Exception as exc:
            reply('ERROR', '', str(exc))



def self_test():
    fixture=[LegacyString('Partición superior'), 'Partición superior',
             {'Sin patrón':CexObject(GlobalRef('Envolvente.objetosEnvolvente','HuecoConocidas'),{LegacyString('descripcion'):'Vñ'})}]
    raw=encoded([fixture])
    result=InertUnpickler(io.BytesIO(raw.replace(b'\r\n',b'\n')),encoding='latin1').load()
    require(typed_value(result)==typed_value(fixture),'E_SELFTEST','Fallo en caracteres o tipos')
    for literal in (b"S'Partici\xf3n y ni\xf1o'\n.", b"S'Partici\\xf3n y ni\\xf1o'\n."):
        inspected=list(protocol0_ops(literal))
        require(inspected[0][1]=='Partición y niño' and inspected[-1][0].name=='STOP',
                'E_SELFTEST','Fallo en inspeccion STRING Latin-1')
    hostile=b"cos\nsystem\n(S'echo no_debe_ejecutarse'\ntR."
    try:
        InertUnpickler(io.BytesIO(hostile),encoding='latin1').load()
    except ConversionError:
        return
    raise ConversionError('E_SELFTEST','El lector ha admitido una funcion arbitraria')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Conversor experimental CE3X 3.2 a 2.3 residencial')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('convert')
    p.add_argument('--source', required=True)
    p.add_argument('--template', default=str(ROOT / 'plantilla_23.cex'))
    p.add_argument('--profile')
    p.add_argument('--overwrite', action='store_true', help='Sustituir expresamente una salida existente')
    p.add_argument('--diagnostic', help='Guardar un ZIP de diagnostico expresamente en esta ruta')
    p.add_argument('--fix-accents', action='store_true', default=True, help=argparse.SUPPRESS)
    sub.add_parser('self-test')
    sub.add_parser('serve')
    a = parser.parse_args(argv)
    try:
        if a.command == 'self-test':
            self_test()
            return 0
        if a.command == 'serve':
            serve()
            return 0
        code, attempt = convert(a.source, a.template, a.profile, a.fix_accents, a.overwrite)
        print(attempt.summary)
        if not code:
            print(attempt.output)
        if a.diagnostic:
            print(attempt.export_diagnostic(a.diagnostic))
        return code
    except Exception as exc:
        print('Error: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
