# Hoja de ruta — 20/11/2026

Prioridades revisables según datos reales. No ejecutar todas a la vez.

1. Operación estable: verificar la inicialización del P0 de continuidad en ambos flujos tras integrar con autorización y seguir el [manual](MANUAL_OPERATIVO.md#verificación-tras-la-integración). Comprobar último despliegue, errores por fuente y pérdidas de cobertura; estudiar alertas tras fallos, comparar candidatas por fuente y recuperación temporal. Mantener CI y controles de publicación.
2. Revisión RSS: reducir trabajo manual con informes diarios de candidatos, comprobar edición, fecha, lugar, duplicados y procedencia; pedir autorización agrupada antes de incorporar candidatos. No convertir títulos de Google en carreras publicadas. Evaluar tasa de falsos positivos y nuevas ediciones que reutilizan URL.
3. Calidad: usar inventario de distancias pendientes, priorizar carreras próximas (30/90 días), completar horarios/plazos documentados. Mantener distancias aproximadas y orientativas diferenciadas.
4. Cobertura territorial: revisar provincias con menos pruebas y calendarios municipales, sin limitarse al recuento absoluto. Revisar periódicamente Jaén, Huelva, Almería, Córdoba y Sevilla. Identificar fuentes autorizadas y alternativas editoriales.
5. Experiencia de usuario: mejoras basadas en necesidades reales, filtros funcionales, rendimiento móvil, accesibilidad; no rediseñar portada sin petición.
6. Legal y privacidad: revisar condiciones, licencias, permisos y obligaciones de lanzamiento; no activar fuentes pausadas, indexación ni monetización sin decisión del responsable.
7. Organización: usar ChatGPT Projects para dirección y consultas, Codex para desarrollo con AGENTS.md, GitHub como memoria verificable, tareas recurrentes para supervisión. Evitar duplicar automatizaciones de GitHub.

Protección de lecturas silenciosas (P1): comparar la salida directa de cada lector con referencias recientes del despliegue confirmado y diagnosticar anomalías. Revisar en un PR los umbrales para evitar falsas alarmas; tras validar la primera ejecución, estudiar avisos de fallo de Actions sin ampliar permisos automáticamente.

Control de cancelaciones editoriales (P1): mantener los vetos expresos por edición frente a las entradas automáticas y los respaldos, sin deducir cancelaciones ni vetar otras fechas. Cada cambio en estas reglas necesita regresiones, CI y autorización antes de integrarlo.

Criterio de completitud: objetivo acotado, pruebas, PR/commit, resultado del despliegue si corresponde, documentación actualizada, limitaciones y siguiente prioridad.
