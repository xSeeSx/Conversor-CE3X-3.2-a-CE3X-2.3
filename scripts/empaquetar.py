"""Create the public portable package from a validated Windows build."""
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile


def package(root, output_directory):
    root, output_directory = Path(root).resolve(), Path(output_directory).resolve()
    source = (root / 'app/converter.py').read_text(encoding='utf-8')
    version = re.search(r"^VERSION = '([0-9]+\.[0-9]+\.[0-9]+)'", source, re.MULTILINE).group(1)
    suffix = version.replace('.', '_')
    contents = {}
    for name in ['Conversor_CE3X.exe', 'app/converter.py', 'app/profile.json',
                 'app/mm_schema_23.json', 'app/plantilla_23.cex', 'CHANGELOG.md']:
        contents[name] = (root / name).read_bytes()
    runtime = root / 'runtime'
    for name in ['python.exe', 'python311.dll', 'python311.zip', 'python311._pth', 'LICENSE.txt']:
        if not (runtime / name).is_file():
            raise FileNotFoundError('Falta un componente del runtime: ' + name)
    for path in sorted(runtime.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            contents[path.relative_to(root).as_posix()] = path.read_bytes()
    contents['LEEME.txt'] = (
        'CONVERSOR CE3X ' + version + ' PARA WINDOWS\n\n'
        'Windows 10/11 de 64 bits. Python incluido, sin instalacion adicional.\n\n'
        '1. Extrae todo el ZIP y abre Conversor_CE3X.exe.\n'
        '2. Selecciona o arrastra el archivo .cex de CE3X 3.2.\n'
        '3. Pulsa Convertir. Se guarda nombre_CE3X2.3.cex junto al original.\n'
        '4. Revisa y recalcula el resultado y las mejoras en CE3X 2.3.\n\n'
        'Si hay solar mensual, decide Adaptar, Omitir lo indicado o Cancelar.\n'
        'Adaptar solo se ofrece para la configuracion ensayada. En una mejora,\n'
        'Omitir retira el conjunto completo, segun advierte el dialogo.\n\n'
        'No se sobrescribe el original. Si la salida ya existe, se pide confirmacion.\n'
        'No se generan logs automaticamente. Si aparece un error, pulsa Guardar\n'
        'diagnostico para guardar un ZIP. Notas y adjunto permite anadir detalles.\n'
        'Guarda el diagnostico antes de cerrar o hacer otra conversion. Revisa\n'
        'su contenido antes de compartirlo, puede contener datos del proyecto.\n\n'
        'Conserva app/ y runtime/ junto al ejecutable. El EXE suelto no funciona.\n'
        'Los resultados energeticos proceden de 3.2 y requieren recalculo en 2.3.\n'
        'Herramienta experimental y no oficial. REVISAR indica comprobaciones\n'
        'estructurales, no validacion por CE3X. No genera certificados ni XML.\n\n'
        'Codigo, incidencias y versiones:\n'
        'https://github.com/xSeeSx/Conversor-CE3X-3.2-a-CE3X-2.3\n'
        'Licencia del runtime de Python: runtime/LICENSE.txt\n'
    ).encode('utf-8')
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(contents.items())}
    contents['SHA256.json'] = (json.dumps(hashes, indent=2) + '\n').encode('utf-8')
    output_directory.mkdir(parents=True, exist_ok=True)
    archive = output_directory / ('Conversor_CE3X_Windows_' + suffix + '.zip')
    prefix = 'Conversor_CE3X_' + suffix + '/'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for name, data in sorted(contents.items()):
            output.writestr(prefix + name, data)
    with zipfile.ZipFile(archive) as output:
        if output.testzip() is not None:
            raise RuntimeError('El ZIP no supera la comprobacion de integridad')
        for name, expected in hashes.items():
            if hashlib.sha256(output.read(prefix + name)).hexdigest() != expected:
                raise RuntimeError('SHA256 incorrecto: ' + name)
        cex_files = [name for name in output.namelist() if name.lower().endswith('.cex')]
        if cex_files != [prefix + 'app/plantilla_23.cex']:
            raise RuntimeError('El paquete contiene proyectos que no deben publicarse')
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output_directory / 'SHA256SUMS.txt').write_text(digest + '  ' + archive.name + '\n', encoding='ascii')
    print(archive)
    print('SHA256: ' + digest)
    return archive


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    package(root, Path(sys.argv[1]) if len(sys.argv) > 1 else root / '_release')
