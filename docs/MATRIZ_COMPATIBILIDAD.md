# Matriz de compatibilidad residencial CE3X 3.2 → 2.3

La matriz recoge las reglas y su evidencia. **E** indica transferencia directa comprobada para los campos citados. **C** indica una equivalencia calculada que requiere validación fuera del ensayo citado. **S** indica simplificación con posible pérdida. **N** indica ausencia de equivalencia comprobada. **?** identifica una estructura o variante sin evidencia suficiente. La igualdad estructural y el recálculo de un caso concreto tienen alcances distintos.

## Origen y alcance de la evidencia

- **N23** son las muestras residenciales del instalador CE3X 2.3 y el esquema de clases de mejora derivado de ellas. [Muestras y procedencia](VALIDACION_1_4_1.md) · [Esquema y hashes](../app/mm_schema_23.json)
- **P23** son las salidas de los diez paneles de envolvente originales de 2.3 y, para las particiones, los registros adicionales contrastados. [Sonda](../scripts/inspeccionar_paneles_23.py) · [Registros obtenidos](../fuentes/fixtures/envolvente_nativa_23.json) · [Particiones](../fuentes/fixtures/particiones_oficiales_23.json)
- **O32** son las dos muestras residenciales del instalador oficial 3.2. Se prueban por hash y se conserva el origen. [Regresión](../scripts/probar_ejemplos.py) · [Procedencia y hashes](VALIDACION_1_4_1.md)
- **R** son las pruebas sintéticas y los rechazos explícitos de estructuras desconocidas. [Pruebas del motor](../fuentes/test_converter.py)
- **T** son los ensayos nativos termosolares acotados descritos con sus resultados. [Ensayos](VALIDACION_SOLAR.md)
- **V** es la apertura, el recálculo y la exportación de la vivienda oficial convertida, con el alcance detallado en el informe. [Validación real](VALIDACION_REAL.md)

## Bloques del proyecto

| Bloque | Clase, campos o variante conocida | Estado | Evidencia y criterio |
| --- | --- | --- | --- |
| 0. Cabecera | `CE3Xv3.2 Residencial` → `CEXv2.3 Residencial` | E | Perfil, R y V. Los archivos terciarios quedan fuera del ámbito. |
| 1. Datos administrativos | 26 posiciones comunes de 29 en 3.2 | E | R. Se conserva el prefijo y se reparan escapes de texto reconocidos. |
| 1. Datos administrativos | Posiciones 26–28 de 3.2 | S | O32 y R. Se inventarían si contienen datos. Estructuras fuera de las formas observadas se bloquean. |
| 2. Datos generales | 21 posiciones comunes, incluida superficie útil [6], altura [7], zona [4] y demanda diaria ACS [9] | E | O32 y R. Se comprueba la conservación del valor común. V confirma apertura para la vivienda ensayada. |
| 2. Datos generales | Posiciones 21–25 de 3.2, incluida segunda superficie [22] | S / ? | O32 y R. [22] puede diferir de [6]. Se solicita consentimiento para los valores activos. Falta establecer el significado completo del resto de posiciones. |
| 3. Cerramientos | Diez tipologías, tabla inferior | E | P23 y R. Longitud nativa exacta, área, U y campos auxiliares preservados. |
| 3. Huecos | `HuecoConocidas` y `HuecoEstimadas`, superficie, U vidrio/marco, g, asociación y patrón | E | N23, O32 y R. `correctorSolar` es opcional en huecos estimados. V confirma apertura para huecos de la muestra. |
| 3. Huecos | Protección nativa, 25 campos y factores estacionales | E | N23 y R. Se conservan los valores comunes cuando el dispositivo sigue presente. |
| 3. Huecos | UUID y tres campos nuevos de protección | S / experimental | **Otros** 2.3 usa los dos factores estacionales guardados de persianas manuales aisladas de cualquier color y pone el factor CTE a 1. Se pierden el tipo y el color. La traducción de los factores se contrastó con el caso blanco. Automatismos aislados se pueden omitir con consentimiento. Sombras combinadas y mejoras de huecos bloquean. |
| 3. Puentes térmicos | Fila de 9 posiciones, ψ [3], longitud [4], cerramiento [7] | E | O32, R y V. Datos preservados y asociación al cerramiento validada. |
| 3 y 7. Zonas y subgrupos | `ventanaSubgrupo.claseZona`, cuatro campos del esquema, relaciones anidadas | E | N23, O32 y R. Incluye las zonas presentes en el grafo de mejoras. Faltan combinaciones de uso y ventilación. |
| 4. Instalaciones | Matriz de 14 grupos → 12, tabla inferior | E / S / N | O32, R y T. Instalaciones nuevas activas se bloquean salvo las rutas termosolares descritas. |
| 5. Mejoras | `grupoMedidasMejora`, aislamiento (13 campos), huecos (21) y puentes (20) | E | N23, O32 y R. Se conservan las definiciones comunes y sus clases. Los cálculos del grafo de origen requieren recálculo. |
| 5. Mejoras | Instalaciones en definiciones y en modelos original/nuevo, datos generales auxiliares, bibliotecas del modelo calculado | E / S / ? | N23, O32 y R. Se proyectan los campos comunes. Los metadatos y bibliotecas auxiliares activos se inventarían. Las clases y los campos nuevos sin regla se bloquean. |
| 5. Mejoras | Campos `ordenPrioridad`, `seRecomienda`, `justificacion`, coeficientes y resultados mensuales | S | O32 y R. Los tres metadatos requieren consentimiento cuando tienen valor. Las series de resultados reconocidas se registran para recálculo. |
| 5 y 6. Mejora termosolar y dependencias | `listadoGeneradoresTermosolarMM`, definición, copias del equipo, filas de coste y selecciones del informe | S / C | O32, R y T. Omitir retira el conjunto y sus referencias. Adaptar conserva las actuaciones de envolvente reconocidas, los costes y las referencias. Es experimental en mejoras combinadas, con igual zona, superficie y caudal de ACS y copias coherentes. |
| 6. Análisis económico | Cuatro posiciones, facturas, costes [2], inversión, vida útil y mantenimiento del conjunto | E / ? | N23, O32 y R. Se comprueban entradas comunes y coste asociado. Queda por contrastar el recálculo de amortizaciones y los cambios de estructura. |
| 8. Biblioteca de cerramientos | `LibreriasCE3X.menuCerramientos.composicionCerramiento` | E / ? | N23 y R. Se conserva el bloque tipado. Quedan por contrastar catálogos 3.2 independientes de materiales, vidrios y marcos. |
| 9 y 10. Sombras | Registros de polígonos y coeficientes y lista de nombres | E | O32, R y V. Conservación tipada y comprobación de referencias de huecos y cerramientos. [Fixture](../fuentes/fixtures/sombras_oficiales.json) |
| 11. Informe | Selecciones de mejora, texto y fechas en los siete campos comunes | E / S | O32 y R. Se conserva informe vacío o nativo. Se retira el octavo campo vacío y se bloquea si está activo. |
| 12. Complementos | Diccionario de entradas por nombre, caso `Icaen` observado | S / ? | O32 y R. Reinicio de entradas escalares con consentimiento. Estructuras compuestas se bloquean. |
| 13 y 14. Reservados | Indicador 13 y token de 32 bytes en Base64 14 | ? | O32, N23 y R. Se conserva el 13 cuando coincide con la plantilla y se registra la sustitución del token con forma conocida. El significado interno sigue pendiente. |

## Cerramientos

Todos los registros de esta tabla están contrastados en P23 y cubiertos por R. La clave se construye con el tipo [1] y el contacto en la última posición. La superficie está en [2], U en [3] y la referencia de sombra en [7].

| Tipo y contacto | Campos 2.3 | Estado | Dato particular conservado |
| --- | ---: | --- | --- |
| Fachada · aire | 15 | E | U, orientación y configuración del muro exterior |
| Fachada · edificio | 13 | E | Medianería y valores de la fila nativa |
| Fachada · terreno | 15 | E | Características del muro en contacto con terreno |
| Cubierta · aire | 15 | E | Valores de cubierta exterior |
| Cubierta · terreno | 16 | E | Espesor de terreno adicional |
| Suelo · aire | 15 | E | Valores de suelo exterior |
| Suelo · terreno | 17 | E | Geometría y parámetros nativos del contacto |
| Partición interior · horizontal superior | 15 | E | Configuración del espacio contiguo |
| Partición interior · vertical | 15 | E | Variantes conocida y estimada |
| Partición interior · horizontal inferior | 15 | E | Variantes conocida y estimada |

## Instalaciones y renovables

| Grupo y estructura | Estado | Evidencia y límite |
| --- | --- | --- |
| [0] ACS, [1] calefacción, [2] refrigeración, [3] climatización, [4] mixto2, [5] mixto3 | E / S | N23, O32 y R. Tipo, combustible, rendimiento [2], cobertura [5], modo [6] y parámetros [7] se conservan. La cola escalar 3.2 del registro de 11 posiciones requiere aviso si contiene datos. |
| Acumulación [8] | E / N | `panelInstalaciones.cogerDatosDelPanel` en ambos motores y R. Se conserva el UA conocido (6 campos), por defecto (6 o 7) y estimado por aislamiento (9), incluido el multiplicador cuando existe. Métodos y formas desconocidos bloquean. |
| [6] Contribuciones energéticas y fotovoltaica anual, formato de seis campos | E / C | N23, R. Se conserva el valor anual de una contribución conocida. La producción mensual, el autoconsumo computable y el tratamiento de excedentes quedan pendientes. |
| [7] Iluminación, [8] ventilación, [9] ventiladores, [10] bombas, [11] torres de refrigeración | N | El Manual de usuario CE3X, tabla de instalaciones por uso y §§4.4.2–4.4.3, reserva el aire primario y ventiladores para uso terciario. La tasa de renovación residencial se conserva sin ajustes. |
| [12] Termosolar mensual `models.GeneradorTermosolar` | C / S | T prueba un generador D2 con 100 m², 100 L/día de ACS y efecto Joule al 100 %, sin acumulación ni otras instalaciones o contribuciones. En ese supuesto se adapta a cobertura anual. En desarrollo, se usan el volumen diario y las temperaturas de red nativas para proyectar experimentalmente en otras zonas y superficies. Puede omitirse cuando cabe conservar las dependencias. |
| [13] Generación eléctrica renovable mensual sin mejoras | Experimental / N | El panel mensual guarda doce valores de autoconsumo EPB. Se suman para el campo eléctrico anual nativo 2.3. Se pierde potencia, identificador y serie mensual. Otras series y dependencias de mejora quedan bloqueadas. |

Cada nueva equivalencia deberá partir de una pareja nativa probada en ambas versiones. Consulta los [ensayos y límites de la sesión 2](EQUIVALENCIAS_Y_LIMITES.md) y el [banco de validación](VALIDACION_REAL.md).
