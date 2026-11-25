# Inventario de omisiones de CE3X 1.5.2

Se prepara y valida un destino en memoria antes de escribir el CEX. El plan recoge las transformaciones y, para cada retirada, el campo, el elemento, la cantidad, el motivo, el impacto y las dependencias. Si hay pérdidas de datos activos o información del usuario, el conversor pide consentimiento. El diagnóstico exportado bajo petición también conserva las retiradas de formato y las cachés.

| Familia | Comportamiento |
| --- | --- |
| Datos administrativos y generales | Los campos adicionales de las posiciones conocidas se muestran si tienen contenido. Se conserva la superficie común del campo general 6. Una estructura inesperada bloquea. |
| Huecos y sombras | Se retira el UUID interno y los campos nuevos vacíos. Puede omitirse la protección nueva aislada en los huecos identificados, restableciendo los factores a 1. Las combinaciones con sombras o mejoras, los campos de hueco desconocidos y las referencias inválidas bloquean. |
| Instalaciones y acumulación | Los dos grupos nuevos vacíos se retiran como ajuste de formato. El final de tres campos escalares de un equipo y el agregado escalar del depósito de siete campos requieren consentimiento cuando contienen datos. Se conservan la cobertura, los rendimientos y el UA común. Los grupos activos nuevos y las formas de descarte desconocidas bloquean. |
| Termosolar mensual | Se permite la adaptación documentada de ACS o la omisión de un generador de forma conocida. En una mejora, la omisión retira el conjunto entero, las filas de coste asociadas y sus selecciones del informe. Referencias adicionales, copias discordantes y solar del edificio combinado con mejoras bloquean. |
| Mejoras | Los metadatos `ordenPrioridad`, `seRecomienda` y `justificacion`, los datos auxiliares contrastados en las muestras y las bibliotecas nuevas de sus modelos calculados requieren consentimiento si contienen información. Se conservan el orden, las mejoras y sus costes. Los campos, clases y definiciones sin regla segura bloquean. |
| Análisis económico e informe | Se mantienen los valores comunes. Se permite retirar el octavo campo vacío del informe. Si está activo o cambia la estructura esperada, la conversión se detiene. |
| Complementos | Desde 1.6.1 se conserva el bloque común, tanto texto como datos compuestos, sin reinicio ni omisión. Las clases exclusivas sin correspondencia siguen bloqueadas. |
| Cachés y bloques internos | Los resultados mensuales reconocidos de las mejoras y sus cachés se auditan para recálculo. En el bloque reservado 14 solo se acepta la forma observada de un token de 32 bytes en Base64. Se registra la sustitución por el token de la plantilla. Otros cambios de forma en los bloques reservados bloquean. |

La interfaz muestra el inventario de cada opción y vuelve a contrastarlo con las entradas al confirmar. La salida con pérdidas usa el estado `CONVERSION_CON_OMISIONES`. El original se conserva. No se crea automáticamente un diagnóstico.

Esta tabla cubre las rutas de descarte revisadas. El catálogo de estructuras residenciales 3.2 y la validación energética en CE3X 2.3 siguen abiertos. Para el único cálculo solar habilitado, consulta [Validación solar](VALIDACION_SOLAR.md).
