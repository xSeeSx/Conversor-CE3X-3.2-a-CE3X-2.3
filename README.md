# Conversor CE3X 3.2 a CE3X 2.3

Conversor experimental de archivos `.cex` residenciales de CE3X 3.2 al formato observado de CE3X 2.3. Version actual: **1.3.0**.

## Descargar para Windows

[**Descargar Conversor_CE3X_Windows_1_3.zip**](https://github.com/xSeeSx/Conversor-CE3X-3.2-a-CE3X-2.3/raw/refs/heads/main/dist/Conversor_CE3X_Windows_1_3.zip)

Windows 10/11 de 64 bits. El ZIP incluye el ejecutable y Python, sin instalacion adicional.

1. Descarga y extrae **todo el ZIP** en una carpeta nueva.
2. Abre `Conversor_CE3X.exe`.
3. Selecciona el archivo `.cex` de CE3X 3.2. La referencia estructural 2.3 viene incluida.
4. Elige una carpeta de resultados y pulsa **Convertir y generar diagnostico**.
5. Abre `convertido_CE3X_2_3.cex` en CE3X 2.3 y revisa sus elementos e instalaciones.
6. Recalcula la calificacion, los conjuntos de mejora y su analisis economico. Guarda una nueva copia y regenera los informes y complementos.

## Funciones

- Adaptacion de datos generales, cerramientos, ventanas e instalaciones residenciales contrastadas.
- Conservacion y adaptacion de conjuntos de mejora de fotovoltaica, aislamiento y sustitucion de ventanas, con sus equipos y datos economicos asociados.
- Conservacion de nombres, descripciones, costes, mantenimiento, vida util, facturas, tarifas y seleccion de conjuntos en el informe.
- Reparacion automatica de escapes literales de acentos, enes y dieresis espanoles, incluidas mayusculas y medidas de mejora. Conserva el texto correcto y diferencia STRING y UNICODE.
- Log de cambios, errores con ubicacion del dato y ZIP de diagnostico por intento.
- Motor editable para aplicar parches sin recompilar la interfaz.
- Trabajo local y originales sin sobrescribir.

## Alcance y validacion

**El estado REVISAR indica comprobaciones estructurales superadas, no validacion por CE3X.** Se han superado 49 pruebas del motor en Linux y conversiones estructurales de archivos reales. La apertura, edicion y el recalculo en CE3X 2.3 siguen pendientes de validacion en la aplicacion.

Los resultados y amortizaciones guardados se conservan como datos del origen 3.2. **No se han recalculado con el motor 2.3.** Recalcula antes de emitir informes. La configuracion de complementos se reinicia y debe regenerarse.

El perfil admite archivos residenciales textuales de 15 bloques, protocolo pickle 0, de hasta 64 MiB. No garantiza compatibilidad universal. Los tipos, clases o funciones nuevas sin regla contrastada producen un error con diagnostico, evitando eliminar silenciosamente conjuntos.

No es una herramienta oficial de CE3X y no genera por si sola certificados, XML de registro ni justificaciones HE0/HE1. No incluye el programa CE3X ni datos de proyectos particulares.

## Informar de un error

Cada intento genera una carpeta y `intento_..._diagnostico.zip`. Los errores del conversor se registran automaticamente.

Si el fallo ocurre en CE3X, escribe la accion, elemento y mensaje exacto en el conversor; pulsa **Guardar error / adjunto** y selecciona su log o una captura. **Intento previo** permite completar un diagnostico despues de cerrar el programa.

**Revisa el ZIP antes de publicarlo en una incidencia:** puede contener datos personales, informacion tecnica del proyecto y los adjuntos que hayas incluido. Publica solo la informacion que quieras compartir.

## Ejecutar el motor desde el codigo fuente

El motor usa Python 3.11 o posterior y la biblioteca estandar, sin paquetes externos.

```sh
python app/converter.py self-test
python -m unittest discover -s fuentes -p test_converter.py -v
python app/converter.py convert --source origen.cex --template app/plantilla_23.cex --outdir resultados
```

Para ejecutar la interfaz desde el codigo descargado, extrae el runtime del ZIP portatil en `runtime/` o utiliza las instrucciones de compilacion de `fuentes/`.

## Compilar la interfaz en Windows

Instala Zig 0.13.0 y ejecuta:

```powershell
powershell -ExecutionPolicy Bypass -File fuentes/compilar_windows.ps1
```

`app/converter.py`, `app/profile.json` y `app/mm_schema_23.json` son editables. El esquema contiene nombres de campos contrastados, sin valores de otro edificio. Cada diagnostico identifica sus versiones y hashes.

## Componentes

- Interfaz nativa Windows x64, fuentes en `fuentes/launcher.c`.
- Motor Python sin dependencias externas.
- Runtime oficial Python 3.11.9 Windows x64 incluido solo en el ZIP portatil. Su licencia y avisos estan en `runtime/LICENSE.txt` dentro del paquete.
- [Distribucion oficial del runtime de Python](https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip).

La plantilla incluida es una referencia estructural neutral. No representa una vivienda y no sirve para certificarla.
