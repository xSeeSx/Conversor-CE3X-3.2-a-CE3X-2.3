# Validación integral del conversor CE3X

Ensayo local del 19 de noviembre de 2026 sobre la base `b42c9d5`. Se usaron CE3X 2.3 y 3.2 instalados en Windows, la vivienda docente del paquete oficial 3.2 y copias sintéticas derivadas. Los CEX y XML de trabajo permanecen locales. Los resultados de 3.2 y 2.3 de las sesiones previas se mantienen en los informes de procedencia. [Validación real de la vivienda oficial](VALIDACION_REAL.md) · [Equivalencias y límites](EQUIVALENCIAS_Y_LIMITES.md)

## Reproducir

```powershell
python -B -X utf8 scripts/validar_bateria_final.py preparar C:\CE3X-pruebas\bateria --oficial32 'C:\CE3X-pruebas\2 Vivienda dentro de bloque.cex'
python -B -X utf8 scripts/validar_bateria_final.py recoger C:\CE3X-pruebas\bateria
```

Abre cada copia 2.3 de la carpeta con CE3X, califica, guarda y exporta el XML junto al CEX usando el mismo nombre base. Repite con `directo32_recalculado.cex` en 3.2 para el control entre motores. El script deja los orígenes e iniciales en subcarpetas, verifica sus hashes y recoge los resultados en JSON y CSV. El parámetro `--persiana32` permite usar el CEX nativo del ensayo de persiana, verificado por SHA256. Sin ese parámetro, se reproduce la configuración con la fixture de campos observados. Usa `--exportaciones` para recoger las copias guardadas desde otra carpeta.

La comprobación de Windows prepara la misma batería sin abrir CE3X y adjunta el resumen estructural junto al ZIP de compilación. El script local distingue esa comprobación de las exportaciones hechas en la aplicación.

## Batería

| Caso | Conversión y conservación | Resultado en CE3X 2.3 |
| --- | --- | --- |
| Directa sin pérdidas | `REVISAR`, cero entradas activas omitidas. Se conserva el modelo común. | Apertura, recálculo, guardado y XML comprobados. |
| Persiana manual omitida | Advertencia y consentimiento. V5 conserva sus propiedades térmicas comunes y vuelve al control sin persiana. | Apertura, recálculo, guardado y XML comprobados. El XML coincide byte a byte con el control directo. |
| Termosolar D2 adaptado | Advertencia y consentimiento. Cobertura anual de ACS del 70 % en el caso de 100 m² y 100 L/día. | Apertura, recálculo, guardado y XML D2 comprobados. El consumo final de ACS es 6,06 kWh/m²·año. |
| Termosolar D2 omitido | Advertencia y consentimiento. Se retira el generador sin alterar el equipo de ACS. | Apertura, recálculo, guardado y XML D2 comprobados. El consumo final de ACS es 20,19 kWh/m²·año. |
| Termosolar D2 cancelado | Se pulsa Cancelar en el protocolo del lanzador. El origen conserva su hash y no se crea salida. | Se verifica la finalización sin archivo. |
| Envolvente ampliada y fotovoltaica anual | Diez tipologías, hueco conocido y estimados, puentes, sombras, dos zonas anidadas, calderas mixtas y refrigeración. Se conserva la contribución eléctrica anual en la forma compatible. | Apertura, recálculo, guardado y XML comprobados. La contribución mensual sigue fuera del alcance y tiene prueba de bloqueo. |
| Tres mejoras con costes | Tres conjuntos, siete filas de costes y referencias del ejemplo oficial conservados. El plan solicita consentimiento por campos auxiliares de 3.2. | Apertura, recálculo del edificio base, guardado y XML comprobados. La comprobación del recálculo individual se trata por separado. |

La batería compara las referencias, áreas, transmitancias, factores solares de vidrio, longitudes y Ψ, grupos de instalaciones y cantidades de mejoras. La salida directa conserva esos datos del origen. Los grupos vacíos exclusivos de 3.2 se retiran según el esquema. Los CEX iniciales y sus orígenes conservaron el SHA256. La conversión conserva exactamente los dos patrones de sombras. Al guardar en 2.3, la aplicación actualizó los coeficientes calculados de ambos patrones y conservó sus polígonos, nombres y referencias. Este cambio se verificó entre el CEX recién convertido y el CEX guardado por CE3X 2.3.

## Indicadores observados

| Caso en CE3X 2.3 | Calefacción | Refrigeración | Demanda ACS | Energía primaria no renovable | Emisiones | Letra de emisiones |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Directo | 117,27 | 0,90 | 23,81 | 187,98 | 39,77 | E |
| Persiana omitida | 117,27 | 0,90 | 23,81 | 187,98 | 39,77 | E |
| Termosolar adaptado | 156,96 | 9,76 | 20,19 | 224,39 | 46,61 | E |
| Termosolar omitido | 156,96 | 9,76 | 20,19 | 252,01 | 51,29 | E |
| Envolvente y fotovoltaica anual | 150,86 | 0,02 | 23,81 | 231,64 | 49,05 | E |
| Tres mejoras, edificio base | 118,25 | 0,83 | 23,81 | 189,22 | 40,04 | E |

Las demandas y la energía primaria no renovable se expresan en kWh/m²·año. Las emisiones se expresan en kgCO₂/m²·año. Los dos primeros casos comparan la misma geometría y equipos dentro de CE3X 2.3. En D2, la adaptación reduce el consumo final de ACS de 20,19 a 6,06 kWh/m²·año, con la misma demanda. Los valores coinciden a la precisión del XML con el ensayo nativo anterior. Los totales entre edificios con distinta geometría, clima o instalaciones se muestran como resultados de cada ensayo. [Ensayo nativo termosolar](VALIDACION_SOLAR.md)

Durante el ensayo se corrigió la recogida del consumo final en XML 2.3. El fichero publica ese valor por vector y servicio. El banco lo conserva con su etiqueta y unidad, separado del indicador agregado de formato 3.2. Una regresión comprueba la distinción.

## Límites pendientes

1. Obtener y conservar evidencia del recálculo de los conjuntos en CE3X 2.3. El XML de edificio base puede omitir resultados individuales.
2. Completar los controles nativos equivalentes en 3.2 y 2.3 donde falten. La sesión 1 midió diferencias de +0,01 en energía primaria no renovable y emisiones, sin una referencia 2.3 independiente para atribuirlas.
3. Mantener bloqueadas las equivalencias que carecen de prueba. En la persiana manual, **Otros** conserva los factores estacionales y altera el CTE de 0,345 a 1. En generación mensual y ventilación residencial faltan modelos comparables. [Matriz de compatibilidad](MATRIZ_COMPATIBILIDAD.md)
