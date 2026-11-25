"""Conversor experimental CE3X 3.2 -> 2.3, motor sin dependencias externas.
No importa clases de CE3X ni ejecuta funciones contenidas en los pickle.
"""
from __future__ import annotations
import argparse
import base64
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

VERSION = '1.6.1'
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


def inactive(value):
    return value is None or value == '' or isinstance(value, (list, tuple)) and all(inactive(x) for x in value)


def scalar(value):
    return value is None or isinstance(value, (str, int, float, Decimal))


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


def check_native_number(value, path, audit, minimum=None):
    """Comprueba sin modificar ni bloquear un dato comun que solo se transfiere."""
    try:
        return as_num(value, path, minimum)
    except ConversionError as exc:
        audit.event('WARNING', 'W_NATIVE_VALUE',
                    'Dato original conservado sin corregir; revisar en CE3X 2.3: '+str(exc),
                    path=path, value=json_value(value))
        return None


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

    def omit(self, path, value, reason, *, risk='formato', element=None,
             dependencies='Ninguna referencia nativa retirada', count=1, operation='omitir'):
        if isinstance(value, CexObject) or isinstance(value, list) and any(isinstance(v, CexObject) for v in value):
            snapshot = typed_value(value)
        else:
            snapshot = json_value(value)
        self.omitted.append({'path': path, 'value': snapshot, 'reason': reason,
                             'risk': risk, 'element': element or path, 'dependencies': dependencies,
                             'count': count, 'operation': operation, 'destination': 'CE3X 2.3'})

    def loss(self, path, value, reason, *, risk='modelo', **details):
        self.omit(path, value, reason, risk='formato' if inactive(value) else risk, **details)

    @property
    def losses(self):
        return [item for item in self.omitted if item['risk'] in ('modelo', 'usuario')]

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
    check_native_number(blocks[2][6],'generales.superficie',audit,minimum=.01)
    check_native_number(blocks[2][7],'generales.altura',audit,minimum=.01)
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
        check_native_number(e[2],p+'.superficie',audit,minimum=0)
        check_native_number(e[3],p+'.U',audit,minimum=0)
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
        check_native_number(state['superficie'],p+'.superficie',audit,minimum=0)
        for key in ('Uvidrio','Umarco','Gvidrio'):
            if key in state: check_native_number(state[key],p+'.'+key,audit,minimum=0)
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
        check_native_number(b[3],p+'.psi',audit)
        check_native_number(b[4],p+'.longitud',audit,minimum=0)
    audit.event('INFO','MODEL_COUNTS','Inventario validado',cerramientos=len(env),huecos=len(windows),puentes=len(bridges),subgrupos=len(subs))


def adapt_systems(source, audit, profile, path_prefix='instalaciones'):
    require(len(source) in (12,14),'E_SYSTEM_GROUPS',f'Numero de grupos no reconocido: {len(source)}')
    if len(source)>12:
        extra=source[12:]
        active = [(12+i, x) for i,x in enumerate(extra) if not empty(x)]
        electrical = isinstance(extra[1], list) and any(
            isinstance(row, CexObject) and row.cls == GlobalRef('models', 'GeneradorElectrico')
            for row in extra[1])
        require(not active, 'E_NEW_SYSTEM',
                'Grupos de instalaciones sin omision segura: ' + ', '.join(
                    f'{i} ({len(x) if isinstance(x, list) else 1}): ' + ', '.join(
                        str(row.state.get('nombre', row.cls.name)) if isinstance(row, CexObject)
                        else str(row[0]) if isinstance(row, list) and row else type(row).__name__
                        for row in (x if isinstance(x, list) else [x])) for i,x in active)
                + ('. Generacion electrica mensual: falta autoconsumo computable por servicio contrastado en 2.3.'
                   if electrical else ''), path_prefix+'[12:]')
        audit.omit(path_prefix+'[12:]',extra,'Grupos nuevos vacios de CE3X 3.2 sin equivalente contrastado', count=2)
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
                if g in (8, 9):
                    raise ConversionError('E_SYSTEM_UNSUPPORTED',
                        f'{entry[0] if entry else "Equipo"}: ventilacion o ventiladores activos. '
                        'Los campos de aire primario y ventiladores de 2.3 son para uso terciario. '
                        'Reducir la renovacion residencial no conserva caudal, recuperacion y consumo.',p)
                raise ConversionError('E_SYSTEM_UNSUPPORTED','Grupo activo sin regla contrastada; se necesita muestra nativa 2.3',p)
            require(len(entry) in (10,11),'E_SYSTEM_ROW',f'Esperados 10/11 campos; hay {len(entry)}',p)
            require(entry[1] in ('ACS','calefaccion','refrigeracion','climatizacion','mixto2','mixto3'),
                    'E_SYSTEM_TYPE',f'Tipo de instalacion no contrastado: {entry[1]}',p)
            if len(entry)==11:
                removed=entry.pop(9)
                require(isinstance(removed,list) and len(removed)==3 and all(scalar(x) for x in removed),
                        'E_SYSTEM_TAIL','Campo adicional de instalacion inesperado',p+'[9]')
                audit.loss(p+'[9]',removed,'Tres campos adicionales de instalacion 3.2',
                           element=str(entry[0]), count=sum(not inactive(x) for x in removed),
                           dependencies='Rendimiento y cobertura comunes conservados; revisar la instalacion')
                audit.change('SYSTEM_FIELD',p+'.length',11,10,'Adaptado registro de instalacion al formato nativo 2.3')
            require(isinstance(entry[-1],str),'E_SYSTEM_SUBGROUP','Subgrupo de instalacion no valido',p)
            accumulation=entry[8]
            if isinstance(accumulation, list) and accumulation and accumulation[0] is True:
                tank = p+'[8]'
                require(len(accumulation) >= 6 and all(scalar(field) for field in accumulation),
                        'E_SYSTEM_TAIL', 'Deposito ACS de estructura desconocida', tank)
                mode = accumulation[5]
                require((mode == 'Conocido' and len(accumulation) == 6)
                        or (mode == 'Por defecto' and len(accumulation) in (6, 7))
                        or (mode == 'Estimado' and len(accumulation) == 9),
                        'E_SYSTEM_TAIL', 'Metodo o campos del deposito ACS sin correspondencia nativa 2.3', tank)
                volume = check_native_number(accumulation[1], tank+'.volumen', audit, minimum=0)
                high = check_native_number(accumulation[2], tank+'.consigna_alta', audit)
                low = check_native_number(accumulation[3], tank+'.consigna_baja', audit)
                check_native_number(accumulation[4], tank+'.UA', audit, minimum=0)
                if (volume is not None and volume <= 0
                        or high is not None and low is not None and high < low):
                    audit.event('WARNING', 'W_NATIVE_VALUE',
                                'Volumen o consignas del deposito incoherentes; se conservan los datos originales.',
                                path=tank)
                if mode == 'Estimado':
                    check_native_number(accumulation[6], tank+'.espesor_aislamiento', audit, minimum=0)
                    if not isinstance(accumulation[7], str) or not accumulation[7].strip():
                        audit.event('WARNING', 'W_NATIVE_VALUE',
                                    'Material de aislamiento incompleto; se conserva el dato original.',
                                    path=tank+'.material_aislamiento')
                if len(accumulation) in (7, 9) and not empty(accumulation[-1]):
                    multiplier = check_native_number(accumulation[-1], tank+'.multiplicador', audit, minimum=0)
                    if multiplier == 0:
                        audit.event('WARNING', 'W_NATIVE_VALUE',
                                    'Multiplicador nulo; se conserva el dato original.', path=tank+'.multiplicador')
                audit.event('INFO','DHW_ACCUMULATION','Deposito ACS conservado en el formato nativo.',path=tank,mode=mode)
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


MM_METADATA = {'ordenPrioridad', 'seRecomienda', 'justificacion'}
MM_GENERATORS = {'listadoGeneradoresElectricoMM', 'listadoGeneradoresTermosolarMM',
                 'listadoGeneradoresElectrico', 'listadoGeneradoresTermosolar'}
MM_MONTHLY_CACHE = {'coeficientesACS', 'coeficientesCal', 'coeficientesIlum',
                    'coeficientesRef', 'repartoMensualDdaCal', 'repartoMensualDdaRef'}
MM_LIBRARIES = {
    'listadoEspacios': 'Espacio', 'listadoMarco': 'Marco', 'listadoVidrio': 'Vidrio',
    'listadoMateriales': 'Material', 'listadoSombras': 'Sombra',
    'listadoSistemasConstructivos': 'SistemaConstructivo',
    'listadoSistemasConstructivosHuecos': 'SistemaConstructivoHueco',
}
MM_EMPTY_SYSTEMS = {'listadoBombas', 'listadoIluminacion', 'listadoTorresRefrigeracion',
                    'listadoVentilacion', 'listadoVentiladores'}
MM_SYSTEM_EXTRAS = {
    'datosEdificio.EquipoGeneracion': {'caracteristicaBdC', 'consumoMensual',
                                       'consumoMensualMedioAmbiente', 'esFicticio', 'servicio'},
    'datosEdificio.ContribucionesEnergeticas': {'ddaACS', 'generacionMensual', 'consumoMensual',
                                                'enFinalACS', 'potencia', 'esGenerador'},
    'datosEdificio.Cerramiento': {'nombreSistemaConstructivo'},
    'datosEdificio.PuenteTermico': {'modoDeObtencion'},
}
MM_RESULT_FIELDS = {'consumoMensual', 'consumoMensualMedioAmbiente', 'generacionMensual',
                    'ddaACS', 'enFinalACS', 'esFicticio'}


def audit_measure_extra(audit, cls, key, value, path, element):
    if (cls == 'MedidasDeMejora.objetoGrupoMejoras.grupoMedidasMejora'
            and key in MM_METADATA and scalar(value)):
        audit.loss(path, value, 'Metadato del conjunto de mejora', risk='usuario', element=element,
                   dependencies='Se conservan el conjunto, su posicion y sus costes')
    elif (cls == 'datosEdificio.datosEdificioIniciales' and key in MM_LIBRARIES
          and isinstance(value, list)
          and all(isinstance(row, CexObject) and row.cls == GlobalRef('models', MM_LIBRARIES[key])
                  for row in value)):
        audit.loss(path, value, 'Biblioteca auxiliar en el modelo calculado de la mejora',
                   risk='usuario', element=element, count=len(value),
                   dependencies='Se conserva la envolvente comun; revisar la mejora y recalcular')
    elif (cls == 'datosEdificio.datosEdificio' and key in MM_MONTHLY_CACHE
          and isinstance(value, list) and len(value) == 12 and all(scalar(x) for x in value)):
        audit.omit(path, value, 'Serie mensual de resultados a recalcular', risk='cache', element=element)
    elif (cls == 'datosEdificio.datosEdificioResultados' and key in ('datosInstCompletoCal', 'datosInstCompletoRef')
          and isinstance(value, CexObject) and value.cls == GlobalRef('datosEdificio', 'ListadoEquipoGeneracion')):
        audit.omit(path, value, 'Resultado de instalaciones a recalcular', risk='cache', element=element)
    elif (key in {'id', 'idEspacio', 'idSistemaConstructivo'}
          and (cls in MM_SYSTEM_EXTRAS or cls.startswith('Envolvente.objetosEnvolvente.'))
          and (value is None or isinstance(value, CexObject) and value.cls == GlobalRef('uuid', 'UUID')
               and set(value.state) == {'int'} and type(value.state['int']) is int)):
        audit.omit(path, value, 'Identificador interno sin casilla nativa', element=element)
    elif key in MM_SYSTEM_EXTRAS.get(cls, ()) and (
            scalar(value) or isinstance(value, list) and all(scalar(x) for x in value)):
        if key in MM_RESULT_FIELDS:
            audit.omit(path, value, 'Resultado de la mejora a recalcular', risk='cache', element=element)
        else:
            audit.loss(path, value, 'Dato del modelo calculado de la mejora', element=element,
                       dependencies='Se conservan los campos comunes del modelo; revisar la mejora y recalcular')
    elif (cls in ('MedidasDeMejora.objetoGrupoMejoras.grupoMedidasMejora', 'datosEdificio.datosEdificioIniciales')
          and key in MM_GENERATORS | MM_EMPTY_SYSTEMS and empty(value)):
        audit.omit(path, value, 'Grupo adicional vacio', element=element)
    else:
        raise ConversionError('E_MM_FIELD', f'{element}: campo sin omision segura {cls}.{key}', path)


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
        elif item[1]=='Mejora de Puentes Térmicos':
            require(len(data)==20, 'E_MM_DEFINITION', 'Mejora de puentes con campos desconocidos', p)
            for j in range(0, 20, 2):
                require(isinstance(data[j], bool), 'E_MM_DEFINITION', 'Seleccion de puente no booleana', p+f'[2][{j}]')
                if data[j] or not empty(data[j+1]):
                    check_native_number(data[j+1], p+f'[2][{j+1}]', audit)
            # Los ejemplos nativos 2.3 conservan estos valores como texto.
            indices=()
        else:
            raise ConversionError('E_MM_DEFINITION','Tipo de medida sin regla contrastada: '+str(item[1]),p)
        for j in indices:
            if isinstance(data[j],str) and data[j]!='':
                before=data[j];number=check_native_number(before,p+f'[2][{j}]',audit)
                if number is None: continue
                data[j]=number
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

    def project(value,path,element='Analisis economico'):
        if id(value) in memo:return memo[id(value)]
        if isinstance(value,CexObject):
            cls=value.cls.module+'.'+value.cls.name
            require(cls in schema,'E_MM_CLASS','Clase sin equivalencia 2.3: '+cls,path)
            result=CexObject(value.cls,style=value.style);memo[id(value)]=result
            state=dict(value.state)
            keepalive.append(state)
            extras=set(state)-set(schema[cls])
            if value.cls==group_cls:
                element = state['nombre']
            for key in sorted(extras, key=str):
                audit_measure_extra(audit, cls, key, state[key], path+'.'+str(key), element)
            if value.cls==group_cls:
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
                audit_general_fields(state['datosGenerales'], audit, path+'.datosGenerales', element)
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
                if len(protection)>n:
                    audit.omit(path+'.elementosProteccionSolar[25:]', protection[n:], 'Proteccion nueva inactiva', element=element)
                state['elementosProteccionSolar']=protection[:n]
            missing=set(required_fields.get(cls,()))-set(state)
            require(not missing,'E_MM_FIELD','Faltan campos nativos: '+str(sorted(missing)),path)
            result.state={k:project(v,path+'.'+str(k),element) for k,v in state.items() if str(k) in schema[cls]}
            return result
        if isinstance(value,list):
            result=[];memo[id(value)]=result
            result.extend(project(v,f'{path}[{i}]',element) for i,v in enumerate(value));return result
        if isinstance(value,dict):
            result={};memo[id(value)]=result
            for k,v in value.items():result[project(k,path+'.key',element)]=project(v,path+'.'+str(k),element)
            return result
        if isinstance(value,tuple):
            values=[project(v,f'{path}[{i}]',element) for i,v in enumerate(value)]
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


SOLAR_MONTHS = ('enero','febrero','marzo','abril','mayo','junio',
                'julio','agosto','septiembre','octubre','noviembre','diciembre')
SOLAR_FIELDS = set(SOLAR_MONTHS) | {'nombre','zona','potencia','id','servicio','tipo','consumoMensual'}
# Coinciden para las variantes peninsular y extrapeninsular de ambos motores.
ACS_TEMPERATURES = {
    'A3':15.5, 'A4':15.7, 'B3':14.9, 'B4':15.4, 'C1':12.6, 'C2':13.4,
    'C3':13.4, 'C4':14.4, 'D1':11.2, 'D2':11.7, 'D3':12.8, 'E1':10.4,
}


def solar_key(generator):
    require(isinstance(generator,CexObject) and generator.cls == GlobalRef('models','GeneradorTermosolar'),
            'E_SOLAR_SCHEMA','Clase de generador solar desconocida')
    state = generator.state
    require(set(state) <= SOLAR_FIELDS and set(SOLAR_MONTHS) | {'nombre', 'zona', 'potencia'} <= set(state)
            and all(scalar(state[k]) for k in set(state) - {'id', 'consumoMensual'})
            and (state.get('consumoMensual') is None or isinstance(state['consumoMensual'], list)
                 and all(scalar(x) for x in state['consumoMensual'])),
            'E_SOLAR_SCHEMA', 'Campos de generador solar desconocidos: '+str(state.get('nombre', '')))
    ident=generator.state.get('id')
    if isinstance(ident,CexObject) and ident.cls == GlobalRef('uuid','UUID') and type(ident.state.get('int')) is int:
        return str(ident.state['int'])
    require(ident is None, 'E_SOLAR_SCHEMA', 'Identificador de generador solar desconocido')
    return hashlib.sha256(json_text(json_value(generator)).encode('utf-8')).hexdigest()


def solar_candidate(generators, systems, general, envelope_changes=False):
    """Project one supported DHW generator, flagging configurations beyond the native comparison."""
    try:
        require(len(generators)==1,'E_SOLAR_SCOPE','Solo se ha validado un generador por instalacion')
        g=generators[0]
        require(g.cls==GlobalRef('models','GeneradorTermosolar'),'E_SOLAR_SCOPE','Clase solar no validada')
        s=g.state
        require(not set(s)-SOLAR_FIELDS,'E_SOLAR_SCOPE','Campos solares nuevos no validados')
        require(s.get('servicio') in (None,'ACS') and s.get('tipo') in (None,'Otro'),
                'E_SOLAR_SCOPE','Servicio o tipo solar no validado')
        require(s.get('zona')=='Edificio Objeto','E_SOLAR_SCOPE','Solar asignada a una zona no validada')
        zone = general[4]
        require(zone in ACS_TEMPERATURES, 'E_SOLAR_SCOPE',
                'Temperatura de red sin criterio contrastado para la zona '+str(zone))
        require(len(systems[0])==1 and not any(group for i, group in enumerate(systems) if i not in (0,12)),
                'E_SOLAR_SCOPE','Solo se ha ensayado un equipo de ACS sin otras instalaciones ni contribuciones')
        acs=systems[0][0]
        require(acs[1]=='ACS' and acs[3]=='Efecto Joule' and acs[4]=='Electricidad'
                and str(acs[6]).startswith('Conocido') and acs[-1]=='Edificio Objeto',
                'E_SOLAR_SCOPE','Solo se ha ensayado ACS electrico de efecto Joule conocido')
        require(as_num(acs[2][0],'solar.rendimiento')==100 and as_num(acs[5][0][1],'solar.cobertura')==100,
                'E_SOLAR_SCOPE','Rendimiento y cobertura deben ser 100 %')
        require(isinstance(acs[8],list) and acs[8] and acs[8][0] is False
                and all(empty(value) for value in acs[8][1:]),
                'E_SOLAR_SCOPE','No se ha validado ACS con acumulacion')
        flow=as_num(general[9],'solar.ACS',minimum=0)
        area=as_num(general[6],'solar.area',minimum=0)
        require(flow > 0 and area > 0, 'E_SOLAR_SCOPE', 'Demanda diaria de ACS y superficie deben ser positivas')
        require(as_num(acs[5][0][0],'solar.superficie_cubierta') == area,
                'E_SOLAR_SCOPE','La superficie cubierta declarada contradice la cobertura total de ACS')
        extra_area = (as_num(general[22], 'solar.superficie_adicional', minimum=0)
                      if len(general) > 22 and not empty(general[22]) else None)
        require(empty(s.get('consumoMensual')), 'E_SOLAR_SCOPE',
                'El generador declara un consumo mensual separado sin representacion contrastada')
        params = {'zona':zone, 'area_m2':area, 'acs_litros_dia':flow, 'dias':360,
                  'calor_especifico_kj_kg_k':4.18, 'temperatura_acs_c':60.0,
                  'temperatura_agua_fria_c':ACS_TEMPERATURES[zone]}
        demand = (params['dias'] * params['calor_especifico_kj_kg_k'] * flow
                  * (params['temperatura_acs_c'] - params['temperatura_agua_fria_c']) / 3600)
        monthly = {m:as_num(s[m],'solar.'+m,minimum=0) for m in SOLAR_MONTHS}
        production=sum(monthly.values())
        power=as_num(s['potencia'],'solar.potencia',minimum=0)
        require(math.isfinite(demand) and math.isfinite(production),'E_SOLAR_SCOPE','Balance anual no finito')
        require(0<production<=demand,'E_SOLAR_SCOPE','Produccion nula o superior a la demanda anual; caso no validado')
        return {'percent':production/demand*100,'production':production,'demand':demand,
                'experimental': envelope_changes or (zone, area, flow) != ('D2', 100, 100) or extra_area not in (None, area),
                'entrada': {'parametros':params, 'produccion_mensual_kwh': monthly, 'potencia_original': power},
                'formula': '100 * suma(produccion_mensual_kwh) / demanda_acs_anual_kwh',
                'evidencia': 'docs/VALIDACION_SOLAR.md'},''
    except (ConversionError,KeyError,TypeError,IndexError) as exc:
        return None,str(exc)


def neutral_legacy_protection(values):
    baseline=['']*6+[['',0,0],['',0,0],'',False,False,'',False,False,'','','',False,False,False,False,False,False,False,['','']]
    return isinstance(values,list) and values==baseline


def window_protection_issues(source):
    indices=[]
    factors = []
    for i,w in enumerate(source[3][1]):
        values=w.state.get('elementosProteccionSolar')
        if not isinstance(values,list) or len(values)!=28 or all(empty(v) for v in values[25:]):continue
        tail=values[25:]
        require(tail[0] is True and all(isinstance(v,str) and len(v)<=128 for v in tail[1:]),
                'E_ACTIVE_SOLAR','Campos de proteccion solar 3.2 no reconocidos',f'huecos[{i}]')
        require(neutral_legacy_protection(values[:25]) and w.state.get('patronSombras','Sin patrón') in ('','Sin patrón'),
                'E_ACTIVE_SOLAR','Proteccion nueva combinada con otras sombras: no se ha validado su omision',f'huecos[{i}]')
        require(isinstance(w.state.get('tieneProteccionSolar'),bool),
                'E_ACTIVE_SOLAR','Indicador de proteccion solar desconocido',f'huecos[{i}]')
        solar_factors = {}
        for field, label in zip(('correctorFSCTE','correctorFSInvierno','correctorFSVerano'),
                                ('CTE','invierno','verano')):
            require(field in w.state,'E_ACTIVE_SOLAR','Falta un factor solar necesario para omitir la proteccion',f'huecos[{i}].{field}')
            solar_factors[label] = as_num(w.state[field],f'huecos[{i}].{field}',minimum=0)
        indices.append(i)
        if (tail[1] == 'Manuales' and tail[2].strip() and w.state['tieneProteccionSolar']
                and all(v <= 1 for v in solar_factors.values())):
            factors.append(dict(solar_factors, hueco=w.state['descripcion'], color=tail[2]))
    if not indices:return []
    require(not source[5],'E_ACTIVE_SOLAR','Protecciones nuevas con medidas de mejora: falta contrastar sus copias y referencias')
    active=sum(source[3][1][i].state['tieneProteccionSolar'] for i in indices)
    names=', '.join(str(source[3][1][i].state.get('descripcion',i+1)) for i in indices)
    candidate = {'experimental': True, 'factores': factors} if len(factors) == len(indices) else None
    experiment = ('ADAPTACION EXPERIMENTAL: sustituye las persianas manuales por Otros. '
                  'Conserva los dos factores estacionales guardados. El corrector CTE pasa a 1. '
                  'Se pierden el tipo de dispositivo y su color. '
                  'Valores originales (CTE, invierno, verano): ' +
                  '; '.join(f"{v['hueco']} ({v['color']}): {v['CTE']}, {v['invierno']}, {v['verano']}" for v in factors)
                  + '. Recalcular y comparar ambos certificados.') if candidate else None
    return [{'id':'window-protection:building','kind':'window_protection','name':'Protecciones solares nuevas en huecos',
             'context':'edificio','candidate':candidate,'window_indices':indices,'experimental_message':experiment,
             'message':f'{len(indices)} huecos tienen configuracion adicional de proteccion solar 3.2 ({active} con la proteccion activada): '+names+'. '
                       'CE3X 2.3 no tiene estos tres campos. '
                       'Omitir elimina SOLO esta proteccion nueva, conserva las ventanas, sus propiedades y los puentes termicos, '
                       'y restablece a 1 los factores solares al no quedar otra proteccion definida. '
                       'Puede cambiar la demanda de refrigeracion. Revisa y recalcula en CE3X 2.3. '
                       'Cancelar no genera salida. El original se conserva.'}]


def electric_generation_issues(source):
    systems = source[4]
    if len(systems) != 14 or empty(systems[13]):
        return []
    generators = systems[13]
    require(isinstance(generators, list) and all(
        isinstance(g, CexObject) and g.cls == GlobalRef('models', 'GeneradorElectrico') for g in generators),
        'E_NEW_SYSTEM', 'Grupo electrico mensual de formato desconocido', 'instalaciones[13]')
    require(not source[5], 'E_NEW_SYSTEM',
            'Generacion electrica mensual con mejoras: faltan correspondencias para sus copias', 'instalaciones[13]')
    valid_zones = {'Edificio Objeto'} | {z.state.get('nombre') for z in source[7]
                                       if isinstance(z, CexObject) and isinstance(z.state.get('nombre'), str)}
    issues = []
    for i, generator in enumerate(generators):
        path = f'instalaciones[13][{i}]'
        state = generator.state
        require(set(SOLAR_MONTHS) | {'nombre', 'zona', 'potencia'} <= set(state)
                and set(state) <= SOLAR_FIELDS - {'servicio'} and state.get('tipo') is None,
                'E_NEW_SYSTEM', 'Generacion electrica mensual: falta un autoconsumo computable por servicio '
                'con estructura reconocida. Se requiere la serie EPB nativa.', path)
        require(isinstance(state['nombre'], str) and state['nombre'].strip()
                and isinstance(state['zona'], str) and state['zona'] in valid_zones,
                'E_NEW_SYSTEM', 'Nombre o zona del generador electrico no reconocidos', path)
        ident = state.get('id')
        require(ident is None or isinstance(ident, CexObject) and ident.cls == GlobalRef('uuid', 'UUID')
                and set(ident.state) == {'int'} and type(ident.state['int']) is int,
                'E_NEW_SYSTEM', 'Identificador electrico mensual desconocido', path)
        monthly = {m: as_num(state[m], f'{path}.{m}', minimum=0) for m in SOLAR_MONTHS}
        calculated = state.get('consumoMensual')
        require(calculated is None or isinstance(calculated, list) and len(calculated) in (0, 12)
                and (not calculated or [as_num(v, path+'.consumoMensual', minimum=0)
                                       for v in calculated] == list(monthly.values())),
                'E_NEW_SYSTEM', 'El balance mensual calculado no coincide con el autoconsumo EPB declarado', path)
        annual = sum(monthly.values())
        require(math.isfinite(annual), 'E_NEW_SYSTEM', 'Autoconsumo electrico anual no finito', path)
        power = as_num(state['potencia'], f'{path}.potencia', minimum=0)
        name = state['nombre']
        message = f'{name} ({state["zona"]}). Omitir elimina el generador y su autoconsumo de la salida.'
        experiment = (f'{name} ({state["zona"]}). Se propone una contribucion anual de '
                      f'{annual:.12g} kWh de autoconsumo EPB. Se pierden el reparto mensual, la potencia '
                      'y el identificador. El reparto por servicios y su efecto energetico pueden cambiar. '
                      'Recalcular y comparar ambos certificados.')
        issues.append({'id':f'electric:{i}', 'kind':'electric_generation', 'path':path,
                       'name':name, 'context':'edificio', 'message':message, 'experimental_message':experiment,
                       'candidate':{'experimental':True, 'autoconsumo_epb_anual_kwh':annual,
                                    'autoconsumo_epb_mensual_kwh':monthly, 'potencia_original':power,
                                    'zona':state['zona']}})
    return issues


def solar_issues(source):
    issues=window_protection_issues(source) + electric_generation_issues(source)
    contexts=[('edificio',source[4],source[2],False,None)]
    for i,m in enumerate(source[5]):
        if not isinstance(m,CexObject):continue
        defs=m.state.get('mejoras')
        if isinstance(defs,list) and len(defs)==2 and isinstance(defs[1],list) and len(defs[1])==3:
            contexts.append((f'mejora {i+1}: '+str(m.state.get('nombre','')),defs[1][1],source[2],bool(defs[0]),i))
    for context,systems,general,changed,index in contexts:
        if not isinstance(systems,list) or len(systems)!=14 or not systems[12]:continue
        require(isinstance(systems[12],list),'E_SOLAR_SCHEMA','Grupo termosolar desconocido',context)
        require(index is not None or not source[5], 'E_SOLAR_SCHEMA',
                'Termosolar del edificio con mejoras: dependencias sin contraste', context)
        if index is not None:
            measure = source[5][index].state
            copies = measure.get('listadoGeneradoresTermosolarMM')
            require(isinstance(copies, list) and typed_value(copies) == typed_value(systems[12]),
                    'E_SOLAR_SCHEMA','Copias de los generadores de la mejora no coinciden',context)
        candidate,reason=solar_candidate(systems[12],systems,general,changed)
        if candidate and changed:
            if (typed_value(measure.get('medidasMejoraEnvolvente')) != typed_value(measure['mejoras'][0])
                    or measure['mejoras'][1][2] is not True):
                candidate, reason = None, 'Las definiciones de envolvente o instalaciones de la mejora no coinciden'
            for key in ('datosEdificioOriginal', 'datosNuevoEdificio'):
                model = measure.get(key)
                if model is None:
                    continue
                params = model.state.get('datosGenerales') if isinstance(model, CexObject) else None
                if (not isinstance(params, list) or len(params) < 21
                        or params[4] != general[4]
                        or any(as_num(params[k], key) != as_num(general[k], key) for k in (6, 9))):
                    candidate, reason = None, 'La mejora combinada no conserva la zona, superficie o demanda diaria de ACS'
                    break
        for generator in systems[12]:
            key=solar_key(generator)
            require(all(item['id']!=key for item in issues),'E_SOLAR_SCHEMA',
                    'Un generador se comparte entre contextos; se requiere revision manual')
            name=str(generator.state.get('nombre','Generador solar'))
            desc=f'{context}: {name}. '
            if candidate:
                desc+=(f"Produccion {candidate['production']:.6g} kWh/ano y demanda ACS {candidate['demand']:.6g} kWh/ano. "
                       f"Se propone cobertura ACS "
                       f"{candidate['percent']:.8g} %. Se pierden reparto mensual y potencia solar. "
                       f"Zona {general[4]}, {general[9]} L/dia, temperatura de red "
                       f"{candidate['entrada']['parametros']['temperatura_agua_fria_c']} C. ")
                if candidate['experimental']:
                    desc+='ADAPTACION EXPERIMENTAL: balance anual sin equivalencia energetica completa. '
                if changed:
                    desc+='Se conservan las actuaciones de envolvente, los costes y las referencias de la mejora. '
            else:desc+='Adaptacion no validada: '+reason+'. '
            desc+=('Omitir elimina esta instalacion solar de la salida. ' if context=='edificio' else
                   'Omitir elimina TODO este conjunto de mejora, incluidos sus costes y otras actuaciones. ')
            desc+='Revisar y recalcular en CE3X 2.3. El original se conserva.'
            issues.append({'id':key,'name':name,'context':context,'candidate':candidate,'message':desc,
                           'measure_index':index,'signature':typed_value(generator)})
    return issues


def remove_solar_measures(blocks, indices, audit):
    group_cls = GlobalRef('MedidasDeMejora.objetoGrupoMejoras', 'grupoMedidasMejora')
    names = [m.state.get('nombre') for m in blocks[5] if isinstance(m, CexObject) and m.cls == group_cls]
    require(len(names) == len(blocks[5]) and all(isinstance(n, str) and n for n in names)
            and len(set(names)) == len(names), 'E_MM_NAME', 'Dependencias de conjuntos no identificables')
    removed = {names[i] for i in indices}
    objects = {id(blocks[5][i]) for i in indices}
    require(len(blocks[6]) == 4 and isinstance(blocks[6][2], list)
            and all(isinstance(row, list) and len(row) == 6 and isinstance(row[1], str) and all(scalar(x) for x in row)
                    for row in blocks[6][2]), 'E_ECONOMIC', 'Referencias de costes desconocidas')
    require(len(blocks[11]) in (0, 7, 8) and all(isinstance(x, str) for x in blocks[11][:3]),
            'E_REPORT_FIELDS', 'Referencias de informe desconocidas')
    for i in sorted(indices):
        name = names[i]
        costs = [row for row in blocks[6][2] if row[1] == name]
        report_slots = [j for j, value in enumerate(blocks[11][:3]) if value == name]
        audit.omit(f'medidas_mejora[{i}]', {'conjunto': name, 'costes': costs, 'informe': report_slots},
                   'Conjunto completo, incluidas todas sus actuaciones y costes', risk='modelo', element=name,
                   dependencies=f'{len(costs)} filas de costes y {len(report_slots)} selecciones del informe retiradas')
    blocks[5] = [m for i, m in enumerate(blocks[5]) if i not in indices]
    blocks[6][2] = [row for row in blocks[6][2] if row[1] not in removed]
    blocks[11][:3] = ['' if x in removed else x for x in blocks[11][:3]]

    seen = set()
    def verify(value, path):
        require(id(value) not in objects and not (isinstance(value, str) and value in removed),
                'E_MM_REFERENCE', 'Referencia adicional a un conjunto que se retiraria', path)
        if isinstance(value, (list, tuple, dict, CexObject)):
            if id(value) in seen:
                return
            seen.add(id(value))
        if isinstance(value, CexObject):
            verify(value.state, path)
        elif isinstance(value, dict):
            for key, item in value.items():
                verify(key, path+'.clave')
                verify(item, path+'.'+str(key))
        elif isinstance(value, (list, tuple)):
            for i, item in enumerate(value):
                verify(item, f'{path}[{i}]')
    for i in range(1, 13):
        verify(blocks[i], f'blocks[{i}]')


def resolve_solar(source, choices, audit, manifest, issues, profile):
    choices=choices or {}
    known={item['id']:item for item in issues}
    require(not set(choices)-set(known),'E_SOLAR_DECISION','La seleccion ya no coincide con el archivo')
    for issue in issues:
        choice=choices.get(issue['id'])
        if choice is None:
            manifest['pending_solar']=issue
            raise ConversionError('E_SOLAR_DECISION',issue['message'],issue['id'])
        require(choice in ('adapt','experimental','omit'),'E_SOLAR_DECISION','Decision solar desconocida')
        candidate = issue['candidate']
        require(choice == 'omit' or candidate is not None and
                (choice == 'experimental') == candidate['experimental'],
                'E_SOLAR_SCOPE','Esta adaptacion requiere su modalidad de consentimiento explicita')
    if not issues:return source
    out=copy.deepcopy(source)
    electric = [issue for issue in issues if issue.get('kind') == 'electric_generation']
    if electric:
        rows = out[4][6]
        require(isinstance(rows, list) and all(isinstance(r, list) and r for r in rows),
                'E_CONTRIBUTION', 'Grupo de contribuciones de forma desconocida')
        for issue in electric:
            if choices[issue['id']] != 'experimental':
                continue
            candidate = issue['candidate']
            name = issue['name'] + ' (adaptado 2.3)'
            require(all(r[0] != name for r in rows), 'E_CONTRIBUTION', 'Nombre de contribucion duplicado', issue['path'])
            rows.append([name, LegacyString('Contribuciones energéticas'), ['', '', '', False],
                         [format(candidate['autoconsumo_epb_anual_kwh'], '.15g')] + [''] * 5,
                         [False, True], candidate['zona']])
        out[4][13] = []
    for issue in issues:
        if issue.get('kind')!='window_protection':continue
        experimental = choices[issue['id']] == 'experimental'
        for i in issue['window_indices']:
            state=out[3][1][i].state;path=f'huecos[{i}]'
            audit.omit(path+'.elementosProteccionSolar[25:]',state['elementosProteccionSolar'][25:],
                       'Retirada explicitamente aceptada de los campos nativos de persiana')
            state['elementosProteccionSolar'][25:]=[False,'','']
            if experimental:
                protection = state['elementosProteccionSolar']
                user_factors = [format(as_num(state[key], path+'.'+key), '.15g')
                                for key in ('correctorFSInvierno','correctorFSVerano')]
                audit.change('EXPERIMENTAL_WINDOW_PROTECTION',path+'.elementosProteccionSolar[23:25]',
                             protection[23:25],[True,user_factors],'Formato Otros de CE3X 2.3')
                audit.change('EXPERIMENTAL_WINDOW_PROTECTION',path+'.correctorFSCTE',state['correctorFSCTE'],1.0,
                             'Factor CTE observado en Otros con una proteccion aislada')
                protection[23:25]=[True,user_factors]
                state['correctorFSCTE']=1.0
                continue
            for key,value in [('tieneProteccionSolar',False),('correctorFSCTE',1.0),('correctorFSInvierno',1.0),('correctorFSVerano',1.0)]:
                audit.change('OMIT_WINDOW_PROTECTION',path+'.'+key,state[key],value,
                             'Sin otra proteccion solar ni patron de sombras en el hueco')
                state[key]=value
    manifest['solar_decisions']=[dict(item,choice=choices[item['id']]) for item in issues]
    def row(item):
        return [item['name']+' (adaptado 2.3)',LegacyString('Contribuciones energéticas'),
                [format(item['candidate']['percent'],'.12g'),'0','0',False],['']*6,[True,False],'Edificio Objeto']
    added=set()
    def contributions(rows,generators,measure_index):
        require(isinstance(rows, list) and isinstance(generators, list), 'E_SOLAR_SCHEMA',
                'Grupos de contribuciones o generadores de forma desconocida')
        for g in generators:
            key=solar_key(g)
            require(key in known,'E_SOLAR_SCHEMA','Generador almacenado sin declaracion coincidente')
            item=known[key]
            require(item['measure_index'] == measure_index, 'E_MM_REFERENCE',
                    'Generador termosolar compartido con un contexto distinto', item['context'])
            require(typed_value(g) == item['signature'], 'E_SOLAR_SCHEMA',
                    'Copia de generador termosolar con valores distintos', item['context'])
            if choices[key] in ('adapt','experimental') and (id(rows),key) not in added:
                new=row(item)
                require(all(r[0]!=new[0] for r in rows),'E_SOLAR_SCHEMA','Nombre de contribucion duplicado')
                rows.append(new);added.add((id(rows),key))
    def matrix(systems,measure_index):
        if isinstance(systems,list) and len(systems)==14 and systems[12]:
            contributions(systems[6],systems[12],measure_index);systems[12]=[]
    # Omission of a measure is explicit and includes its dependent report/cost references.
    removed_indices = {issue['measure_index'] for issue in issues
                       if issue.get('measure_index') is not None and choices[issue['id']]=='omit'}
    def visit(value, measure_index, seen):
        if id(value) in seen:return
        if isinstance(value,(CexObject,list,dict,tuple)):seen.add(id(value))
        if isinstance(value,CexObject):
            state=value.state
            if 'datosInstalaciones' in state:matrix(state['datosInstalaciones'],measure_index)
            if value.cls==GlobalRef('MedidasDeMejora.objetoGrupoMejoras','grupoMedidasMejora'):
                require(value is out[5][measure_index], 'E_MM_REFERENCE',
                        'Un conjunto de mejora referencia otro conjunto')
                matrix(state['mejoras'][1][1],measure_index)
                generators=state.get('listadoGeneradoresTermosolarMM',[])
                if generators:contributions(state['sistemasContribucionesMM'],generators,measure_index);state['listadoGeneradoresTermosolarMM']=[]
            if 'listadoGeneradoresTermosolar' in state and state['listadoGeneradoresTermosolar']:
                contributions(state['sistemasContribuciones'],state['listadoGeneradoresTermosolar'],measure_index)
                state['listadoGeneradoresTermosolar']=[]
            for val in state.values():visit(val, measure_index, seen)
        elif isinstance(value,dict):
            for val in value.values():visit(val, measure_index, seen)
        elif isinstance(value,(list,tuple)):
            for val in value:visit(val, measure_index, seen)
    matrix(out[4],None)
    for i, measure in enumerate(out[5]):
        visit(measure, i, set())
    if removed_indices:
        # A whole-group decision still requires a recognized group and graph.
        convert_measures([out[5][i] for i in sorted(removed_indices)], [], profile, Audit())
        remove_solar_measures(out, removed_indices, audit)
    reasons = {'window_protection':'Proteccion solar nueva', 'electric_generation':'Generacion electrica mensual'}
    for issue in issues:
        choice=choices[issue['id']]
        message = (issue.get('experimental_message') or issue['message']) if choice == 'experimental' else issue['message']
        audit.omit(issue.get('path', issue['context']+'.solar'), issue,
                   reasons.get(issue.get('kind'), 'Instalacion termosolar mensual'),
                   risk='modelo', operation={'adapt':'adaptar','experimental':'adaptar experimentalmente','omit':'omitir'}[choice],
                   element=issue['name'], count=len(issue.get('window_indices',[None])),
                   dependencies=message)
        audit.event('WARNING','W_SOLAR_'+choice.upper(),message,choice=choice)
    manifest['results_require_recalculation']=True
    return out


def audit_general_fields(values, audit, path, element):
    extra = values[21:]
    require(all(scalar(x) for x in extra), 'E_NEW_GENERAL',
            'Campos nuevos con estructura no reconocida', path+'[21:]')
    if len(values) > 22 and not empty(values[22]):
        as_num(values[22], path+'[22]', minimum=0)
    for i, value in enumerate(extra, 21):
        audit.loss(f'{path}[{i}]', value, 'Campo general exclusivo de CE3X 3.2',
                   element=element, dependencies='Se conservan los datos generales comunes y su superficie')


def transfer(source, template, profile, audit, fix_accents=True):
    audit.stage='adaptar estructuras'
    require(len(source[1])==29 and len(source[2])==26, 'E_SOURCE_SCHEMA',
            'El perfil 3.2 espera 29 campos administrativos y 26 generales')
    audit_general_fields(source[2], audit, 'generales', 'Edificio')
    for i, value in enumerate(source[1][26:], 26):
        require(scalar(value) or i == 27 and isinstance(value, list) and all(scalar(x) for x in value),
                'E_ADMIN_FIELD', 'Campo administrativo adicional con estructura desconocida', f'administrativos[{i}]')
        audit.loss(f'administrativos[{i}]', value, 'Campo administrativo exclusivo de CE3X 3.2',
                   risk='usuario', element='Datos administrativos',
                   dependencies='Se conservan los campos administrativos comunes')
    out=copy.deepcopy(source)
    out[0]=copy.deepcopy(template[0])
    audit.change('HEADER','version',source[0],out[0],'Cabecera nativa 2.3 de la plantilla')
    for index,count in ((1,26),(2,21)):
        out[index]=copy.deepcopy(source[index][:count])
        audit.change('FIELDS_23',f'blocks[{index}].length',len(source[index]),count,'Longitud nativa 2.3; valores comunes del origen conservados')
    schema = mm_schema()
    for i,w in enumerate(out[3][1]):
        require(isinstance(w,CexObject),'E_WINDOW_CLASS','Registro de hueco invalido',f'huecos[{i}]')
        cls = w.cls.module+'.'+w.cls.name
        unknown = set(w.state) - set(schema[cls]) - set(profile['window_removed_attributes'])
        require(not unknown, 'E_WINDOW_FIELD', f'{w.state["descripcion"]}: campos de hueco desconocidos {sorted(unknown, key=str)}',
                f'huecos[{i}]')
        for key in profile['window_removed_attributes']:
            if key in w.state:
                audit_measure_extra(audit, cls, key, w.state.pop(key),f'huecos[{i}].{key}',w.state['descripcion'])
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
    require(len(out[11]) in (0,7,8),'E_REPORT_FIELDS','Configuracion de informe desconocida')
    if len(out[11])==8:
        require(empty(out[11][7]),'E_REPORT_FIELDS','Campo adicional de informe activo sin equivalencia 2.3','informe[7]')
        audit.omit('informe[7]',out[11][7],'Campo adicional vacio de 3.2')
        out[11]=out[11][:7]
        audit.change('REPORT_FIELDS','informe.length',8,7,'Retirado campo adicional vacio de informe 3.2')
    # El bloque comun de complementos se transfiere opaco. Una lista o un
    # diccionario no justifica borrar configuraciones ni resultados del origen.
    for name, payload in source[12].items():
        require(isinstance(name, str) and name,
                'E_ADDON_SCHEMA', 'Nombre de complemento no reconocido', 'complementos')
        audit.event('INFO', 'ADDON_PRESERVED',
                    'Datos del complemento conservados sin reinterpretar.',
                    path='complementos.'+name, payload_type=type(payload).__name__)
    # Dos bloques reservados observados en ficheros nativos. No se interpretan.
    for i in (13,14):
        old, new = source[i], template[i]
        if typed_value(old) == typed_value(new):
            continue
        token = lambda value: (isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9+/]{43}=', value)
                               and len(base64.b64decode(value, validate=True)) == 32)
        require(i == 14 and token(old) and token(new), 'E_RESERVED_BLOCK',
                'Bloque reservado con forma desconocida', f'blocks[{i}]')
        audit.omit(f'blocks[{i}]', old, 'Token interno de 32 bytes sustituido por el de la plantilla',
                   operation='sustituir')
        out[i] = copy.deepcopy(new)
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
    for index in (7,8,9,10,12):
        require(typed_value(src[index])==typed_value(dst[index]),'E_PRESERVATION','Bibliotecas, sombras, subgrupos o complementos alterados',f'blocks[{index}]')
    require(len(src[3][1])==len(dst[3][1]),'E_PRESERVATION','Numero de huecos alterado')
    for i in (0,2,3):
        require(json_value(src[3][i])==json_value(dst[3][i]),'E_PRESERVATION','Cerramientos, puentes o subgrupos alterados')
    for g in range(min(6,len(src[4]))):
        require(len(src[4][g])==len(dst[4][g]),'E_PRESERVATION','Numero de equipos alterado')
        for a,b in zip(src[4][g],dst[4][g]):
            for index in (1,2,3,4,5,6,7,8):
                require(json_value(a[index])==json_value(b[index]),'E_PRESERVATION','Datos termicos de instalaciones alterados',f'instalaciones[{g}][{index}]')


def validate_target_classes(blocks):
    # No dejar clases exclusivas de 3.2 en bloques que 2.3 tiene que importar.
    allowed={
        ('Envolvente.objetosEnvolvente','HuecoConocidas'),
        ('Envolvente.objetosEnvolvente','HuecoEstimadas'),
        ('LibreriasCE3X.menuCerramientos','composicionCerramiento'),
        ('ventanaSubgrupo','claseZona'),
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


def prepare_destination(source, native, profile, audit, manifest, issues, choices, fix_accents):
    audit.stage = 'planificar conversion'
    resolved = resolve_solar(source, choices, audit, manifest, issues, profile)
    target = transfer(resolved, native, profile, audit, fix_accents)
    validate(target, audit, profile, target=True)
    check_preservation(resolved, target, fix_accents)
    compare_windows(resolved, target, profile)
    validate_target_classes(target)
    return target


def consent_token(manifest, choices, losses):
    scope = [manifest[key] for key in ('source_sha256', 'template_sha256', 'profile_sha256',
                                       'improvements_schema_sha256')]
    return hashlib.sha256(json_text([VERSION, scope, sorted(choices.items()), losses]).encode('utf-8')).hexdigest()


def describe_losses(losses):
    return '\n'.join(
        f"- {item['risk'].capitalize()} | {item['element']} | {item['count']} | "
        f"{item['operation'].capitalize()} {item['reason']} ({item['path']}). {item['dependencies']}."
        for item in losses)


def convert(source, template, profile_path=None, fix_accents=True, overwrite=False, solar_choices=None,
            expected_source_sha=None, consent=None):
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
        if expected_source_sha is not None:
            require(sha(source)==expected_source_sha,'E_INPUT_CHANGED','El archivo ha cambiado despues de solicitar la decision')
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
        if expected_source_sha is not None:
            require(manifest['source_sha256']==expected_source_sha,'E_INPUT_CHANGED','El origen ha cambiado durante la comprobacion')
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
        require(sha(source)==manifest['source_sha256'],'E_INPUT_CHANGED','El origen ha cambiado durante la lectura')
        issues = solar_issues(src)
        requested = solar_choices or {}
        require(not set(requested) - {issue['id'] for issue in issues}, 'E_SOLAR_DECISION',
                'La seleccion ya no coincide con el archivo')
        undecided = [issue for issue in issues if issue['id'] not in requested]
        choices = {issue['id']: requested.get(issue['id'], 'omit') for issue in issues}
        dst = prepare_destination(src, native, profile, audit, manifest, issues, choices, fix_accents)
        token = consent_token(manifest, choices, audit.losses)
        require(consent is None or not undecided and consent == token and audit.losses,
                'E_CONSENT_CHANGED', 'El plan autorizado no coincide. Vuelve a analizar el archivo.')
        if audit.losses and consent is None:
            first_option = 'apply' if any(value != 'omit' for value in choices.values()) else 'omit'
            options = {first_option: {'token': token, 'choices': choices, 'losses': audit.losses}}
            adapt_choices = {**choices, **{issue['id']: 'experimental' if issue['candidate']['experimental'] else 'adapt'
                                          for issue in undecided if issue['candidate']}}
            adaptation = 'experimental' if 'experimental' in adapt_choices.values() else 'adapt'
            if adapt_choices != choices:
                adapt_audit = Audit()
                try:
                    prepare_destination(src, native, profile, adapt_audit, {}, issues, adapt_choices, fix_accents)
                except ConversionError as exc:
                    audit.event('WARNING', 'W_ADAPT_BLOCKED', str(exc), path=exc.path)
                else:
                    options[adaptation] = {'token': consent_token(manifest, adapt_choices, adapt_audit.losses),
                                           'choices': adapt_choices, 'losses': adapt_audit.losses}
            title = 'Omitir lo indicado y convertir' if first_option == 'omit' else 'Aplicar las decisiones indicadas'
            message = title + '\n' + describe_losses(audit.losses)
            if adaptation in options:
                title = 'Adaptacion experimental' if adaptation == 'experimental' else 'Adaptar y convertir'
                message += '\n\n'+title+' (incluye estas perdidas)\n' + describe_losses(options[adaptation]['losses'])
            message += '\n\nEl certificado puede cambiar. Revisa y recalcula en CE3X 2.3. Cancelar conserva todos los archivos.'
            issue_id = issues[0]['id'] if len(issues) == 1 else 'plan:'+token[:16]
            manifest['pending_plan'] = {'id': issue_id, 'options': options}
            if undecided:
                manifest['pending_solar'] = undecided[0]
            manifest.pop('solar_decisions', None)
            raise ConversionError('E_SOLAR_DECISION' if undecided else 'E_CONSENT_REQUIRED', message, issue_id)
        if audit.losses:
            manifest['consent'] = {'token': token, 'solar_choices': choices}
            manifest['results_require_recalculation'] = True
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
        status, exit_code = ('CONVERSION_CON_OMISIONES' if audit.losses else 'REVISAR'), 0
        if manifest.get('solar_decisions'):
            labels = {'adapt':'Adaptado: ', 'experimental':'Adaptado experimentalmente: ', 'omit':'Omitido: '}
            actions=[labels[x['choice']]+(x['context']+' / ' if x['choice']=='omit' else '')+x['name']
                     for x in manifest['solar_decisions']]
            manifest['decision_summary']='; '.join(actions)
        attempt.summary = (f'Archivo generado. {len(dst[3][0])} cerramientos, {len(dst[3][1])} huecos, '
                           f'{len(dst[3][2])} puentes y {len(dst[5])} conjuntos de mejora. '
                           'Revisar y recalcular en CE3X 2.3.')
        preserved_warnings = sorted({event['path'] for event in audit.events
                                     if event['code'] == 'W_NATIVE_VALUE'})
        if preserved_warnings:
            manifest['preserved_value_warnings'] = preserved_warnings
            attempt.summary += (' Hay datos originales incompletos o incoherentes conservados sin cambios: '
                                + ', '.join(preserved_warnings[:3])
                                + ('; listado completo en el diagnostico' if len(preserved_warnings) > 3 else '') + '.')
        if audit.losses:
            decisions = manifest.get('decision_summary', '')
            manifest['decision_summary'] = ('CONVERSION_CON_OMISIONES\n' + decisions + '\n'
                                            + describe_losses(audit.losses)
                                            + '\nRevisar y recalcular en CE3X 2.3.')
    except Exception as exc:
        code, path = (exc.code, exc.path) if isinstance(exc, ConversionError) else ('E_UNEXPECTED', '')
        audit.event('ERROR', code, str(exc), path=path, exception_type=type(exc).__name__)
        attempt.traceback_text = traceback.format_exc()
        if 'pending_plan' in manifest:
            status, exit_code='DECISION',2
        manifest.update(structural_validation=False, error_code=code, error_path=path,
                        error_message=str(exc), error_stage=audit.stage)
        attempt.summary = (code + ': ' + str(exc)) if status=='DECISION' or not path else f'{code} [{path}]: {exc}'
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        manifest.update(status=status, finished=dt.datetime.now().astimezone().isoformat(),
                        plan_de_conversion={'transformaciones': audit.changes, 'no_transferido': audit.omitted})
    return exit_code, attempt


def serve(stream_in=None, stream_out=None):
    """Keep the last attempt in memory until the GUI requests an export or closes."""
    stream_in, stream_out = stream_in or sys.stdin, stream_out or sys.stdout
    last_attempt = None
    pending = None
    def reply(status, path, message):
        clean = lambda value: str(value).translate({0: ' ', 9: ' ', 13: '', 30: ' ', 31: ' '})
        line = '\t'.join((status, clean(path).replace('\n', ' '), clean(message).replace('\n', '\x1e\x1f'))) + '\n'
        fits = len(line.encode('utf-8')) < 131072
        if not fits:
            status = ('ERROR' if status.startswith('DECISION_') else status)
            prefix = 'CONVERSION_CON_OMISIONES. ' if status == 'REVISAR_CAMBIOS' else ''
            line = f'{status}\t{clean(path) if status != "ERROR" else ""}\t{prefix}El inventario completo excede la vista. Guarda el diagnostico para consultarlo.\n'
        stream_out.write(line)
        stream_out.flush()
        return fits
    for line in stream_in:
        try:
            request = json.loads(line)
            command = request['command']
            if command == 'exit':
                return
            if command in ('convert','decision'):
                if command=='convert':
                    last_attempt=None
                    pending=dict(request)
                    pending['source_sha']=sha(Path(request['source']))
                    selected = {'choices': {}, 'token': None}
                else:
                    require(pending is not None and last_attempt is not None,'E_RUN','No hay una decision pendiente')
                    plan=last_attempt.manifest.get('pending_plan')
                    require(plan is not None and request.get('id')==plan['id'],'E_SOLAR_DECISION','Decision caducada')
                    if request.get('choice')=='cancel':
                        pending=None
                        last_attempt.manifest['status'] = 'CANCELADO'
                        reply('CANCELADO','','Conversion cancelada. No se ha generado ningun archivo.')
                        continue
                    selected=plan['options'].get(request.get('choice'))
                    require(selected is not None,'E_SOLAR_DECISION','Seleccion no disponible')
                code,last_attempt=convert(pending['source'],pending.get('template',ROOT/'plantilla_23.cex'),
                                          overwrite=pending.get('overwrite',False),
                                          solar_choices=selected['choices'],expected_source_sha=pending['source_sha'],
                                          consent=selected['token'])
                if code==2:
                    plan=last_attempt.manifest['pending_plan']
                    decision = next((key for key in ('experimental','adapt','omit') if key in plan['options']), 'omit')
                    if not reply('DECISION_'+decision.upper(),
                                 plan['id'],last_attempt.manifest['error_message']):
                        pending=None
                else:
                    status=last_attempt.manifest['status']
                    message=last_attempt.summary
                    if status == 'CONVERSION_CON_OMISIONES':
                        status='REVISAR_CAMBIOS'
                        message=last_attempt.manifest['decision_summary']
                    reply(status,last_attempt.output if not code else '',message)
                    pending=None
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
    p.add_argument('--solar-choice', action='append', default=[], metavar='ID=adapt|experimental|omit', help='Decision explicita para cada generador indicado por el analisis previo')
    p.add_argument('--consent', metavar='TOKEN', help='Autorizar el plan exacto mostrado en el analisis previo')
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
        choices=dict(item.split('=',1) for item in a.solar_choice)
        code, attempt = convert(a.source, a.template, a.profile, a.fix_accents, a.overwrite,
                                solar_choices=choices, consent=a.consent)
        print(attempt.summary)
        if code==2:
            for option, plan in attempt.manifest['pending_plan']['options'].items():
                flags = ' '.join(f'--solar-choice {key}={value}' for key, value in plan['choices'].items())
                print(f'{option}: {flags} --consent {plan["token"]}')
        if not code:
            print(attempt.output)
            if attempt.manifest.get('decision_summary'):print(attempt.manifest['decision_summary'])
        if a.diagnostic:
            print(attempt.export_diagnostic(a.diagnostic))
        return code
    except Exception as exc:
        print('Error: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
