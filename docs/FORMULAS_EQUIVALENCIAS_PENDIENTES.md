# Fórmulas candidatas para adaptaciones CE3X 3.2 → 2.3

**Encargo técnico para Codex, no funcionalidad implementada.** Fórmulas físicas y pruebas preparadas para ahorrar investigación repetida. **Una fórmula físicamente correcta no demuestra que el campo de destino residencial 2.3 la reproduzca.** Antes de habilitar cada adaptación, comprobar en los ejecutables nativos CE3X 3.2 y 2.3, guardar modelos de control y validar el CEX convertido. No modificar el caudal higiénico exigible ni ocultar pérdidas.

## 1. Recuperador de calor aire-aire sensible, candidato P2

### 1.1 Potencia recuperada y temperatura de impulsión

Para recuperadores **sensibles**, sin condensación y con condiciones estables:

```text
C_imp   [W/K] = rho_aire [kg/m3] × cp_aire [J/(kg K)] × V_imp [m3/h] / 3600
C_ext   [W/K] = rho_aire × cp_aire × V_ext [m3/h] / 3600
C_min   [W/K] = min(C_imp, C_ext)
P_rec   [W]   = epsilon_sensible × C_min × (T_extraccion - T_exterior)
T_impulsion_tras_recuperador = T_exterior + P_rec / C_imp
```

Valores de referencia aproximados, **no propiedades exactas constantes de la instalación**: `rho_aire ≈ 1,2 kg/m3`, `cp_aire ≈ 1005 J/(kg K)`. Para caudales **equilibrados** `V_imp=V_ext=V`:

```text
P_rec [W] ≈ 0,335 × V [m3/h] × epsilon_sensible × (T_extraccion - T_exterior) [K]
             ≈ 0,34 × V × epsilon_sensible × delta_T
T_impulsion ≈ T_exterior + epsilon_sensible × (T_extraccion - T_exterior)
```

**Eficiencia:** `epsilon_sensible` es adimensional (p. ej. 80 % → 0,80). Si la ficha da eficacia definida respecto al caudal exterior/impulsión en vez de `C_min`, respetar **esa definición** y evitar el doble factor de caudales. Con caudales desequilibrados se debe identificar la definición de rendimiento usada por CE3X antes de calcular.

Ejemplo equilibrado: `V=150 m3/h`, `epsilon=0,80`, `T_interior=20 °C`, `T_exterior=5 °C`:

```text
P_rec ≈ 0,34 × 150 × 0,80 × 15 = 612 W
T_impulsion ≈ 5 + 0,80 × (20 - 5) = 17 °C
```

La energía térmica de **1.000 h a esas mismas condiciones** sería ≈ `612 kWh`, **no una predicción anual automática**.

### 1.2 Energía por periodos de cálculo

```text
Q_rec_sensible [kWh] = suma_t( max_uso_t × P_rec_t [W] × horas_t [h] / 1000 )
```

Aquí `max_uso_t` es 0/1 o fracción de funcionamiento, según el horario; el signo y la oportunidad de recuperación dependen de la estación. Para **calefacción**, usar los periodos con demanda y `T_extraccion > T_exterior`. Para **refrigeración**, evaluar la reducción de carga de enfriamiento cuando el aire exterior está más caliente que el extraído, con **bypass/free cooling** si el aire exterior favorece enfriar gratuitamente. No sumar todo `abs(delta_T)` anual ni permitir recuperación de signo contrario que perjudique la demanda.

Cuando solo existen caudal nominal, eficiencia nominal y horas nominales, la energía anual **no es única** sin temperaturas, horarios, bypass y control. No inventar un resultado fijo.

### 1.3 Recuperador entálpico (sensible + latente), caso distinto

Con humedad específica `w [kg_vapor/kg_aire_seco]`:

```text
h [kJ/kg_aire_seco] ≈ 1,006 × T_C + w × (2501 + 1,86 × T_C)
P_total [W] = m_aire_seco [kg/h] × (h_salida - h_entrada) [kJ/kg] / 3,6
```

El cálculo necesita eficacia entálpica o sensible/latente **según su definición** y humedades. No sumar una recuperación latente ficticia a un equipo exclusivamente sensible. Tampoco asumir que todos los recuperadores son entálpicos.

### 1.4 Posible analogía térmica en 2.3 (NO implementar como equivalencia hasta validar)

Para ventilación mecánica equilibrada con eficacia sensible constante y sin bypass, la **carga sensible** se aproxima a la de un caudal exterior sin recuperación:

```text
V_equiv_termico = V_otro_sin_recuperacion + (1 - epsilon_sensible) × V_mecanico_recuperado
n_equiv_termico [ren/h] = V_equiv_termico [m3/h] / Volumen_habitable [m3]
```

Ejemplo: `V_mec=150 m3/h`, `epsilon=0,8`, sin otras entradas de aire, `V_equiv_termico=30 m3/h`. **Eso no significa que la vivienda ventile solo 30 m3/h:** sigue entrando aire higiénico a 150 m3/h. Es un equivalente **exclusivamente de intercambio sensible para condiciones ideales**, no de calidad del aire, infiltraciones, latente ni potencia eléctrica.

**Criterio de seguridad:** no reemplazar sin más la tasa de ventilación general de CE3X 2.3 por esa tasa equivalente. Se debe demostrar que el motor 2.3 usa ese campo exclusivamente para la parte que se quiere aproximar y que la representación respeta los requisitos de ventilación. De no haber mapeo defendible, la solución es omisión consentida o bloqueo, no una calificación alterada arbitrariamente.

### 1.5 Información mínima de ensayo y test

- Tipo de recuperador; caudales **impulsión y extracción**, rendimiento estacional/nominal y su definición; horarios, bypass, zonas, condiciones térmicas; electricidad de ventiladores.
- Verificar en CE3X 3.2 el grupo y los campos `equipos aire primario` / `ventiladores` y cómo alteran los resultados. En 2.3 residencial no hay correspondencia comprobada en el conversor actual.
- Modelos: ventilación sola; recuperador 50/80 %; dos caudales; verano bypass; ventilador integrado/no integrado; mejora independiente/combinada; distintas zonas. Contrastar calefacción, refrigeración, electricidad final, energía primaria y emisiones.
- Tests aritméticos: `epsilon=0 → P_rec=0`, `delta_T=0 → P_rec=0`, `V=0 → P_rec=0`, caudal de extracción limitante, rendimiento entre `0..1`, unidades, y ausencia de doble cómputo.

**Fuente principal:** IDAE/MITECO, *Guía técnica de ahorro y recuperación de energía en instalaciones de climatización*, sección 4.1, fórmula `E=m_aire_seco × Δh × t` y eficacias sensible, latente y total: https://www.miteco.gob.es/content/dam/miteco/es/energia/files-1/Eficiencia/RITE/documentosreconocidosrite/Gu%C3%ADas%20t%C3%A9cnicas/Guia_Climatizacion_Ahorro.pdf

## 2. Ventiladores y electricidad auxiliar, candidato P2

Si el CEX declara **consumo eléctrico anual medido/estimado computable**, usar ese dato, sin reconstruirlo artificialmente:

```text
E_ventiladores [kWh/año] = suma_t( P_electrica_t [kW] × horas_t [h] )
```

Si solo declara caudal, pérdida de carga y rendimiento global de **motor + ventilador**, se puede **estimar** la potencia eléctrica:

```text
P_electrica [W] = suma_corrientes( delta_p [Pa] × V [m3/h] / (3600 × eta_total) )
E_ventiladores [kWh/año] = P_electrica [W] × horas_funcionamiento [h] / 1000
```

`eta_total` debe corresponder realmente al conjunto eléctrico del cálculo; no confundir eficiencia aerodinámica, motor, SFP y energía declarada. Si `P` ya es eléctrico, **no** dividir otra vez entre rendimiento. Si hay múltiples velocidades, calcular `Σ P_i h_i / 1000`; la ley cúbica `P ∝ V^3` solo es candidata para instalaciones cuya curva y control justifiquen esa aproximación.

Ejemplo: dos ventiladores de `40 W` cada uno, ambos durante `2000 h` → `E=(40+40)×2000/1000=160 kWh/año`.

**No** restar esta electricidad directamente de la demanda de calefacción; distinguir energía térmica recuperada de consumo eléctrico final, y nunca duplicar el consumo del propio equipo si CE3X ya lo incorpora. Identificar si CE3X 2.3 residencial tiene campo capaz de preservar el consumo antes de habilitar.

## 3. Generación fotovoltaica o eléctrica mensual, candidato P1

El **manual oficial de ampliación CE3X de octubre de 2026**, apartado 7, dice expresamente que los datos mensuales autoconsumidos en servicios EPB los calcula previamente el técnico, **no el programa**. Incluye calefacción, refrigeración y ACS en residencial privado; no incluye electrodomésticos ni iluminación doméstica. Por tanto:

```text
E_generada_anual = suma_12meses(E_generada_mes)
E_autoconsumida_EPB_anual = suma_12meses(E_autoconsumida_EPB_mes)
0 ≤ E_autoconsumida_EPB_mes ≤ E_generada_mes   (si ambas magnitudes cubren la misma instalación)
```

**Conversión candidata a la contribución eléctrica anual de 2.3**:
```text
E_equivalente_23 = E_autoconsumida_EPB_anual
```

Esta última asignación **no está validada**: confirmar que el campo anual 2.3 contabiliza la misma energía, servicios, signo y factores de paso; no confundir energía generada ni consumo total de vivienda. Si 3.2 solo muestra producción mensual sin dato EPB fiable, **no se puede deducir el autoconsumo** con esta fórmula. No estimar `min(E_generada_mes, E_consumo_EPB_mes)` sin evidencia de coincidencia temporal, almacenamiento y criterios del motor.

**Fuente oficial:** MITECO, *Ampliación del manual de usuario CE3X*, octubre 2026, apartado 7: https://www.miteco.gob.es/content/dam/miteco/es/energia/eficiencia/certificacionenergetica/documentosreconocidos/procedimientoscertificacion/ce3x/Ampliaci%C3%B3n%20Manual_usuario_CE3X.pdf

## 4. Persianas nuevas y sombreamiento, candidato P1

Ensayo del proyecto: persiana manual blanca 3.2 produjo `correctorFSInvierno=1`, `correctorFSVerano=0,345`, `correctorFSCTE=0,345`. Introducir «Otros» de 2.3 con:

```text
OtroInvierno_23 = correctorFSInvierno_32
OtroVerano_23   = correctorFSVerano_32
```

reprodujo indicadores anuales **para la vivienda ensayada** pero modificó `correctorFSCTE` a 1. Esto **no es** una equivalencia completa. Ver `docs/EQUIVALENCIAS_Y_LIMITES.md`. Las persianas manuales/automáticas, colores, uso estacional, patrones de sombras y medidas de mejora necesitan contrastes separados. No combinar factores multiplicándolos sin demostrar cómo los combina el motor.

## 5. Solar térmica ACS, P0: usar datos del certificado

Se mantiene como prioridad `docs/PLAN_ADAPTACIONES_PENDIENTES.md`. Base:

```text
D_ACS_kWh = dias × rho_agua × c_agua × litros_ACS_dia × (T_ACS - T_fria_zona) / 3600
Cobertura_porcentaje = 100 × suma_12meses(E_solar_termica_mes) / D_ACS_kWh
```

En el ejemplo D2: `dias=360`, `rho≈1kg/L`, `c=4,18kJ/(kg K)`, `T_ACS=60 °C`, `T_fria=11,7 °C`. Son **parámetros de partida del ensayo**, no un mandato de D2 / 100 m² / 100 L/día para todos los certificados. Obtener `T_fria_zona` del criterio CE3X 2.3, validar cobertura/depósitos/sistemas y usar caudal real. No ampliar a todos los servicios sin prueba.

## 6. Regla de implementación y entrega

1. **Identificar primero el campo real** en el CEX 3.2, sus unidades y si mide total, sensible, EPB o auxiliar. No asumir por el nombre del atributo.
2. Calcular magnitud y unidades con estas fórmulas en **funciones puras locales**, sin abrir CE3X para cada cálculo.
3. **Separar** (a) cálculo físico, (b) representación 2.3, y (c) contraste energético. El paso (a) **no** autoriza el (b) ni el (c).
4. Documentar subtipos y casos que no se pueden representar; mantener bloqueo cuando el CEX destino sea inválido o altere la calificación sin control.
5. Añadir tests de unidades, límites, conservación, decisión previa y aceptación. Comparar modelos nativos de ambos programas y el convertido. Actualizar la matriz y README **solo al implementar y ensayar**, no ahora.

Estas fórmulas cubren la **investigación teórica preliminar**, no sustituyen el trabajo de integración y validación en ambos motores.
