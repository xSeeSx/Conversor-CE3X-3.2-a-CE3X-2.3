# Conversor CE3X 3.2 a CE3X 2.3

Conversor experimental de archivos `.cex` residenciales de CE3X 3.2 a CE3X 2.3 para Windows 10/11 de 64 bits.

## Descargar

[**Descargar para Windows, versión 1.5.3**](https://github.com/xSeeSx/Conversor-CE3X-3.2-a-CE3X-2.3/releases/download/v1.5.3/Conversor_CE3X_Windows_1_5_3.zip)

[Releases y notas de cada versión](https://github.com/xSeeSx/Conversor-CE3X-3.2-a-CE3X-2.3/releases) · [Historial de cambios](CHANGELOG.md)

El ZIP incluye el ejecutable y Python. En Releases, descarga `Conversor_CE3X_Windows_1_5_3.zip`. Los archivos **Source code** contienen los fuentes.

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

## Funcionalidades nuevas de 3.2 todavía no adaptadas

La siguiente tabla distingue **adaptar**, **omitir con consentimiento** y **bloquear**. Es el estado del conversor, no una afirmación de que CE3X 2.3 carezca de todos esos elementos. El código de desarrollo en `main` puede ir por delante de la [última release publicada](https://github.com/xSeeSx/Conversor-CE3X-3.2-a-CE3X-2.3/releases).

| Funcionalidad de origen 3.2 | Estado actual | Consecuencia para el usuario |
| --- | --- | --- |
| Persianas nuevas de huecos (tres campos adicionales) | **No adaptadas** | Solo se pueden omitir, con consentimiento, cuando no están combinadas con otras protecciones, sombras o mejoras; se restablecen los factores solares a 1. En las demás combinaciones se bloquea. |
| Solar térmica con producción mensual | **Adaptación muy limitada** | Solo se adapta a porcentaje anual de ACS en el [ensayo D2 documentado](docs/EQUIVALENCIAS_Y_LIMITES.md#termosolar-mensual-para-acs). En otros casos conocidos puede ofrecer omisión consentida; si hay dependencias inseguras, bloquea. |
| Generadores eléctricos con producción mensual | **Sin equivalencia validada** | Bloquea. Falta identificar el autoconsumo correspondiente a servicios computables, distinto de la generación total. |
| Ventilación y ventiladores activos en residencial, incluida recuperación de calor | **Sin equivalencia validada** | Bloquea. No se sustituye el efecto térmico y eléctrico por un descuento genérico. |
| Instalaciones nuevas, acumulación y campos adicionales de equipos | **Según estructura contrastada** | Conserva datos comunes; determinadas colas adicionales pueden retirarse con consentimiento. Estructuras activas desconocidas bloquean. |
| Mejoras que incluyen generadores nuevos o protecciones no contrastadas | **Según dependencias** | Bloquea o, cuando está documentado y se autoriza, retira la mejora y las referencias asociadas; no elimina componentes en silencio. |

Los cerramientos de las diez tipologías, las particiones interiores y los huecos convencionales tienen reglas de conservación. Para el inventario completo de campos y variantes, consulta la [matriz de compatibilidad](docs/MATRIZ_COMPATIBILIDAD.md) y el [inventario de omisiones](docs/OMISIONES_1_5_2.md).

## Criterios y fórmulas de adaptación

**Regla general:** una equivalencia numérica no basta por sí sola. Se comprueba primero con dos modelos nativos comparables, uno en CE3X 3.2 y otro en 2.3; después se contrasta el archivo convertido con el modelo nativo 2.3. Los cálculos solo se habilitan en las condiciones efectivamente ensayadas. Cuando no se conoce una equivalencia, se bloquea o se solicita consentimiento para una omisión segura.

### Solar térmica mensual a cobertura anual de ACS (implementada únicamente en el ensayo D2)

```text
Q_solar_anual [kWh/año] = suma(Q_solar_mes[m], m=1..12)
D_ACS [kWh/año] = 360 × 4,18 × 100 × (60 - 11,7) / 3600 = 2.018,94
Cobertura_ACS_2.3 [%] = 100 × Q_solar_anual / D_ACS
```

**Condiciones del ensayo:** zona D2, 100 m², 100 L/día de ACS, un equipo eléctrico de efecto Joule con rendimiento y cobertura del 100 %, sin acumulación ni otras instalaciones o contribuciones. La producción debe ser positiva y no superar la demanda calculada. Esta fórmula **no es una regla general para cualquier edificio**. Se conservan los valores energéticos anuales ensayados, pero se pierden el reparto mensual y la potencia de la instalación. [Datos y resultados del ensayo](docs/VALIDACION_SOLAR.md).

### Persianas de 3.2 a «Otros» en 2.3 (hipótesis, no implementada)

En un ensayo de persiana manual blanca, CE3X 3.2 guardó `correctorFSInvierno = 1`, `correctorFSVerano = 0,345` y `correctorFSCTE = 0,345`. Introducir **Otros** en CE3X 2.3 con `OtroInvierno = 1` y `OtroVerano = 0,345` produjo los mismos indicadores energéticos **en esa vivienda y a la precisión exportada**, pero el archivo 2.3 guardó `correctorFSCTE = 1`, no 0,345.

La correspondencia candidata es:

```text
OtroInvierno_2.3 = correctorFSInvierno_3.2
OtroVerano_2.3   = correctorFSVerano_3.2
```

**No se aplica automáticamente:** faltan controles sin persiana, combinaciones con sombras y mejoras, y validación del factor CTE. No se debe conservar ni inventar `correctorFSCTE` como si ambos programas lo calcularan igual. [Ensayo y discrepancia](docs/EQUIVALENCIAS_Y_LIMITES.md#persianas-de-huecos).

### Generación fotovoltaica mensual a contribución anual (criterio candidato, no implementado)

```text
E_equivalente_2.3 [kWh/año] = suma(E_autoconsumida_en_servicios_computables_mes[m], m=1..12)
```

**No equivale a sumar la producción fotovoltaica total.** Antes de automatizarlo hay que verificar qué energía es realmente autoconsumida en los servicios del certificado, cómo trata CE3X 2.3 esa contribución y qué ocurre con los excedentes. Las contribuciones **anuales** que ya tienen formato nativo compatible se conservan sin esta transformación. [Límites actuales](docs/EQUIVALENCIAS_Y_LIMITES.md#generacion-electrica-instalaciones-y-ventilacion).

### Ventilación, recuperadores y otras instalaciones (sin fórmula segura)

No hay una fórmula general validada para convertir caudal, recuperación térmica y consumo de ventiladores en una única reducción anual. Tampoco se deduce el consumo a partir de la potencia nominal de un equipo. Hasta obtener ensayos nativos equivalentes, los sistemas activos sin regla contrastada **se bloquean**, sin adaptar ni omitir silenciosamente.

**Mantenimiento de este apartado:** cada equivalencia nueva debe actualizar su estado, fórmula, unidades, condiciones, evidencia, pérdidas y pruebas. Las instrucciones para agentes de programación están en [AGENTS.md](AGENTS.md).

## Antes de utilizar el resultado

Es una herramienta experimental, no oficial. El estado **REVISAR** indica comprobaciones estructurales, no validación en CE3X.

**Recalcula el edificio, los conjuntos de mejora y el análisis económico en CE3X 2.3.** Los resultados guardados proceden de la versión 3.2. Revisa las instalaciones y regenera los informes y complementos.

Cuando el conversor detecta datos activos que puede omitir con seguridad, presenta un único inventario antes de crear la salida. Incluye los elementos afectados, las dependencias y los cambios de cada opción. La selección inicial es **Cancelar**. Si el programa detecta una estructura cuyo descarte es inseguro, muestra el diagnóstico y detiene la conversión.

- **Omitir lo indicado y convertir** aplica el inventario de omisiones mostrado.
- **Adaptar y convertir** conserva la cobertura anual de ACS en el caso termosolar ensayado y aplica las omisiones que figuran en esa opción. La adaptación pierde el reparto mensual y la potencia solar. [Alcance del ensayo](docs/EQUIVALENCIAS_Y_LIMITES.md#termosolar-mensual-para-acs)
- **Cancelar** termina la operación sin crear salida.

Cuando se acepta una opción con pérdidas, el estado **CONVERSION_CON_OMISIONES** identifica el resultado y muestra lo retirado o simplificado. El diagnóstico registra la decisión si el usuario solicita exportarlo. Consulta el [inventario de omisiones](docs/OMISIONES_1_5_2.md) y los [ensayos y límites de la adaptación solar](docs/VALIDACION_SOLAR.md).

La conversión tiene alcance residencial. Se comprobó la apertura, el guardado, el recálculo y la exportación XML de seis salidas en CE3X 2.3. Consulta el [informe de validación final](docs/INFORME_VALIDACION_FINAL.md) para conocer los casos ensayados y sus límites.

## Si encuentras un fallo

Pulsa **Guardar diagnóstico** para exportar un ZIP con la información del último intento. En **Notas y adjunto** puedes añadir una explicación y un log o captura. No se generan logs automáticamente: guarda el diagnóstico antes de cerrar el programa o hacer otra conversión.

Indica la versión del conversor, qué estabas haciendo y el mensaje exacto en [Issues](https://github.com/xSeeSx/Conversor-CE3X-3.2-a-CE3X-2.3/issues). Si adjuntas un diagnóstico, revísalo antes: puede contener datos del proyecto.

## Desarrollo

El código de la interfaz está en `fuentes/launcher.c` y el motor en `app/converter.py`. Para ejecutar desde los fuentes, compilar o colaborar, consulta la [guía de desarrollo](docs/DESARROLLO.md). Las notas técnicas de validación de la versión 1.3 están en `fuentes/VALIDACION.txt`.
