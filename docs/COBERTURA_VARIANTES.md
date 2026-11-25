# Cobertura real de variantes y equivalencias CE3X 3.2 → 2.3

Documento técnico de control de compatibilidad. **Una funcionalidad que funciona en un ejemplo NO está adaptada universalmente.** Separar siempre: (1) formato CEX 2.3 válido, (2) datos transferidos o simplificados, (3) equivalencia energética contrastada y (4) condiciones de aplicación.

## Regla de clasificación obligatoria

Para cada **subtipo y combinación de parámetros relevantes**, registrar un estado exclusivo:

- **CONSERVACIÓN**: datos transferidos sin transformación relevante, con estructura reconocida; no implica que ambos motores calculen idéntico.
- **ADAPTACIÓN CONTRASTADA [ámbito explícito]**: transformación aplicada y probada frente a un modelo nativo 2.3 y referencia 3.2, con magnitudes y tolerancias documentadas.
- **ADAPTACIÓN EXPERIMENTAL [ámbito explícito]**: representación 2.3 estructuralmente válida y cálculo plausible, sin equivalencia energética completa demostrada. Solo con consentimiento expreso, detalle de pérdidas y recálculo/comparación posterior.
- **OMISIÓN CONSENTIDA [ámbito explícito]**: se pierde un elemento o su efecto, y se retiran correctamente todas las dependencias; **nunca** llamarlo adaptación.
- **BLOQUEADO [motivo específico]**: combinación desconocida, relación incoherente o no existe representación segura; no generar salida.

**Prohibido usar "adaptado", "compatible", "resuelto" o ✅ sin cualificar el subconjunto que de verdad funciona.** Tener los campos serializados **no prueba** que incorporen todos los efectos del color, control, sombras o funcionamiento. Investigar dónde calcula cada motor esos efectos. No asumir que todos los campos `correctorFS*` son actualizados o utilizados igual.

## Ficha por funcionalidad (actualizar en cada PR)

En `docs/MATRIZ_COMPATIBILIDAD.md` y, si conviene, aquí, cada conversión necesita:

1. **Parámetros y variantes**: enumeraciones reales extraídas del programa 3.2 o de archivos nativos; no inventar posibilidades. Identificar cuáles intervienen en el cálculo energético, en controles o solo en descripción.
2. **Correspondencia 2.3**: campo o mecanismo destino y diferencias físicas/semánticas, incluidas unidades, redondeo, signo y servicios computables.
3. **Ámbito admitido**: condiciones expresadas como reglas explícitas del código, no como nombre genérico del elemento.
4. **Ámbito no cubierto**: opciones válidas de 3.2 todavía no adaptadas, bloqueos y sus causas exactas.
5. **Evidencia**: pruebas unitarias, archivos nativos recalculados, XML comparables, tolerancias y datos perdidos.
6. **Consentimiento/diagnóstico**: identificar **qué hueco o instalación** y **qué opción exacta** convierte o descarta.
7. **Cobertura al nivel de opciones**: recuento por subtipo o combinación comprobada, sin porcentajes inventados sobre un universo desconocido.

**Jerarquía de evidencia y coste:** reutilizar ensayos ya documentados y consultar manuales oficiales y fórmulas/tablas nativas antes de ejecutar pruebas nuevas. Si la correspondencia está documentalmente definida y la estructura de salida es conocida, bastan pruebas automáticas de la regla y el control de compatibilidad correspondiente. Reservar ensayos nativos dirigidos para ambigüedades de interpretación o impactos energéticos no demostrados; no eximir de comprobar que el archivo abre y recalcula cuando cambie la estructura o la semántica del destino. No presentar un cálculo físico documentado como equivalencia CE3X 3.2/2.3 sin comprobar que ambos motores lo utilizan de la misma manera.

**Validar el algoritmo, no cada valor:** primero extraer de CE3X la ecuación, tabla o regla que cubre la familia y trasladarla a una función parametrizada. Probar todas las ramas **distintas por su funcionamiento** y los límites, pero no construir un certificado nativo por cada color, zona climática, caudal o superficie. Usar unit tests parametrizados, clases de equivalencia, límites numéricos y combinaciones representativas de interacciones (pairwise). Reservar ensayos nativos 3.2/2.3 para unas pocas configuraciones que contrasten **cada regla física/algorítmica diferenciada** y las interacciones de alto riesgo. La cobertura es el **dominio matemático demostrado** y las estructuras destino admitidas, no una lista de ejemplos exitosos. No inferir igualdad física únicamente porque dos exportaciones coincidan.

## Inventario inicial sobre la v1.5.4

| Familia | Cobertura que existe | Variantes aún no justificadas como adaptadas |
| --- | --- | --- |
| Persianas nuevas | Opción **experimental** `Otros` para **manual + blanco + ventana aislada**, con correctores invierno/verano válidos. Factor CTE no conservado. | Otros colores, modos automáticos, combinaciones con voladizo/cajón/sombras, mejoras, varias protecciones simultáneas. Analizar si el color ya está representado **por completo** en los factores y si estos son actuales; no suponerlo sin pruebas. |
| Solar térmica mensual | ACS con generador único, zona conocida, volumen diario del CEX, equipo eléctrico conocido efecto Joule 100 %, sin acumulación ni otras contribuciones. Contrastes nativos D1 y D2; otros casos admitidos **experimentales**. | Diferentes sistemas ACS, varias coberturas/equipos, acumuladores, otros servicios, mejoras simultáneas y condiciones territoriales especiales; no calificarlos como resueltos. |
| Fotovoltaica anual nativa | Se conserva una contribución anual compatible. | Generación/autoconsumo **mensual** de 3.2, excedentes y otras combinaciones: bloqueo actual. |
| Ventilación, recuperadores, ventiladores | Grupos vacíos reconocidos. | Grupos activos sin equivalencia contrastada: bloqueo; distinguir caudal, recuperación térmica y electricidad auxiliar. |
| Mejoras con elementos nuevos | Determinadas mejoras comunes, equipos y costes se conservan. | Mejoras con dependencias o generadores 3.2 nuevos, combinaciones con protecciones y solar que no se pueden trasladar íntegramente. |
| Acumulación y componentes nuevos | Datos comunes en estructuras conocidas. | Métodos de cálculo del depósito, tipos estimados, varios depósitos y estructuras desconocidas. |

Esta tabla es **inventario parcial**, no una lista completa de todas las opciones de interfaz 3.2. Se deben explorar las opciones reales y añadir las variantes descubiertas por categoría.

## Ampliaciones sobre la v1.5.4

| Variante | Estado y dominio |
| --- | --- |
| Persianas manuales aisladas | **Experimental** para cualquier color informado y correctores guardados en [0,1]. «Otros» recibe los de invierno y verano. Se pierde el tipo, el color y el CTE original. La regla de destino coincide con la usada en el ensayo nativo de la persiana blanca. |
| Automatismos, persianas con otras sombras o integradas en mejoras | Automatismo aislado de forma reconocida admite **omisión consentida**. El control horario de 3.2 y los dispositivos combinados carecen de correspondencia contrastada. Los casos combinados se bloquean. |
| Autoconsumo mensual renovable | **Experimental** para la serie nativa EPB de doce meses no negativos y sin mejoras. Si existe balance calculado, debe coincidir. Se pierde la serie, potencia e identificador. Producción total, excedentes y series con estructura diferente quedan fuera. |
| Aire primario, recuperadores y ventiladores | **Bloqueado** en residencial. El manual sitúa los paneles correspondientes en terciario. La tasa de renovación no puede representar el equipo ni su consumo auxiliar. |
| Mejora de envolvente y solar de ACS | **Experimental** con equipo de ACS admitido, zona, caudal y superficie invariantes, definiciones coherentes y copias reconocidas. Se conservan actuaciones, costes y referencias. |
| Depósitos de ACS | **Conservación** para UA conocido, por defecto y estimado por aislamiento, incluido el multiplicador y con su estructura nativa. Los campos vacíos o incoherentes se conservan con aviso (1.6.1), sin completar desde el edificio base. Métodos desconocidos bloquean. La adaptación termosolar con depósitos sigue fuera de alcance. |

[Fuentes y detalle de los ensayos](EQUIVALENCIAS_Y_LIMITES.md)

## Comportamiento esperado del conversor

- Clasificar **cada elemento afectado** por su configuración concreta, no declarar válido todo un tipo porque una variante superó el ensayo.
- Permitir adaptar con consentimiento experimental cuando exista una representación 2.3 técnicamente válida y la incertidumbre se explique; nunca forzar una equivalencia con energía inventada.
- Si un archivo contiene un elemento compatible y otro no, **identificar ambos por separado**. Evitar que una decisión global enmascare pérdidas de uno de ellos.
- Cuando se detecten opciones nuevas de 3.2, comprobarlas contra la matriz y **no transformarlas automáticamente** como si fueran del caso ya probado.
- Conservar siempre la posibilidad de cancelar sin modificar el origen, y recalcular/contrastar los resultados convertidos en CE3X 2.3.

## Definición de terminado para una familia

1. Inventariados los subtipos/opciones que soporta el programa y las interacciones importantes, con fuente de evidencia.
2. Documentados por opción los estados y límites anteriores; sin dar por compatibles variantes no ensayadas.
3. Pruebas positivas, negativas y de límites para **cada rama algorítmica soportada**, sin exigir un certificado por valor continuo o color equivalente.
4. Comprobada apertura, recálculo, guardado y XML en CE3X 2.3 para cada equivalencia física nueva representativa.
5. README solo comunica el ámbito real en una frase; el detalle vive en esta matriz y en `docs/EQUIVALENCIAS_Y_LIMITES.md`.

**Implementa y valida fórmulas o tablas generalizables en el código, no listas de excepciones basadas en ejemplos.** **No bloquees por una condición arbitraria copiada del único ejemplo**, como `color=="Blanco"` o `zona=="D2"`, **si la equivalencia es independiente de ella**. Pero **no elimines esa condición** hasta revisar de dónde salen los parámetros efectivos y probar la hipótesis. Si el dato simplemente no existe en 2.3, documentar la pérdida y cuál es el sustituto aceptado.
