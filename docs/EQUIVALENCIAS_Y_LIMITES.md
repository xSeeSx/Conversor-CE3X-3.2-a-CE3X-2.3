# Equivalencias y límites de conversión

Los criterios y cambios de la sesión 2 se incorporan a la versión 1.5.3. Para atribuir una diferencia al conversor hacen falta tres resultados. Se comparan primero los modelos nativos 3.2 y 2.3 de la misma configuración. Después se compara el 2.3 convertido con la referencia nativa 2.3. El banco local genera las diferencias absolutas y relativas para magnitudes con igual unidad. Cuando la base es cero, informa solo de la diferencia absoluta. [Matriz](MATRIZ_COMPATIBILIDAD.md) · [Banco local](VALIDACION_REAL.md)

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

En esta vivienda los indicadores coinciden a la precisión publicada por el XML. Esa coincidencia tiene un alcance distinto al de conservar el factor CTE. Faltan los controles recalculados sin dispositivo y los ensayos con sombra combinada y mejoras. La opción de adaptación sigue deshabilitada. La omisión aislada exige consentimiento y restablece los factores a 1. Se verificó el flujo con el CEX 3.2 del ensayo y se comprobó que el archivo de origen conservaba su hash. [Factores, resultados y hashes](../fuentes/fixtures/persiana_ce3x.json)

## Termosolar mensual para ACS

La adaptación anual queda ceñida al modelo medido. La opción exige 100 m², 100 L/día de ACS, zona D2, un solo equipo eléctrico de efecto Joule, rendimiento y cobertura del 100 %, sin acumulación ni otras instalaciones o contribuciones declaradas. Si el proyecto declara una segunda superficie, debe coincidir con la común. Los valores de depósito presentes pese al indicador de acumulación desactivado también dejan el caso fuera del ensayo. Fuera de ese alcance, la omisión consentida se mantiene donde las dependencias lo permiten.

```text
producción_anual [kWh/año] = suma(producción_mensual)
demanda_ACS [kWh/año] = 360 × 4,18 × 100 × (60 − 11,7) / 3600 = 2018,94
cobertura_2.3 [%] = 100 × producción_anual / demanda_ACS
```

El diagnóstico incluye los doce valores de entrada, la potencia declarada, los parámetros de cálculo, la fórmula y la fuente de evidencia. El formato 2.3 conserva la cobertura anual calculada y pierde el reparto mensual, la potencia y el identificador del generador. Producciones nulas, no finitas o superiores a la demanda quedan fuera del cálculo. Las pruebas verifican la cobertura calculada y serializada con los cuatro perfiles del ensayo. La comparación energética usa la precisión publicada por los XML, con consumos finales de ACS de 6,06 o 18,33 kWh/m²·año según el caso. [Resultados originales](VALIDACION_SOLAR.md) · [Fixture D2](../fuentes/fixtures/solar_d2_ensayos.json)

## Generación eléctrica, instalaciones y ventilación

| Caso | Evidencia disponible y decisión |
| --- | --- |
| Contribución anual en formato nativo | Se conserva la energía declarada en las filas compatibles. La prueba de conservación verifica su valor y su tipo de destino. |
| Generación eléctrica mensual | El constructor nativo 3.2 de `models.GeneradorElectrico` expone tipo, potencia, meses y `consumoMensual`. Esa forma por sí sola no acredita qué electricidad se autoconsume en servicios computables ni qué parte se exporta. El diagnóstico identifica el dato pendiente y bloquea. |
| Nuevos generadores y acumulación | Para habilitar equivalencias adicionales hacen falta el servicio, la entrada física común y ensayos por tipo de equipo. Un valor de potencia nominal no aporta por sí solo el consumo anual. Los grupos activos desconocidos se bloquean. |
| Ventilación o ventiladores activos | El diagnóstico identifica el equipo y la necesidad de contrastar caudal, recuperación y consumo en 2.3 residencial. Se conserva el bloqueo. |
| Mejoras combinadas | Se conservan tipos, equipos y costes contrastados. Las copias discordantes, los generadores activos sin equivalencia y las protecciones con dependencias sin validar se bloquean. Cuando una omisión termosolar retira una mejora, elimina el conjunto y las referencias comprobadas tras consentimiento. |

Las aproximaciones de producción mensual a autoconsumo anual, de recuperador a descuento genérico y de factores de persiana a correcciones equivalentes siguen como hipótesis de ensayo. El cálculo sin interfaz de `datosEdificio.calificacion` no reprodujo los resultados de control de la sesión 1. Para la evidencia energética de esta sesión se utilizan únicamente exportaciones de la aplicación completa y los ensayos nativos ya documentados.
