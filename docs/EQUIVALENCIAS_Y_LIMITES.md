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

La salida convertida de la persiana blanca se abrió, recalculó, guardó y exportó en CE3X 2.3. Los tres correctores guardados y las 62 magnitudes comparables del XML coincidieron con la referencia nativa 2.3. La **adaptación experimental** reutiliza esa misma regla para persianas manuales aisladas y activas de cualquier color informado. Lee los dos factores estacionales guardados y los escribe en `Otros` si los tres correctores están en [0,1]. El factor CTE toma el valor nativo 1 y se pierden el tipo y el color. La regla no vuelve a calcular el factor a partir del color ni de la geometría. Los automatismos tienen condiciones horarias adicionales, y las sombras combinadas y mejoras siguen bloqueadas. La omisión aislada exige consentimiento y restablece los factores a 1. [Factores, resultados y hashes](../fuentes/fixtures/persiana_ce3x.json) · [Batería final](INFORME_VALIDACION_FINAL.md)

## Termosolar mensual para ACS

En ambos ejecutables instalados se ejecutó `Calculos.funcionesCalculo.getDiccionarioTemperaturasAguaRedACS()`. La tabla coincide entre las dos versiones y, para A3, A4, B3, B4, C1, C2, C3, C4, D1, D2, D3 y E1, coincide también entre las variantes peninsular y extrapeninsular. La selección territorial para las claves exclusivas queda pendiente.

```text
producción_anual [kWh/año] = suma(producción_mensual)
demanda_ACS [kWh/año] = 360 × 1 kg/L × 4,18 kJ/(kg·K) × litros_ACS_día × (60 °C − T_red_zona) / 3600
cobertura_2.3 [%] = 100 × producción_anual / demanda_ACS
```

La superficie del CEX solo se usa para verificar que el área cubierta concuerda con el 100 % declarado. El ensayo histórico D2 de 100 m², 100 L/día y 11,7 °C conserva la opción contrastada. Los demás casos admitidos llevan aceptación experimental explícita. Se exige un equipo eléctrico de efecto Joule conocido, rendimiento y cobertura del 100 %, sin acumulación, consumos mensuales separados ni otras aportaciones. Una mejora de la envolvente puede combinarse con solar en modo experimental si conserva los parámetros de ACS y las copias son coherentes. Producciones nulas, no finitas o superiores a la demanda se rechazan para adaptar. La salida pierde meses, potencia e identificador del generador. El diagnóstico registra fórmula, parámetros y decisión.

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
| Generación eléctrica mensual | Adaptación experimental al campo anual eléctrico 2.3 para la serie EPB nativa, sin mejoras. Si el CEX lleva un balance mensual calculado, debe coincidir con la serie declarada. |
| Depósitos de ACS | Se conservan los formatos de UA conocido, por defecto y estimado por aislamiento, incluido el multiplicador de 7 o 9 campos cuando existe. |
| Ventilación o ventiladores activos | Los Manuales de usuario CE3X reservan los paneles de aire primario a pequeño y gran terciario y los de ventiladores a gran terciario. Se conserva el bloqueo residencial y la tasa de renovación original. |
| Mejoras combinadas | Se admite experimentalmente solar de ACS con actuaciones de envolvente reconocidas y parámetros de ACS invariantes. Conserva el conjunto, las copias coherentes, los costes y las referencias. Las copias discordantes y otros generadores o protecciones con dependencias no representables siguen bloqueados. |

La ayuda del panel mensual 3.2 pide al técnico introducir la energía autoconsumida en los servicios EPB. `Instalaciones.panelGeneradorElectrico.Panel1.cogerDatos` lee una fila de doce valores y los serializa en `enero` a `diciembre` de `models.GeneradorElectrico`, con `tipo=None` y `consumoMensual=None` antes de calificar. Al guardar tras el recálculo, el motor rellenó `consumoMensual` con los mismos doce valores en ambos ensayos. La fórmula aplicada es `E_anual [kWh/año] = Σ E_EPB_mes [kWh]`. Se conserva la zona y se identifica la contribución con el nombre del generador. Se pierden potencia, identificador y distribución mensual. El Manual de octubre de 2026, §7, distingue esta serie de la producción total, que incluye excedentes. [Manual oficial de ampliación](https://www.miteco.gob.es/content/dam/miteco/es/energia/eficiencia/certificacionenergetica/documentosreconocidos/procedimientoscertificacion/ce3x/Ampliaci%C3%B3n%20Manual_usuario_CE3X.pdf)

`python -B -X utf8 scripts/preparar_ensayo_fv.py <origenes/acs_D132.cex> <carpeta-nueva>` prepara un control en cada versión, una serie de 10 kWh/mes, otra de 120 kWh en julio y una referencia anual de 120 kWh en 2.3. Los tres modelos con aporte eléctrico coincidieron tras el recálculo en 180,76 kWh/m²·año de primaria no renovable y 37,05 kg CO₂/m²·año de emisiones globales. Para ACS coincidieron en 15,23 kWh/m²·año de electricidad final, 29,76 kWh/m²·año de primaria no renovable y 5,04 kg CO₂/m²·año. La comparación es al centésimo. El ensayo avala la suma anual para la configuración probada. Otras imputaciones por servicio y valores superiores a la demanda mensual siguen sin contraste.

El método nativo `Instalaciones.panelVentilacion.Panel1.cogerDatos` devuelve la misma fila de seis campos en 2.3 y 3.2. Para 125 m³/h y 85 % se obtiene `[nombre, "ventilacion", "125", True, "85", zona]`. El Manual de usuario CE3X, tabla de instalaciones por uso y §§4.4.2–4.4.3, explica el ámbito terciario de estos paneles. Para una vivienda, bajar la tasa de renovación cambiaría el caudal declarado y dejaría sin representar el consumo auxiliar. [Estudio de IDAE sobre CE3X, sección de ventilación](https://www.idae.es/sites/default/files/documentos/publicaciones_idae/estudios_004_impacto_solar_termica_en_cee_v2.pdf)

En ACS, `panelInstalaciones.cogerDatosDelPanel` de 2.3 y 3.2 serializa volumen (L), consignas (°C), UA (W/K) y método en las mismas posiciones. Los métodos por defecto y estimado guardan además el multiplicador adimensional. Estimado conserva también espesor y material del aislamiento. El ejemplo oficial **1 Bloque de viviendas** usa el multiplicador 10 en el séptimo campo. Se conserva tal cual. Si un generador nuevo depende de un depósito, su balance sigue fuera de la adaptación termosolar.

CE3X 2.3 abrió y recalculó una copia convertida con la fila de depósito de ese ejemplo y guardó los siete campos con el multiplicador 10. También exportó una mejora combinada con sustitución de ventanas y 480 kWh/año de solar para ACS. El consumo final de ACS de la mejora fue 12,03 kWh/m²·año y el del edificio base 15,23. La mejora mantuvo la selección de informe y sus dos filas de coste.
