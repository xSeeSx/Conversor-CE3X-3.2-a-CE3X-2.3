# Adaptación de solar térmica mensual, versión 1.5.0

## Evidencia

Ensayos introducidos y recalculados por el usuario en CE3X 2.3 y 3.2. Se inspeccionaron los CEX con lector inerte y los XML exportados, sin ejecutar sus objetos serializados. Los proyectos completos y sus imágenes no se incorporan al repositorio ni al ZIP público. Las pruebas automáticas usan modelos sintéticos sin datos personales.

Modelo común: residencial, zona D2, 100 m², demanda de ACS 100 litros/día a 60 °C, un equipo de efecto Joule eléctrico conocido con rendimiento 100 %, cobertura 100 % y sin acumulación. Sin otras contribuciones.

El manual de fundamentos técnicos de enero de 2015, incluido en el instalador oficial 2.3, apartado 3, página impresa 14, utiliza 360 días y TAF=11,7 °C para D2. Instalador histórico: https://www6.serviciosmin.gob.es/aplicaciones/calener/setupCE3Xv2.3.exe (SHA256 5cb86c17900bb383577bb31f78251f22d722db2f185d16d69b4decfef57ae82c).

Demanda anual sin acumulación:

`D = 360 * 4.18 * Q_litros_dia * (60 - 11.7) / 3600`

Para el ensayo, D=2018,94 kWh/año. La cobertura candidata es `100 * suma_producciones_mensuales / D`. No se utiliza el campo de cobertura mostrado en las tablas del XML 3.2.

| Caso | Cobertura 2.3 | Producción 3.2, kWh/año | Consumo final ACS, kWh/m²·año |
| --- | ---: | ---: | ---: |
| Meses de 10 a 21 kWh | 9,21276 % | 186 | 18,33 en ambas versiones |
| Doce meses de 15,5 kWh | 9,21276 % | 186 | 18,33 en ambas versiones |
| Doce meses de 117,7715 kWh | 70 % | 1413,258 | 6,06 en ambas versiones |
| Toda la producción en julio | 70 % | 1413,258 | 6,06 en ambas versiones |
| Solar dentro de mejora independiente | 70 % | 1413,258 | 6,05682 en los resultados internos de ambas versiones |

En la mejora, el consumo de ACS pasa de 20,1894 a 6,05682 kWh/m²·año. Calefacción y refrigeración mantienen sus consumos. Se comprobaron tanto la definición como las copias internas de instalaciones y el XML 3.2 del conjunto.

El XML 3.2 de la prueba concentrada conserva la producción de julio en DatosBalance/Componentes. Los indicadores anuales coinciden con los del reparto uniforme. Esto describe el comportamiento de CE3X en este ensayo, no demuestra almacenamiento físico entre meses ni validez universal de un balance anual.

Se observaron valores de CoberturaDemandaAcs=8 o 64 en tablas 3.2 que no coinciden con el porcentaje equivalente de la prueba. No se ha resuelto el significado de esa discrepancia y no se usa para adaptar.

## Decisión previa

Sin una decisión no se escribe salida. Cada generador declarado solicita adaptar, omitir lo indicado o cancelar. La selección se vincula al SHA256 del origen; si cambia, el proceso se detiene. La opción por defecto del diálogo es Cancelar.

Adaptar conserva nombre identificable y producción anual mediante una contribución porcentual 2.3; pierde reparto mensual, potencia solar e identificador de 3.2. No recalcula resultados energéticos.

Omitir una instalación base elimina esa solar. Omitir solar de una mejora elimina TODO el conjunto, con sus otras actuaciones, costes y selecciones de informe. El aviso lo explica antes de aceptar. No se presenta una mejora vacía como si conservara el ahorro solar. El resto de los conjuntos se mantiene.

Las decisiones y el recordatorio de recalcular aparecen al finalizar. El diagnóstico incluye el detalle solo cuando el usuario lo exporta. No se generan registros automáticamente.

## Alcance conservador

Solo se ofrece adaptar con un generador, zona Edificio Objeto, D2, ACS eléctrico conocido de efecto Joule al 100 % de rendimiento y cobertura, sin acumulación ni contribuciones adicionales, sin campos solares desconocidos y con producción positiva no superior a la demanda anual. No se ofrece en mejoras combinadas con cambios de envolvente ni para solar base combinada con mejoras.

Los casos fuera de alcance permiten omitir o cancelar cuando su estructura se reconoce. Los formatos desconocidos siguen detenidos. No hay adaptación automática para otras zonas climáticas, múltiples generadores, bombas de calor, acumulación, otros servicios, fotovoltaica mensual o producciones mayores que la demanda anual.

La apertura, edición y el recálculo del CEX convertido en CE3X 2.3 siguen requiriendo comprobación manual. Los ensayos anteriores comparan proyectos nativos introducidos en ambas versiones; no se atribuye al motor de conversión una validación de apertura que todavía no se ha realizado.
