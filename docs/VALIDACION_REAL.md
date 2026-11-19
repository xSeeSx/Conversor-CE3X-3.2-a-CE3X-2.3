# Banco de pruebas local de CE3X

## Repetir un ensayo

En Windows, desde la raíz del repositorio, ejecuta `./scripts/validar_ce3x_local.ps1 -Modo Ayuda`. El banco usa Python 3.11 o posterior y permite comprobar las rutas instaladas con `-Modo Entorno`. El comando de pruebas ejecuta la regresión sin abrir CE3X.

```powershell
./scripts/validar_ce3x_local.ps1 -Modo Pruebas
./scripts/validar_ce3x_local.ps1 -Modo Preparar -Carpeta 'C:\CE3X-pruebas\ensayo-01' -Origen32 'C:\CE3X-pruebas\modelo32.cex'
```

Para comparar contra un proyecto equivalente creado de forma nativa en 2.3, añade `-Nativo23 <ruta>`. Si la conversión requiere consentimiento, revisa el plan y repite con `-Modo Aceptar -Carpeta <ruta> -Consentimiento <token>`. El banco conserva las entradas y sus hashes. Los proyectos reales deben usar una carpeta fuera del repositorio. Para muestras públicas o sintéticas se permite `-MuestraPublica`.

En cada versión abre la copia indicada por `-Modo Estado`. Pulsa **Calificar**, guarda el CEX y exporta el XML con el mismo nombre base junto a la copia. Después ejecuta `-Modo Recoger -Carpeta <ruta>`. Puedes hacerlo tras cada exportación. El estado señala los pasos pendientes y la recogida escribe `resumen.json` e `indicadores.csv`.

El resumen registra hashes, medidas de envolvente, referencias, equipos comunes y los indicadores que reconoce en el XML. Comprueba la cabecera esperada de cada CEX. La comparación exige la misma magnitud, servicio y unidad. Si aportas una referencia nativa 2.3, calcula por separado la comparación 3.2–2.3 nativos y la comparación convertido–nativo 2.3. El porcentaje queda vacío cuando la referencia vale cero.

## Ensayo ejecutado en Windows

Se comprobó la instalación de CE3X 2.3 y 3.2. Se preparó la muestra oficial **2 Vivienda dentro de bloque** incluida con CE3X 3.2. El origen docente se identifica por el SHA256 `b57a58f3e639757e6b8576f895cc3f6cfc8abd8952cf3ce22c7238df1da54dba`. La conversión exigió consentimiento para 170 entradas inventariadas y conservó cuatro cerramientos, siete huecos, 17 puentes, dos patrones de sombra y tres conjuntos de mejora. Se preservaron el CEX oficial y la primera salida convertida.

| Prueba | Resultado observado |
| --- | --- |
| Apertura y guardado en CE3X 3.2 y 2.3 | El usuario abrió la copia de origen en 3.2 y la convertida en 2.3. El banco verificó ambas cabeceras y el cambio de hash de las dos copias guardadas. |
| Recálculo y exportación en ambas aplicaciones | El usuario generó ambos XML. El banco leyó 109 entradas de indicadores y calificación en 3.2, incluidas mejoras, y 22 en 2.3. |
| Conservación al guardar | La geometría, transmitancias de cerramientos, datos de huecos, ψ y longitudes de puentes, referencias, equipos y recuentos de mejoras del resumen coinciden con la copia inicial de cada versión. |
| Nativo 2.3 equivalente | Pendiente. Los datos del convertido documentan que funciona este caso, con independencia de una futura comparación energética contra el nativo. |

| Indicador | Nativo 3.2 | Convertido en 2.3 | Δ |
| --- | ---: | ---: | ---: |
| Demanda de calefacción, kWh/m²·año | 118,25 | 118,25 | 0,00 |
| Demanda de refrigeración, kWh/m²·año | 0,83 | 0,83 | 0,00 |
| Demanda de ACS, kWh/m²·año | 23,81 | 23,81 | 0,00 |
| Energía primaria no renovable, kWh/m²·año | 189,21 | 189,22 | +0,01 |
| Emisiones, kgCO₂/m²·año | 40,03 | 40,04 | +0,01 |
| Compacidad, m | 4,46 | 4,46 | 0,00 |
| Calificación global de energía y emisiones | E | E | Coincide |

La diferencia observada combina el cambio de motor y la conversión. Hace falta el modelo equivalente creado y calculado en 2.3 para atribuirla. El SHA256 del XML 3.2 es `1b004b9ad7f7e5f5d5cbfa531dfb009aca4518ebbaaa1ab9aae45c3c3927cb57` y el del XML 2.3 es `03b8c850f2338f2b3830468fb1b6c6878803b245e00d93a0fa616bfdf824f01a`.

La exportación XML de 2.3 ensayada contiene indicadores del edificio. El recálculo individual de mejoras, el análisis económico y la generación de PDF quedan pendientes. Quedan por ejecutar también la apertura y el recálculo de archivos con omisión termosolar, protecciones nuevas y otras combinaciones de la [matriz](MATRIZ_COMPATIBILIDAD.md). Los CEX y XML completos permanecen locales.
