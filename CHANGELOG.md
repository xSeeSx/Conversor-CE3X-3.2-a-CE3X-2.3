# Historial de cambios

Las versiones publicadas y sus descargas están en [Releases](https://github.com/xSeeSx/Conversor-CE3X-3.2-a-CE3X-2.3/releases).

## 1.4.1, 2026-11-17

- Ventana inicial más baja: se elimina la fila de salida y el texto explicativo repetido.
- La dirección de conversión se integra en el título: Conversor CE3X 3.2 → 2.3.
- Se conservan la versión, Residencial y el aviso de revisar y recalcular en CE3X 2.3.
- El estado solo aparece al iniciar una operación o recibir un resultado; no reserva espacio en reposo.
- Comprobación de los ejemplos del instalador oficial, identificando la versión real de cada archivo.

## 1.4.0, 2026-11-17

### Interfaz

- Nuevo estilo técnico compacto: gris claro, controles rectos y acento índigo.
- Notas y adjunto en un panel desplegable.
- Escalado de la ventana y los controles según la configuración DPI de Windows.

### Cambios de uso

- El resultado se guarda en la misma carpeta que el origen como `nombre_CE3X2.3.cex`.
- Se pide confirmación antes de sustituir una salida existente. El original se conserva.
- Los registros y errores se conservan en memoria durante la sesión.
- El ZIP y sus logs solo se escriben al pulsar **Guardar diagnóstico**, con notas y un adjunto opcionales.
- Se eliminan la selección de carpeta de salida y las carpetas automáticas por intento.
- La plantilla estructural incluida se utiliza automáticamente.

### Documentación y desarrollo

- README centrado en descargar y usar; compilación y pruebas trasladadas a la guía de desarrollo.
- Historial consolidado en este archivo, conservando las notas de versiones anteriores.
- Pruebas de salida, sobrescritura, diagnóstico a petición y comunicación persistente.
- Comprobación de compilación e integración nativa Windows en GitHub Actions.

Se mantiene la necesidad de revisar y recalcular los resultados en CE3X 2.3.

## 1.3.0

- Se convierten los conjuntos contrastados de medidas de mejora.
- Proyeccion de clases/campos internos al esquema nativo 2.3 sin valores ajenos.
- Adaptacion de parametros numericos y contribuciones fotovoltaicas.
- Conservacion de equipos, definiciones, textos y datos economicos de conjuntos.
- Facturas, tarifas, costes y seleccion de conjuntos del informe conservados.
- Caches guardadas identificadas como origen 3.2, pendientes de recalculo.
- Conversion conserva ciclos y referencias compartidas de los grafos.
- Reparacion siempre automatica de escapes de acentos, enes y dieresis.
- Casilla retirada de la interfaz. CLI anterior compatible, reparacion obligatoria.
- Acentos mayusculos y escapes Unicode completos, sin modificar texto correcto.
- Logger con ubicacion de los datos internos de cada conjunto.
- Tipos nuevos sin equivalencia: error diagnosticable, sin eliminacion silenciosa.
- 49 pruebas y conversion estructural de dos archivos reales, 2 conjuntos cada uno.

## 1.2.0

- Correccion de E_READ en bloque 5, STRING con acentos en Python 3.11.
- Inspector de protocolo 0 con decodificacion Latin-1 explicita.
- Se conservan los offsets y se rechazan protocolos binarios antes de leerlos.
- No se modifica pickletools globalmente ni se reescribe el origen.
- Autotest ampliado con cadenas Latin-1 crudas y escapadas.
- Logger inicial: Python, plataforma, codificacion e inspector.
- 40 pruebas superadas, incluido el lector ASCII emulado de Python 3.11.
- Error exacto reproducido con version 1.1 y origen de tu intento;
  origen[5] @ 69249, byte 0xf1 en posicion 34. Version 1.2 lo convierte.
- Ejecutable recompilado con identificador 1.2.0.

## 1.1.0

- Lectura y escritura controlada de Decimal en resultados antiguos.
- Campos generales adicionales 3.2: inventario, aviso y control de superficie.
- Campo adicional vacio en configuracion del informe: retirada registrada.
- Lista de clases contrastadas para impedir trasladar clases exclusivas 3.2.
- Verificacion de todas las propiedades de ventanas y bibliotecas conservadas.
- La reparacion de acentos mantiene activas las comprobaciones de conservacion.
- Boton Intento previo para anadir logs tras cerrar y reabrir el programa.
- 36 pruebas automaticas. Conversion estructural de dos archivos reales.
