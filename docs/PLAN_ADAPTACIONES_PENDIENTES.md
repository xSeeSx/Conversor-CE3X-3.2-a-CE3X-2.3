# Adaptaciones pendientes CE3X 3.2 → 2.3

Documento de trabajo para Codex. **No describe funcionalidades ya disponibles.** Priorizar el uso del banco local y los ejecutables CE3X 2.3 y 3.2 instalados. Cada equivalencia requiere evidencia nativa y pruebas de regresión. No hacer promesas de compatibilidad sin validación.

## P0 - Generalizar la adaptación de solar térmica mensual a ACS

**Problema actual (motor 1.5.3):** `solar_candidate()` en `app/converter.py` exige literalmente zona `D2`, superficie de `100 m²`, ACS de `100 L/día`, un único equipo eléctrico por efecto Joule con 100 % de rendimiento y cobertura, y ausencia de acumulación y otras instalaciones. Estas eran las condiciones del **ensayo**, no reglas universales de conversión. En un certificado corriente se impide adaptar aunque los datos sean perfectamente reconocibles.

**Objetivo:** calcular la conversión a cobertura anual de ACS a partir de **los valores propios del certificado**, sin exigir que replique el caso de prueba. Eliminar las restricciones artificiales de 100 m² / 100 L/día; ampliar a zonas climáticas distintas de D2 empleando la temperatura de agua fría y los criterios de cálculo correspondientes según documentación y motor CE3X 2.3. Investigar los equipos y situaciones adicionales por separado, sin extrapolar arbitrariamente.

### Modelo físico candidato a comprobar en motores nativos

```text
Q_solar_anual [kWh/año] = suma(Q_solar_mensual[m], m=1..12)
D_ACS_anual [kWh/año] = dias_23 × ρ_agua × c_agua × V_ACS_dia × (T_ACS - T_fria_zona) / 3600
Cobertura_ACS_23 [%] = 100 × Q_solar_anual / D_ACS_anual
```

En unidades del ensayo: `dias_23=360`, `ρ_agua≈1 kg/L` absorbida al usar litros/día, `c_agua=4,18 kJ/(kg·K)`, `T_ACS=60 °C` y `T_fria_D2=11,7 °C`. **No suponer que esas constantes o el balance anual basten para todos los casos:** obtener temperaturas y criterio de demanda por zona de fuentes nativas del programa, identificar las condiciones de acumulación y producción mensual, y documentar los límites. La superficie del edificio solo se utiliza donde realmente intervenga en el método nativo; no imponer 100 m² ni igualdades ajenas a la fórmula.

### Tareas técnicas

1. Inspeccionar `solar_candidate()`, `solar_issues()`, `resolve_solar()`, las contribuciones de ACS de 2.3 y el manejo de conjuntos de mejora.
2. Extraer y contrastar de CE3X 2.3 las temperaturas de agua fría por zona climática y cualquier condición de cálculo efectiva. Conservar la procedencia y las unidades.
3. Separar claramente **restricción estructural auténtica**, **caso aún no ensayado** y **dato imposible de interpretar**. No tratar los dos primeros como sinónimos.
4. Calcular con demanda de ACS real, usando volumen diario y zona reales. Validar producción anual, unidades, valores nulos, límites físicos, redondeos, cobertura y conservación de equipos; no duplicar aportes ni convertir producción exportada en autoconsumo.
5. Ensayar al menos dos zonas climáticas distintas, varios caudales de ACS (diferentes de 100 L/día), varias superficies, y coberturas distintas; controlar con modelos comparables construidos y recalculados en CE3X 3.2 y 2.3. Añadir escenarios con equipo distinto, acumulación, múltiples generadores y mejoras para determinar qué **se puede** ampliar y qué **no**.
6. Incluir una prueba automática que demuestre que el antiguo caso D2 sigue funcionando y varias que demuestren que los valores no se codifican a `100` ni a `D2`. Comparar demanda, consumo final ACS, primaria y emisiones con igualdad de unidades y tolerancias justificadas.
7. Mantener decisión explícita: **Adaptar y convertir** para casos validados; cuando la estructura sea conocida pero no haya suficiente evidencia energética, evaluar ofrecer **Adaptación experimental** claramente marcada con valores de entrada, fórmula, pérdida de detalle, consentimiento expreso y recalculo obligatorio, **solo** si el CEX 2.3 es válido y permite comprobación. Conservar **Omitir** (si dependencias seguras) y **Cancelar**. **Nunca** omitir en silencio ni generar un archivo inválido solo por forzar la conversión.
8. Si hay bloqueo real, mostrar **la razón concreta** (por ejemplo, servicio no ACS, acumulación no interpretable, generadores compartidos), no un genérico «no coincide con D2».
9. Documentar por cada combinación admitida su fórmula, hipótesis, pruebas, pérdidas y estado en `docs/EQUIVALENCIAS_Y_LIMITES.md`, `docs/MATRIZ_COMPATIBILIDAD.md`, y actualizar el README de forma breve.

### Criterio de finalización P0

- Una instalación solar típica ya **no** queda excluida solo por su zona, superficie o litros de ACS.
- Se contrastan en la aplicación real variantes fuera del ejemplo original.
- Se conserva el CEX de origen, el esquema de destino es reconocido por 2.3 y la decisión/pérdida de información aparece antes de escribir.
- Pruebas locales y de regresión pasan; los cambios de alcance quedan documentados.
- No declarar «universal» la adaptación mientras existan equipos o condiciones sin prueba.

## Backlog de funcionalidades nuevas no adaptadas

| Prioridad | Funcionalidad | Estado del motor 1.5.3 | Siguiente paso de ingeniería |
| --- | --- | --- | --- |
| P1 | Persianas nuevas 3.2 | Solo omisión explícita en huecos aislados; sombras combinadas o mejoras bloquean. | Ensayar traducción a «Otros» 2.3, analizar discrepancia de `correctorFSCTE`, contrastar refrigeración/calefacción, sombras y mejoras. |
| P1 | Generación eléctrica/fotovoltaica **mensual** | Se bloquea la estructura nueva activa. Fotovoltaica **anual** compatible ya se conserva. | Determinar qué energía es autoconsumida computable y qué se exporta; construir equivalentes nativos con excedentes y distintos servicios. |
| P2 | Ventilación y recuperadores/ventiladores activos | Se bloquean los grupos sin estructura residencial equivalente. | Distinguir consumo de ventiladores, caudales y efecto de la recuperación; probar representaciones nativas, no descontar energía sin respaldo. |
| P2 | Mejora con elementos nuevos, generadores compartidos o dependencias desconocidas | Se bloquea cuando no se pueden preservar referencias. | Ampliar inspección de copias de equipos, medidas combinadas y costes; consentir omisión solo si se retira limpiamente el conjunto afectado. |
| P3 | Acumuladores, metadatos y combinaciones residenciales sin ejemplos | Solo tipos contrastados; extras conocidos con consentimiento; formatos desconocidos bloqueados. | Ensayos adicionales y matriz de decisión por subtipo. |

**Importante:** que CE3X 3.2 posea un campo nuevo **no significa** que sea energéticamente relevante ni que deba bloquearse siempre. Clasificar con pruebas: conservar, calcular, omitir con aviso, o bloquear. No confundir la conservación de la estructura con la igualdad de resultados energéticos.

## Forma de trabajar

- Primero P0. Reutilizar `scripts/validar_bateria_final.py` y las pruebas locales; evitar interacciones gráficas repetitivas.
- No modificar a ciegas las fórmulas de certificación. Obtener primero el método y un caso de referencia.
- Hacer commits por hito, registrar las pruebas y no publicar nueva versión sin integración Windows y evidencia de los nuevos casos.
- Mantener este documento como backlog técnico de Codex y conservar el README público sintetizado. No enlazar este plan de agentes desde el README.
