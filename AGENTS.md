# Instrucciones para Codex y otros agentes de desarrollo

## Fórmulas y límites ya investigados

Antes de investigar las equivalencias P0-P3, lee [docs/FORMULAS_EQUIVALENCIAS_PENDIENTES.md](docs/FORMULAS_EQUIVALENCIAS_PENDIENTES.md). Contiene ecuaciones, unidades, contraejemplos y pruebas de recuperadores, ventiladores, generación eléctrica mensual, persianas y solar térmica. **Reutilizar y contrastar** en los ejecutables nativos, sin gastar una sesión repitiendo derivaciones físicas. Las fórmulas candidatas no son adaptaciones activas.

## Próxima prioridad de implementación

**Estado: v1.5.4 publicada.** P0 (eliminar restricciones D2/100 m²/100 L/día) ya está implementada experimentalmente y contrastada con ensayos D1/D2; no repetirla ni presentarla como pendiente. **Siguiente trabajo: P1**, comenzando por generalizar las persianas manuales aisladas a **cualquier color** si sus factores calculados de invierno/verano son válidos, sin intentar conservar el nombre de color en el campo «Otros» de 2.3, que no lo admite. Mantener aviso del cambio de factor CTE y consentimiento experimental. Después, estudiar persianas automáticas/combinaciones y **generación eléctrica/fotovoltaica mensual**. Proseguir con P2 (ventilación, recuperación, mejoras combinadas) y P3 si hay evidencia suficiente. Leer [el plan actualizado](docs/PLAN_ADAPTACIONES_PENDIENTES.md) y [las fórmulas preparadas](docs/FORMULAS_EQUIVALENCIAS_PENDIENTES.md). **No cerrar la tarea tras documentar bloqueos**: para cada pendiente identificar si puede convertirse, elaborar un ensayo y hacer una implementación segura, o registrar el impedimento técnico verificable. Publicar solo tras pruebas.

## Generalización por fórmula o algoritmo

**No exigir una prueba nativa por cada color, zona, superficie o valor continuo.** Para cada familia, localizar primero en los módulos nativos 3.2/2.3 cómo se calculan sus magnitudes: parámetros de entrada, tablas y reglas discretas, ecuaciones y factores resultantes. Implementar en el conversor una **función general parametrizada** o una traducción exacta de magnitudes calculadas, nunca una lista de constantes obtenidas de uno o dos certificados.

- **Persianas**: determinar si los factores `correctorFSInvierno` y `correctorFSVerano` están calculados y actualizados a partir de tipo, color, control, sombras y zona. Si son una representación completa y válida, trasladarlos a `Otros` sin depender del nombre del color. Si no son fiables, reproducir la fórmula/tabla nativa de 3.2 según las opciones **o** mantener el caso como experimental/bloqueado; no inventar correctores. Documentar la discrepancia de `correctorFSCTE`.
- **Solar térmica, fotovoltaica, ventilación y otras instalaciones**: derivar de datos reales del certificado con ecuaciones y tablas nativas de cada motor cuando proceda. No introducir filtros de «solo D2», «solo 100 m²» o «solo blanco» por proceder de una muestra.
- **Pruebas eficientes**: tests unitarios parametrizados para ramas discretas, entradas válidas e inválidas y límites numéricos; **pocos ensayos nativos representativos por fórmula o rama semánticamente distinta**, más casos de interacciones de alto riesgo. No multiplicar certificados por todas las combinaciones de colores, zonas y caudales.
- La validación física o estructural de la **regla general** permite extenderla a valores del mismo régimen sin ensayar cada valor. Cuando cambie el algoritmo por tipo, automatismo, sombreamiento, mejora o equipo, identificar una rama distinta y comprobarla por separado.
- Si el parámetro almacenado es un **resultado cacheado** del origen, averiguar si CE3X lo recalcula al cambiar las opciones. No tomar un valor obsoleto como verdadero sin comprobación. Ante ambigüedad, solicitar comprobación o limitar la adaptación.
- Mantener diferencias entre **equivalencia validada**, **aproximación experimental**, **omisión consentida** y **bloqueo real**. La extrapolación debe apoyarse en la regla, no en una coincidencia numérica fortuita.

## Cobertura por configuración, no por nombre de elemento

Antes de llamar adaptada a una familia, consulta y actualiza [docs/COBERTURA_VARIANTES.md](docs/COBERTURA_VARIANTES.md). **Un ensayo exitoso no valida todas las configuraciones.** Inventaría cada subtipo y opción real de CE3X 3.2, el campo o alternativa 2.3, las dependencias y el ámbito probado. Clasifica como conservación, adaptación contrastada, experimental, omisión consentida o bloqueo; incluye pruebas positivas/negativas y de interacciones. **No declares terminada una familia** mientras queden variantes no caracterizadas: marca explícitamente su alcance, sin restringir artificialmente a constantes del ejemplo. En cada release, refleja ese alcance con honestidad y brevedad en README.

## Documentación de compatibilidad obligatoria

El README contiene las secciones **Qué funciona y qué falta** y **Criterios y fórmulas de adaptación**. **Mantenlas actualizadas en el mismo cambio de código** cada vez que se añada, cambie, limite o retire una adaptación, omisión o bloqueo de CE3X 3.2 a 2.3. No es una tarea para aplazar al cierre de la sesión.

Para cada funcionalidad nueva o modificada:
1. Actualiza la fila de estado en el README: conservación directa, adaptación contrastada, omisión con consentimiento, bloqueo o pendiente.
2. Resume en el README el criterio o fórmula y su alcance. Documenta fórmula completa, variables, unidades, restricciones, datos perdidos y evidencias en `docs/EQUIVALENCIAS_Y_LIMITES.md`. Si es candidata, indica **no implementada/no validada** y no la habilites.
3. Añade o actualiza evidencia y pruebas en `docs/EQUIVALENCIAS_Y_LIMITES.md`, `docs/MATRIZ_COMPATIBILIDAD.md` y la documentación de ensayos pertinente. Enlaza desde el README, sin duplicar tablas extensas.
4. Comprueba efectos en las medidas de mejora, referencias, costes, factores solares y decisiones de consentimiento. Nunca elimines información activa en silencio ni presentes una omisión como equivalencia.
5. Actualiza pruebas de regresión para los casos admitidos y rechazados. Diferencia la comprobación estructural de la apertura y el recálculo real en CE3X 2.3.
6. Mantén diferenciados los cambios de `main` y las funcionalidades de la última release publicada. No anuncies en el apartado de descarga una versión que no esté publicada y verificada.

## README para personas, no para agentes

- Mantén el README **breve (objetivo: 50-75 líneas)**, con instrucciones claras, tabla de compatibilidad compacta y solo las fórmulas imprescindibles.
- Evita repetir advertencias, justificaciones, detalles de serialización, resultados de ensayos y explicaciones largas. Todo eso va en `docs/`, enlazado desde el README.
- Escribe para técnicos que quieren instalar y convertir un archivo en menos de un minuto: lenguaje directo, sin coletillas genéricas ni tono promocional.
- Cuando añadas una funcionalidad, actualiza la fila y, si procede, una fórmula breve; **no agregues párrafos repetidos** ni hagas crecer indefinidamente el README.

## Trabajo eficiente

- Prioriza Git, terminal local, Python y PowerShell. Evita navegador gráfico para operaciones de GitHub realizables por terminal o conector.
- Ejecuta primero pruebas focalizadas y después las regresiones pertinentes. Deja la compilación completa de Windows y publicación para un hito de entrega.
- Conserva el contexto técnico y las decisiones en el repositorio; no repitas investigación que ya tenga evidencia versionada.
- No incluyas certificados particulares, diagnósticos con datos privados ni registros con información sensible en commits.
- Estas instrucciones son para **futuras sesiones de desarrollo**: no implican actividad autónoma en segundo plano.
