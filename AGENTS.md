# Instrucciones para Codex y otros agentes de desarrollo

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
