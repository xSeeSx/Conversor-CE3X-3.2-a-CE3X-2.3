# Desarrollo

Esta guía corresponde a la versión 1.4.0. La interfaz nativa utiliza el estilo técnico compacto, con controles escalados según los DPI de Windows.

## Ejecutar el motor

Python 3.11 o posterior, sin paquetes externos. Desde la raíz del repositorio:

```sh
python app/converter.py self-test
python -m unittest discover -s fuentes -p test_converter.py -v
python app/converter.py convert --source origen.cex
```

La conversión guarda `origen_CE3X2.3.cex` junto al original. No crea logs ni carpetas de diagnóstico automáticamente. Si la salida existe, el motor devuelve `E_OUTPUT_EXISTS`; `--overwrite` autoriza expresamente su sustitución.

En la línea de comandos, la exportación de diagnóstico se pide de forma explícita:

```sh
python app/converter.py convert --source origen.cex --diagnostic diagnostico.zip
```

`--template` y `--profile` permiten indicar referencias de desarrollo; por defecto se utilizan los recursos de `app/`.

## Compilar la interfaz en Windows

Instala Zig 0.13.0, añade `zig.exe` al `PATH` y ejecuta:

```powershell
powershell -ExecutionPolicy Bypass -File fuentes/compilar_windows.ps1
```

El script genera `Conversor_CE3X.exe`. Para ejecutarlo, descarga la [distribución embebida oficial de Python 3.11.9 para Windows x64](https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip) y extrae todo su contenido en `runtime/`. Conserva `runtime/LICENSE.txt` y los avisos del proveedor.

La interfaz necesita `app/` y `runtime/` junto al ejecutable. Comprueba la conexión con el motor:

```powershell
./Conversor_CE3X.exe --self-test resultado_motor.txt
```

## Diagnóstico a petición

La interfaz mantiene una sesión Python mediante tuberías anónimas. Los comandos se envían como una línea JSON UTF-8 y las respuestas contienen estado, ruta y mensaje separados por tabuladores.

El último intento, los eventos, los cambios, la excepción y las instantáneas técnicas se conservan en memoria. No se utilizan logs temporales ni archivos puente. **Guardar diagnóstico** exporta un único ZIP en la ruta elegida. La información del intento se pierde al cerrar el programa o comenzar otra conversión.

La conversión escribe un archivo temporal únicamente para releer y verificar la salida. Lo retira si falla y publica el `.cex` una vez validado, sin sobrescribir una salida existente salvo autorización expresa.

## Pruebas y publicación

GitHub Actions ejecuta las pruebas con Python 3.11, compila en Windows, repite las pruebas con Python embebido y verifica la comunicación entre el ejecutable y el motor. El paquete portátil y una captura de la interfaz quedan como artefactos de la comprobación; no se publican automáticamente en Releases.

Después de compilar y preparar `runtime/`, `python scripts/empaquetar.py` crea el ZIP público y su SHA256 en `_release/`. La selección de archivos excluye proyectos particulares. `Conversor_CE3X.exe --preview vista.bmp` permite revisar el aspecto de la interfaz nativa.

La apertura y el recálculo en CE3X 2.3 requieren validación manual. Una compilación y sus pruebas correctas no acreditan la validez energética de la conversión.

Antes de publicar una versión, actualiza su número y `CHANGELOG.md`, valida el paquete y crea una release con su ZIP para Windows y las notas correspondientes. Conserva las versiones anteriores.

## Arquitectura y reglas de conversión

El motor crea datos inertes al leer el pickle textual: no importa módulos de CE3X ni ejecuta funciones del archivo. Adapta estructuras contrastadas, conserva tipos y referencias y relee la salida antes de publicarla.

El perfil y el esquema de mejoras contienen reglas estructurales, sin valores físicos de proyectos particulares. Los tipos no contrastados se rechazan con un error. Para añadir una regla, compara muestras nativas 3.2 y 2.3 del mismo elemento e incorpora una prueba de regresión.

Las instantáneas de diagnóstico excluyen los bloques administrativos y las imágenes, pero el ZIP puede contener datos técnicos y los adjuntos que el usuario elija. Debe revisarse antes de compartirlo.
