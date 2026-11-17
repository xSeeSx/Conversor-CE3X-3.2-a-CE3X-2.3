# Validación de la versión 1.4.1

## Muestras utilizadas

Ejemplos docentes incluidos en el paquete oficial CE3X 3.2 del MITECO, enlazado por Efinovatic:

- Página del desarrollador: https://efinova.es/CE3X
- Paquete: https://www.miteco.gob.es/content/dam/miteco/es/energia/eficiencia/certificacionenergetica/documentosreconocidos/procedimientoscertificacion/ce3x/CE3Xv3.2.zip
- SHA256 del ZIP: `d92bea9f25ebd60c30ef9043ffdd3339fc84065eb415b2629b8a77f948f6b9dd`.

Se inspeccionan los archivos mediante el lector inerte del conversor. El instalador se extrae y no se ejecuta. Las duplicaciones de ejemplos dentro del instalador tienen el mismo hash.

| Ejemplo residencial 3.2 | Cerramientos | Ventanas | Puentes | Patrones de sombra | Mejoras | Resultado |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Bloque de viviendas, Zaragoza | 6 | 4 | 16 | 0 | 3 | Error explícito por un generador termosolar nuevo sin equivalencia contrastada |
| Vivienda dentro de bloque, Pamplona | 4 | 7 | 17 | 2 | 3 | Conversión y relectura estructural correctas |

SHA256 de los archivos:

- Bloque: `8b4ca4dbb37ec646ee9168f9cebe53905285f9693ae79191509d2a94eb31e0aa`.
- Vivienda con sombras: `b57a58f3e639757e6b8576f895cc3f6cfc8abd8952cf3ce22c7238df1da54dba`.

Los ejemplos de pequeño y gran terciario se identifican y se excluyen de la conversión residencial. Algunos incluidos en este instalador conservan una cabecera 3.1: el nombre del paquete no basta para determinar la versión de cada CEX.

## Contraste nativo 2.3

Se extrajeron los ejemplos residenciales del instalador oficial 2.3:

- URL: https://www6.serviciosmin.gob.es/aplicaciones/calener/setupCE3Xv2.3.exe
- SHA256: `5cb86c17900bb383577bb31f78251f22d722db2f185d16d69b4decfef57ae82c`.
- Los dos archivos declaran `CEXv2.3 Residencial`. Sus hashes se registran en `app/mm_schema_23.json`.

Estos archivos contrastan los campos y clases del formato de destino. Los valores del edificio convertido proceden de su origen 3.2.

Se comprobaron estas diferencias:

1. `correctorSolar` falta en ventanas estimadas válidas de 2.3 y aparece en otras de la misma clase. Es un campo opcional; se conserva cuando existe.
2. Las mejoras de puentes térmicos utilizan una lista de 20 campos, con selecciones booleanas y coeficientes conservados como texto. El formato coincide en ambos ejemplos.
3. El bloque oficial 3.2 tiene 1293,44 m² en el campo general común y 1200 m² en el campo adicional. Exigir igualdad bloqueaba un archivo nativo válido. Se conserva el campo común, se comprueba que el adicional sea numérico no negativo y se registra para revisión.
4. El generador termosolar mensual nuevo de 3.2 no equivale por sí solo a la contribución porcentual de 2.3. Su conversión se rechaza expresamente.

## Comprobaciones de la vivienda con sombras

- Conservación tipada exacta de los bloques de patrones y nombres: polígonos, coeficientes y opciones.
- Conservación de las referencias de sombras en cerramientos y ventanas.
- Conservación de cerramientos, superficies y puentes del origen.
- Conservación de los tres conjuntos de mejora, incluidas sus definiciones de puentes térmicos y los datos económicos.
- Escritura y relectura de los 15 bloques de salida.
- Los registros solo se exportan al solicitar un diagnóstico.

La regresión automatizada exige que esta vivienda convierta y conserve sus patrones; un error de conversión hace fallar la comprobación. También exige el error explícito del bloque con el generador no soportado.

## Límites

Estas comprobaciones son estructurales. La apertura, edición y el recálculo en CE3X 2.3 requieren validación manual. Los valores energéticos guardados proceden del origen 3.2. Las diferencias entre los ejemplos 2.3 y 3.2 no deben confundirse con diferencias introducidas por el conversor.

Los ejemplos completos se obtienen del distribuidor oficial para las pruebas. El paquete público del conversor contiene únicamente su plantilla estructural neutral. La pequeña fixture de sombras conserva solo datos geométricos y coeficientes de un ejemplo docente, con su referencia y hash.
