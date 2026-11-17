# Conversor CE3X 3.2 a CE3X 2.3

Conversor experimental de archivos `.cex` residenciales de CE3X 3.2 a CE3X 2.3 para Windows 10/11 de 64 bits.

## Descargar

[**Descargar para Windows, versión 1.4.0**](https://github.com/xSeeSx/Conversor-CE3X-3.2-a-CE3X-2.3/releases/download/v1.4.0/Conversor_CE3X_Windows_1_4_0.zip)

[Releases y notas de cada versión](https://github.com/xSeeSx/Conversor-CE3X-3.2-a-CE3X-2.3/releases) · [Historial de cambios](CHANGELOG.md)

El ZIP incluye el ejecutable y Python. No necesitas instalar Python ni otros paquetes. En Releases, descarga `Conversor_CE3X_Windows_1_4_0.zip`; los archivos llamados **Source code** contienen los fuentes.

## Cómo usar la versión publicada

1. Extrae **todo el ZIP** en una carpeta nueva.
2. Abre `Conversor_CE3X.exe`.
3. Selecciona o arrastra el `.cex` de CE3X 3.2 y pulsa **Convertir**. Se guarda `nombre_CE3X2.3.cex` en la misma carpeta del original.
4. Abre el resultado en CE3X 2.3, revisa sus datos y recalcula antes de emitir informes.

Conserva las carpetas del paquete junto al ejecutable. El `.exe` suelto no funciona.

## Qué convierte

- Datos generales, cerramientos, ventanas e instalaciones residenciales de los tipos contrastados.
- Conjuntos de mejora de fotovoltaica, aislamiento y sustitución de ventanas contrastados, con sus datos económicos.
- Textos con acentos, eñes y diéresis, reparando los escapes literales reconocidos.

Los originales se conservan y el trabajo se realiza localmente. Si ya existe una salida con ese nombre, se pide confirmación antes de sustituirla.

## Antes de utilizar el resultado

Es una herramienta experimental, no oficial. El estado **REVISAR** indica comprobaciones estructurales, no validación en CE3X.

**Recalcula el edificio, los conjuntos de mejora y el análisis económico en CE3X 2.3.** Los resultados guardados proceden de la versión 3.2. Revisa las instalaciones y regenera los informes y complementos.

No garantiza compatibilidad universal ni genera por sí sola certificados, XML de registro o justificaciones HE0/HE1. La apertura, edición y el recálculo de los resultados siguen pendientes de validación en CE3X 2.3.

## Si encuentras un fallo

Pulsa **Guardar diagnóstico** para exportar un ZIP con la información del último intento. En **Notas y adjunto** puedes añadir una explicación y un log o captura. No se generan logs automáticamente: guarda el diagnóstico antes de cerrar el programa o hacer otra conversión.

Indica la versión del conversor, qué estabas haciendo y el mensaje exacto en [Issues](https://github.com/xSeeSx/Conversor-CE3X-3.2-a-CE3X-2.3/issues). Si adjuntas un diagnóstico, revísalo antes: puede contener datos del proyecto.

## Desarrollo

La próxima versión 1.4.0 se está preparando: salida junto al original y diagnóstico guardado solo a petición. Todavía no está publicada en Releases. Las instrucciones anteriores corresponden a la versión 1.4.0 disponible para descargar.

El código de la interfaz está en `fuentes/launcher.c` y el motor en `app/converter.py`. Para ejecutar desde los fuentes, compilar o colaborar, consulta la [guía de desarrollo](docs/DESARROLLO.md). Las notas técnicas de validación de la versión 1.3 están en `fuentes/VALIDACION.txt`.
