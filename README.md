# Conversor CE3X 3.2 a CE3X 2.3

Código fuente del conversor experimental de archivos `.cex` residenciales de CE3X 3.2 al formato observado de CE3X 2.3. Versión actual: **1.3.0**.

## Descargar y usar en Windows

[**Descargar Conversor_CE3X_Windows_1_3.zip**](https://github.com/xSeeSx/Conversor-CE3X-3.2-a-CE3X-2.3/releases/latest/download/Conversor_CE3X_Windows_1_3.zip)

El paquete portátil para Windows 10/11 de 64 bits incluye Python y el ejecutable, sin instalación adicional. Encontrarás las versiones publicadas en [Releases](https://github.com/xSeeSx/Conversor-CE3X-3.2-a-CE3X-2.3/releases).

1. Descarga `Conversor_CE3X_Windows_1_3.zip` desde los archivos de la release.
2. Extrae **todo el ZIP** en una carpeta nueva.
3. Abre `Conversor_CE3X.exe`.
4. Selecciona el `.cex` de CE3X 3.2 y una carpeta de resultados.
5. Pulsa **Convertir y generar diagnóstico**.
6. Abre el resultado en CE3X 2.3 y recalcula antes de emitir informes.

Los archivos automáticos **Source code (zip)** y **Source code (tar.gz)** de GitHub contienen los fuentes. Para usar el programa directamente en Windows, descarga el ZIP indicado arriba.

## Ejecutar desde el código fuente

Necesitas Python 3.11 o posterior. El motor utiliza únicamente la biblioteca estándar y no requiere instalar paquetes adicionales.

Clona este repositorio o descarga su código y ejecuta estos comandos desde la carpeta principal:

```sh
python app/converter.py self-test
python -m unittest discover -s fuentes -p test_converter.py -v
python app/converter.py convert --source origen.cex --template app/plantilla_23.cex --outdir resultados
```

Cada conversión crea una carpeta `intento_...` con el archivo `convertido_CE3X_2_3.cex`, los registros de cambios y un ZIP de diagnóstico junto a esa carpeta. Los originales no se sobrescriben.

Abre la salida en CE3X 2.3, revisa los elementos e instalaciones y recalcula la calificación, los conjuntos de mejora y su análisis económico. Guarda una nueva copia y regenera los informes y complementos.

## Compilar y ejecutar la interfaz en Windows

La interfaz está escrita en C y utiliza la API nativa de Windows. Para compilarla, instala Zig 0.13.0, añade `zig.exe` al `PATH` y ejecuta desde la carpeta principal:

```powershell
powershell -ExecutionPolicy Bypass -File fuentes/compilar_windows.ps1
```

El script genera `Conversor_CE3X.exe` en la raíz del proyecto. La interfaz busca el motor en `app/` y Python en `runtime/python.exe`, junto al ejecutable.

Para preparar Python para la interfaz, descarga la [distribución embebida oficial Python 3.11.9 para Windows x64](https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip) y extrae todo su contenido en `runtime/`. Conserva su `LICENSE.txt` y los avisos de licencia.

Ejecuta `Conversor_CE3X.exe`, selecciona el `.cex` de origen y una carpeta de resultados. La referencia estructural 2.3 está incluida en `app/plantilla_23.cex`.

## Funciones

- Adaptación de datos generales, cerramientos, ventanas e instalaciones residenciales contrastadas.
- Conservación y adaptación de conjuntos de mejora de fotovoltaica, aislamiento y sustitución de ventanas, con sus equipos y datos económicos asociados.
- Conservación de nombres, descripciones, costes, mantenimiento, vida útil, facturas, tarifas y selección de conjuntos en el informe.
- Reparación automática de escapes literales de acentos, eñes y diéresis españoles, incluidas mayúsculas y medidas de mejora. Conserva el texto correcto y diferencia STRING y UNICODE.
- Registro de cambios, errores con ubicación del dato y ZIP de diagnóstico por intento.
- Motor editable para aplicar parches sin recompilar la interfaz.

## Alcance y validación

**El estado REVISAR indica comprobaciones estructurales superadas, no validación por CE3X.** La versión 1.3 incluye 49 pruebas del motor y se ha contrastado estructuralmente con archivos reales. La apertura, edición y el recálculo en CE3X 2.3 siguen pendientes de validación en la aplicación.

Los resultados y amortizaciones guardados se conservan como datos del origen 3.2. **No se han recalculado con el motor 2.3.** Recalcula antes de emitir informes. La configuración de complementos se reinicia y debe regenerarse.

El perfil admite archivos residenciales textuales de 15 bloques, protocolo pickle 0, de hasta 64 MiB. No garantiza compatibilidad universal. Los tipos, clases o funciones nuevas sin regla contrastada producen un error con diagnóstico, evitando eliminar silenciosamente conjuntos.

No es una herramienta oficial de CE3X y no genera por sí sola certificados, XML de registro ni justificaciones HE0/HE1. No incluye el programa CE3X ni datos de proyectos particulares.

## Informar de un error

Cada intento genera una carpeta y `intento_..._diagnostico.zip`. Los errores del conversor se registran automáticamente.

Si el fallo ocurre en CE3X, escribe la acción, elemento y mensaje exacto en el conversor; pulsa **Guardar error / adjunto** y selecciona su log o una captura. **Intento previo** permite completar un diagnóstico después de cerrar el programa.

También puedes añadir evidencia desde el motor:

```sh
python app/converter.py evidence --run resultados/intento_... --log CE3X.exe.log --notes-file notas.txt
```

**Revisa el ZIP antes de publicarlo en una incidencia:** puede contener datos personales, información técnica del proyecto y los adjuntos que hayas incluido. Publica solo la información que quieras compartir.

## Estructura del código

| Archivo | Función |
| --- | --- |
| `app/converter.py` | Motor de conversión y comandos de diagnóstico |
| `app/profile.json` | Reglas estructurales del perfil residencial |
| `app/mm_schema_23.json` | Campos contrastados de medidas de mejora |
| `app/plantilla_23.cex` | Referencia estructural neutral para el formato 2.3 |
| `fuentes/launcher.c` | Interfaz nativa Windows x64 |
| `fuentes/compilar_windows.ps1` | Compilación de la interfaz con Zig |
| `fuentes/test_converter.py` | Pruebas de regresión autónomas |
| `fuentes/DESARROLLO.txt` | Notas de implementación y depuración |
| `fuentes/VALIDACION.txt` | Evidencia y límites de la validación de la versión 1.3 |

El esquema contiene nombres de campos contrastados, sin valores de otro edificio. Cada diagnóstico identifica las versiones y hashes del motor, perfil y esquema. La plantilla es una referencia estructural neutral, no representa una vivienda y no sirve para certificarla.

El repositorio contiene los fuentes y recursos necesarios para trabajar con el código. El runtime de Python y los ejecutables se preparan localmente siguiendo las instrucciones anteriores.
