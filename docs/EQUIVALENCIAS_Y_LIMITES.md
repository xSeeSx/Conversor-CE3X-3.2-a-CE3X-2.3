# Equivalencias y límites de conversión

La versión 1.5.3 incorpora la evidencia de las sesiones originales. La 1.5.4 añade las opciones experimentales de ACS y persianas descritas aquí. Para atribuir una diferencia al conversor hacen falta tres resultados. Se comparan primero los modelos nativos 3.2 y 2.3 de la misma configuración. Después se compara el 2.3 convertido con la referencia nativa 2.3. El banco local genera las diferencias absolutas y relativas para magnitudes con igual unidad. Cuando la base es cero, informa solo de la diferencia absoluta. [Matriz](MATRIZ_COMPATIBILIDAD.md) · [Banco local](VALIDACION_REAL.md)

## Persianas de huecos

La sonda de los módulos instalados ejecutó `Envolvente.panelHuecos.panelHuecos.cogerDatosSombras` con controles representados y sin sustituir el método de serialización. La fila 2.3 acaba con `Otro_Si` y el par `[OtroInvierno, OtroVerano]`. La fila 3.2 añade `Persianas_Si`, `Persianas` y `Persianas_Color`. El módulo nativo de 3.2 recibe parámetros adicionales y el panel distingue el umbral de activación y la fracción de tiempo de la persiana. Los correctores almacenados requieren contraste energético en ambas versiones para demostrar que el efecto persiste al cambiar de representación.

El ensayo local se prepara con `python -B scripts/preparar_ensayo_persianas.py <ejemplo-oficial-32> <carpeta-nueva>`. Parte del ejemplo oficial **2 Vivienda dentro de bloque**, verificado por SHA256. Se retiran las mejoras del ensayo y sus referencias. V5, orientación sur y 0,94 m², se deja sin voladizo ni patrón de sombras. Las demás ventanas conservan su configuración. El usuario añadió una persiana manual blanca en 3.2 y obtuvo `correctorFSCTE=0,345`, `correctorFSInvierno=1` y `correctorFSVerano=0,345`. Los resultados del XML se conservan localmente.

Se introdujeron esos dos correctores estacionales con **Otros** directamente en CE3X 2.3 y se recalculó y exportó el edificio. El archivo 2.3 guardó `Otro_Si=True` y `[OtroInvierno, OtroVerano]=["1", "0.345"]`. Conservó ambos factores estacionales y guardó **`correctorFSCTE=1`**. En 3.2 el campo CTE guardado es **0,345**. Es un contraejemplo a sustituir la persiana por **Otros** conservando los tres campos.

| Indicador exportado | Persiana nativa 3.2 | Otros nativo 2.3 |
| --- | ---: | ---: |
| Demanda de calefacción, kWh/m²·año | 117,27 | 117,27 |
| Demanda de refrigeración, kWh/m²·año | 0,78 | 0,78 |
| Demanda de ACS, kWh/m²·año | 23,81 | 23,81 |
| Energía primaria no renovable, kWh/m²·año | 187,86 | 187,86 |
| Emisiones, kgCO₂/m²·año | 39,75 | 39,75 |
| Calificación global de emisiones | E | E |

En esta vivienda los indicadores coinciden a la precisión publicada por el XML. Esa coincidencia tiene un alcance distinto al de conservar el factor CTE. La batería final contrastó el control sin persiana en ambas versiones y la salida con omisión en 2.3. Faltan ensayos con sombra combinada y mejoras. La **adaptación experimental** de una persiana manual blanca aislada y activa escribe los factores estacionales en `Otros` si los tres correctores están entre 0 y 1. El factor CTE toma el valor nativo 1 y se pierden el dispositivo y su color. La salida convertida se abrió, recalculó, guardó y exportó en CE3X 2.3. Los tres correctores guardados y las 62 magnitudes comparables extraídas del XML coincidieron con la referencia nativa 2.3. La omisión aislada exige consentimiento y restablece los factores a 1. El CEX 3.2 del ensayo conservó su hash durante la conversión. [Factores, resultados y hashes](../fuentes/fixtures/persiana_ce3x.json) · [Batería final](INFORME_VALIDACION_FINAL.md)

## Termosolar mensual para ACS

En ambos ejecutables instalados se ejecutó `Calculos.funcionesCalculo.getDiccionarioTemperaturasAguaRedACS()`. La tabla coincide entre las dos versiones y, para A3, A4, B3, B4, C1, C2, C3, C4, D1, D2, D3 y E1, coincide también entre las variantes peninsular y extrapeninsular. La selección territorial para las claves exclusivas queda pendiente.

```text
producción_anual [kWh/año] = suma(producción_mensual)
demanda_ACS [kWh/año] = 360 × 1 kg/L × 4,18 kJ/(kg·K) × litros_ACS_día × (60 °C − T_red_zona) / 3600
cobertura_2.3 [%] = 100 × producción_anual / demanda_ACS
```

La superficie del CEX solo se usa para verificar que el área cubierta concuerda con el 100 % declarado. El ensayo histórico D2 de 100 m², 100 L/día y 11,7 °C conserva la opción contrastada. Los demás casos admitidos llevan aceptación experimental explícita. Se exige un equipo eléctrico de efecto Joule conocido, rendimiento y cobertura del 100 %, sin acumulación, consumos mensuales separados ni otras aportaciones. Las mejoras combinadas con envolvente quedan fuera de la adaptación. Producciones nulas, no finitas o superiores a la demanda se rechazan para adaptar. La salida pierde meses, potencia e identificador del generador. El diagnóstico registra fórmula, parámetros y decisión.

Las regresiones prueban D1, D2 y C3 con superficies, volúmenes y temperaturas distintos. `scripts/sondar_temperaturas_acs.py` reproduce la extracción con `probe_python27`. `scripts/preparar_ensayo_acs.py` prepara las parejas D1 y D2 para abrir y exportar desde los dos programas.

| Caso | Superficie (m²) | ACS (L/día) | Producción (kWh/año) | Demanda ACS (kWh/m²·año) | ACS final eléctrico (kWh/m²·año) | Primaria ACS no renovable (kWh/m²·año) | Emisiones ACS (kg CO₂/m²·año) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| D1 | 150 | 112 | 480 | 15,23 | 12,03 | 23,51 | 3,98 |
| D2 | 85 | 75 | 744 | 17,81 | 9,06 | 17,71 | 3,00 |

Los cuatro CEX se abrieron, recalcularon, guardaron y exportaron en sus respectivas versiones. Las cifras de la tabla coinciden entre los dos motores al centésimo. En 2.3 se usa el indicador por vector de electricidad peninsular y en 3.2 el total de ACS, que en estos ensayos solo tiene un equipo y vector. Los consumos finales coinciden también con el balance proyectado. Tras corregir el UUID termosolar y la referencia catastral de los casos de prueba, los dos XML exportados directamente por CE3X 3.2 superaron su esquema Relax NG. El exportador requirió introducir la potencia nominal de 2 kW del equipo de ACS de ensayo. La comparación respalda estos dos casos y la adaptación general sigue siendo experimental. [Ensayo histórico](VALIDACION_SOLAR.md) · [Fixture D2](../fuentes/fixtures/solar_d2_ensayos.json)

## Generación eléctrica, instalaciones y ventilación

| Caso | Evidencia disponible y decisión |
| --- | --- |
| Contribución anual en formato nativo | Se conserva la energía declarada en las filas compatibles. La prueba de conservación verifica su valor y su tipo de destino. |
| Generación eléctrica mensual | El constructor nativo 3.2 de `models.GeneradorElectrico` expone tipo, potencia, meses y `consumoMensual`. Esa forma por sí sola no acredita qué electricidad se autoconsume en servicios computables ni qué parte se exporta. El diagnóstico identifica el dato pendiente y bloquea. |
| Nuevos generadores y acumulación | Para habilitar equivalencias adicionales hacen falta el servicio, la entrada física común y ensayos por tipo de equipo. Un valor de potencia nominal no aporta por sí solo el consumo anual. Los grupos activos desconocidos se bloquean. |
| Ventilación o ventiladores activos | El diagnóstico identifica el equipo y la necesidad de contrastar caudal, recuperación y consumo en 2.3 residencial. Se conserva el bloqueo. |
| Mejoras combinadas | Se conservan tipos, equipos y costes contrastados. Las copias discordantes, los generadores activos sin equivalencia y las protecciones con dependencias sin validar se bloquean. Cuando una omisión termosolar retira una mejora, elimina el conjunto y las referencias comprobadas tras consentimiento. |

El panel mensual 3.2 distingue el cálculo de la generación total del autoconsumo en servicios EPBD. El panel anual de ambos motores identifica su campo como generación eléctrica para autoconsumo. Falta comprobar el significado de cada campo serializado y el cómputo nativo de 2.3 con excedentes. Los paneles de ventilación de ambos motores exponen caudal y recuperador. Falta comprobar su uso real en residencial y dónde se contabiliza la electricidad auxiliar. Se mantienen los bloqueos.
