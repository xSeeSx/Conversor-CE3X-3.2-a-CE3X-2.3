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
| Solar térmica **mensual** | Usa zona y litros del CEX. Adaptación experimental en mejoras que combinan envolvente conocida y ACS compatible |
| Persianas nuevas | Opción experimental **Otros** para persianas manuales aisladas de cualquier color con factores válidos |
| Autoconsumo eléctrico **mensual** | Opción experimental de aportación anual para series EPB reconocidas, sin mejoras asociadas |
| Depósitos de ACS | Conserva todos los campos nativos, incluidos vacíos, UA, método y multiplicador |
| Aire primario, recuperadores y ventiladores | Bloqueados en residencial por falta de un campo equivalente en 2.3 |

**Nunca se eliminan datos activos sin avisar.** El programa detalla las pérdidas y pide confirmación, con **Cancelar** como opción inicial. Si no puede convertir u omitir algo con seguridad, se detiene.

## Criterios y fórmulas de adaptación

Los campos comunes se conservan aunque estén vacíos o sean incoherentes: se avisa sin rellenarlos ni cancelar. Las validaciones físicas estrictas se reservan para los cálculos de adaptación de elementos nuevos de 3.2.
Las opciones experimentales se identifican antes de convertir y requieren consentimiento y recálculo.
El aviso experimental recomienda comparar ambos certificados y permite consultar el inventario completo en **Ver detalles**.

```text
Demanda_ACS (kWh/año) = 360 × 4,18 × litros_ACS_día × (60 − T_red_zona) / 3600
Cobertura_ACS_2.3 (%) = 100 × suma(producción mensual) / Demanda_ACS
```

La termosolar admite un equipo eléctrico de efecto Joule conocido al 100 %, sin acumulación ni otras aportaciones. **Otros** conserva los factores estacionales de las persianas manuales aisladas y lleva el factor CTE a 1. El autoconsumo anual se calcula sumando los doce valores EPB declarados. La adaptación pierde el reparto mensual.

[Detalle de equivalencias](docs/EQUIVALENCIAS_Y_LIMITES.md) · [Matriz completa de compatibilidad](docs/MATRIZ_COMPATIBILIDAD.md)

## ¿Está probado?

La **v1.6.0** superó las pruebas automáticas y la integración Windows. Se han comprobado en CE3X 2.3 la apertura, el recálculo, el guardado y la exportación XML de casos residenciales, incluidos ACS solar, persianas y mejoras. El autoconsumo mensual también se contrastó entre ambos motores en los ensayos documentados. Las opciones **experimentales** requieren revisar los resultados y no garantizan equivalencia universal.

[Pruebas residenciales](docs/INFORME_VALIDACION_FINAL.md) · [Equivalencias y límites](docs/EQUIVALENCIAS_Y_LIMITES.md) · [Historial](CHANGELOG.md)

## Si falla

Pulsa **Guardar diagnóstico** y adjúntalo a una [incidencia en GitHub](https://github.com/xSeeSx/Conversor-CE3X-3.2-a-CE3X-2.3/issues), indicando qué ocurrió. **Revisa el ZIP antes de compartirlo**: puede contener datos del certificado.

[Documentación de desarrollo](docs/DESARROLLO.md)
