# Validación 1.5.1

## Formatos de cerramientos

Se ejecutó `cogerDatos` de los diez paneles originales de CE3X 2.3 con su Python 2.7 y sus módulos compilados oficiales. Se simularon únicamente los controles gráficos y la comprobación de entradas para inspeccionar los registros; no se abrió la aplicación ni se evaluaron resultados energéticos. Las longitudes observadas se guardan en `fuentes/fixtures/envolvente_nativa_23.json` y una prueba exige que el catálogo coincida exactamente.

La cubierta enterrada devuelve 16 campos. El dato adicional de espesor no se elimina ni se reinterpreta. Las otras tipologías devuelven 13, 15 o 17 campos según el caso.

Las particiones verticales e inferiores y la clase de zonas se contrastaron además con el ejemplo oficial 5 de CE3X 2.3. El inventario de ejemplos oficiales 3.2 confirma la misma clase de zona y los mismos cuatro nombres de campos.

## Pruebas del producto

91 pruebas de regresión del motor: conservación de las diez tipologías; zonas anidadas y zonas dentro de mejoras; estructuras desconocidas; decisiones y cancelación; factores solares; conservación de campos y del original. El flujo ejecuta las pruebas con Python instalado y portátil y prueba el ejecutable de Windows y sus decisiones. También conserva la regresión con los ejemplos oficiales 3.2.

## Diagnóstico privado

El ZIP no contiene el .cex original completo. Se reconstruyó exclusivamente su modelo técnico para reproducir los fallos, sin datos administrativos, fotos ni planos. Después de aceptar expresamente la omisión de la protección solar nueva, se genera una salida estructural con sus seis cerramientos, ocho huecos y dos puentes, conservando los cerramientos y puentes. No se publica esa reconstrucción ni el diagnóstico.

La omisión está limitada a huecos sin otras protecciones ni patrones de sombra y sin medidas de mejora. Restablece los factores solares a 1 y conserva ventanas y puentes. Las demás combinaciones siguen rechazándose, sin pérdida silenciosa de datos. La salida requiere apertura, revisión y recálculo en CE3X 2.3.
