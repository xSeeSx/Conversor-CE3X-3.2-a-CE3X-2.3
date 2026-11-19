# Historial de cambios

## 1.5.2

- Inventario previo de recortes y reinicios, con elementos afectados, dependencias y consentimiento explícito antes de crear la salida.
- Bloqueo de formatos sin una regla segura y comprobación de referencias al retirar conjuntos de mejora.
- Resumen `CONVERSION_CON_OMISIONES` y diagnóstico bajo petición. Se mantiene la adaptación termosolar del caso ensayado.
- Regresiones sintéticas para pérdidas simultáneas, cancelación, consentimiento caducado y campos desconocidos. Las dos muestras residenciales oficiales comprueban la decisión previa y la conservación del original.

## 1.5.1 - 2026-11-18

- Admitida la clase nativa de zonas y añadida una prueba con zonas anidadas.

- Corregido el rechazo de particiones interiores verticales y horizontales inferiores compatibles con CE3X 2.3.
- Ampliado el catálogo de cerramientos a diez tipologías, incluyendo muros y cubiertas en contacto con el terreno. La cubierta enterrada conserva sus 16 campos, incluido el espesor de terreno.
- Contrastada su estructura de 15 campos con las particiones del ejemplo oficial nativo 2.3. Los datos se conservan sin transformar sus valores.
- Aviso y decisión explícita antes de omitir las protecciones solares nuevas sin equivalente ensayado, sin dejar factores solares incoherentes.
- Añadidas pruebas de conservación y rechazo de estructuras desconocidas. No cambia el ámbito residencial del conversor.


Las versiones publicadas y sus descargas están en [Releases](https://github.com/xSeeSx/Conversor-CE3X-3.2-a-CE3X-2.3/releases).

## 1.5.0

- Aviso previo para generadores termosolares: Adaptar, Omitir lo indicado o Cancelar. No genera salida sin decidir.
- Adaptación anual a cobertura ACS en la configuración ensayada de efecto Joule eléctrico sin acumulación en D2, tanto en edificio como en mejora solar independiente.
- Adaptar deshabilitado en casos no validados. Omitir una mejora elimina el conjunto completo y sus referencias de costes e informe, según advierte el diálogo.
- Resumen visible de las decisiones, exportadas al diagnóstico únicamente si se solicita.
- Comprueba que el origen no cambie durante las decisiones.
- Acepta el informe vacío observado en archivos nativos de ambas versiones.
- Documentación de los ensayos de producción mensual y mejoras.

## 1.4.1, 2026-11-17

- Ventana inicial más baja: se elimina la fila de salida y el texto explicativo repetido.
- La dirección de conversión se integra en el título: Conversor CE3X 3.2 → 2.3.
- Se conservan la versión, Residencial y el aviso de revisar y recalcular en CE3X 2.3.
- El estado solo aparece al iniciar una operación o recibir un resultado; no reserva espacio en reposo.
- Corregida una comparación incorrecta entre superficies generales de 3.2: se conserva la superficie nativa común y se registra el campo adicional.
- `correctorSolar` pasa a ser opcional en huecos estimados de mejoras, contrastado con ejemplos nativos 2.3.
- Soporte de las mejoras de puentes térmicos con el formato observado en los ejemplos oficiales 2.3 y 3.2.
- Esquema de mejoras ampliado con campos opcionales contrastados en los ejemplos oficiales 2.3.
- Regresión del ejemplo oficial residencial con dos patrones de sombras, siete ventanas y tres conjuntos de mejora.
- Los generadores termosolares nuevos sin equivalencia contrastada siguen produciendo un error explícito.

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
