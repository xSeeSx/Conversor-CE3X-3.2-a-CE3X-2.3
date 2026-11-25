# Avisos y actualizaciones (1.6.2)

Los mensajes visibles agrupan por edificio base, mejora y copia del edificio
original o mejorado. Los componentes se identifican con su nombre real, mediante
el contexto de los objetos de origen. Se explica el campo, la acción y la
consecuencia; las copias repetidas comparten descripción. El inventario técnico
completo, con rutas, valores, cantidades y riesgos, se conserva en el diagnóstico.
No se rebajan validaciones ni se cambian las pérdidas que requieren consentimiento.
Los campos adicionales cuyo significado no está contrastado se indican como tales;
no se inventan nombres físicos.

Ejemplo de presentación:

```text
Mejora "Aislar cubierta" / Edificio con la mejora
  - Se omite: Nombre de la solución constructiva en el cálculo guardado.
    Afecta a: Cerramiento "Cubierta de prueba".
    Se conservan los campos comunes del modelo; revisar la mejora y recalcular.
```

La consulta de versiones utiliza `GET /repos/xSeeSx/Conversor-CE3X-3.2-a-CE3X-2.3/releases/latest`
de la [API oficial](https://docs.github.com/en/rest/releases/releases#get-the-latest-release).
Se verifica la versión numérica completa, el estado público y estable y la
existencia del ZIP de Windows terminado. Se ignoran borradores, versiones previas
y releases sin paquete. No se ofrecen versiones anteriores a la instalada.
Solo se envía una solicitud de metadatos pública con un identificador del programa;
no se leen ni envían CEX, rutas de proyectos o diagnósticos.

La interfaz inicia otro proceso de Python con tuberías propias y lo sondea sin
bloquear el hilo de ventana. La red tiene timeout de 4 segundos; la interfaz
cancela su proceso de consulta a los 10 segundos y al cerrar. La conversión y su
último diagnóstico no se reinician. La consulta automática falla en silencio si
no hay conexión; la manual informa del fallo sin impedir convertir. Una versión
nueva se muestra en la cabecera y en el botón de descarga. La búsqueda manual
ofrece abrir la página de esa versión. El URL se forma con el repositorio fijo
y una versión validada; no se ejecuta una URL arbitraria recibida por la red.

Pruebas: red simulada para orden numérico, versiones anteriores, borradores,
pre-releases, paquetes incompletos, timeout, JSON inválido y respuesta demasiado
grande; prueba nativa sin red del aviso, botón y conservación del estado de
conversión. La integración Windows conserva una captura del aviso.
