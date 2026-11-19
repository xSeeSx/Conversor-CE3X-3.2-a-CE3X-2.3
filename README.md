# Conversor CE3X 3.2 a CE3X 2.3

Convierte archivos `.cex` **residenciales** de CE3X 3.2 para abrirlos en CE3X 2.3. Funciona en Windows 10/11 de 64 bits.

## Descargar y usar

**[Descargar última versión para Windows](https://github.com/xSeeSx/Conversor-CE3X-3.2-a-CE3X-2.3/releases/latest)**

1. Descarga `Conversor_CE3X_Windows_*.zip` y **extrae todo**. No ejecutes el `.exe` separado de sus carpetas.
2. Abre `Conversor_CE3X.exe`, arrastra tu archivo y pulsa **Convertir**.
3. Abre `nombre_CE3X2.3.cex` en CE3X 2.3 y **recalcula** antes de emitir informes.

El original no se modifica. El resultado se guarda junto a él. La conversión se realiza localmente.

## Qué funciona y qué falta

| Elemento de CE3X 3.2 | Estado |
| --- | --- |
| Cerramientos (10 tipologías), ventanas convencionales, puentes térmicos y sombras | ✅ Se conservan los datos contrastados |
| Instalaciones habituales, fotovoltaica **anual** y mejoras compatibles con sus costes | ✅ Se conservan los datos contrastados |
| Solar térmica **mensual** | ⚠️ Solo se adapta en una configuración de prueba muy concreta: zona D2, 100 m², ACS de 100 L/día y equipo eléctrico específico. En los demás casos, omisión consentida o bloqueo |
| Persianas nuevas | ⚠️ Solo omisión consentida si están aisladas; combinadas con sombras o mejoras, bloqueo |
| Generación eléctrica **mensual** | ❌ Sin adaptación validada, bloqueo |
| Ventilación, recuperadores y otros sistemas nuevos activos | ❌ Sin adaptación validada, bloqueo |

**Nunca se eliminan datos activos sin avisar.** El programa detalla las pérdidas y pide confirmación, con **Cancelar** como opción inicial. Si no puede convertir u omitir algo con seguridad, se detiene.

## Criterios y fórmulas de adaptación

**Solo se habilitan equivalencias contrastadas en CE3X 2.3 y 3.2.** No se equipara una fórmula plausible con una conversión validada.

**Solar térmica: adaptación experimental, no general.** Solo se ofrece si el edificio reproduce exactamente el caso de prueba:

```text
Solar_anual (kWh) = suma de las 12 producciones mensuales
Demanda_ACS (kWh) = 360 × 4,18 × 100 × (60 - 11,7) / 3600 = 2.018,94
Cobertura_ACS_2.3 (%) = 100 × Solar_anual / Demanda_ACS
```

Solo funciona con **zona climática D2, 100 m², 100 L/día de ACS y un único equipo eléctrico de efecto Joule al 100 %**, sin acumulación ni otras instalaciones o contribuciones. **Fuera de ese supuesto, no ofrece adaptar**: permite omitir la instalación con consentimiento cuando es seguro, o bloquea. Se pierden la distribución mensual y la potencia. [Ensayo completo](docs/VALIDACION_SOLAR.md).

**Criterios pendientes, NO implementados:**

- **Persianas:** usar los factores estacionales de 3.2 como valores de **Otros** en 2.3 es una posibilidad, pero el factor CTE no coincide. [Prueba realizada](docs/EQUIVALENCIAS_Y_LIMITES.md#persianas-de-huecos).
- **Fotovoltaica mensual:** `E_anual = suma del autoconsumo mensual computable`, **no** de toda la producción. Falta validar el tratamiento de servicios y excedentes.
- **Recuperación de calor:** sin equivalencia energética y eléctrica suficientemente contrastada.

[Detalle de equivalencias](docs/EQUIVALENCIAS_Y_LIMITES.md) · [Matriz completa de compatibilidad](docs/MATRIZ_COMPATIBILIDAD.md)

## ¿Está probado?

La **v1.5.3** superó apertura, recálculo, guardado y exportación XML de **seis salidas** en CE3X 2.3, incluidas mejoras y omisiones. Es una herramienta **experimental**, no garantiza compatibilidad universal ni sustituye la revisión del técnico.

[Ver pruebas y resultados](docs/INFORME_VALIDACION_FINAL.md) · [Historial de versiones](CHANGELOG.md)

## Si falla

Pulsa **Guardar diagnóstico** y adjúntalo a una [incidencia en GitHub](https://github.com/xSeeSx/Conversor-CE3X-3.2-a-CE3X-2.3/issues), indicando qué ocurrió. **Revisa el ZIP antes de compartirlo**: puede contener datos del certificado.

[Documentación de desarrollo](docs/DESARROLLO.md)
