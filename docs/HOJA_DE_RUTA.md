# Hoja de ruta — 20/11/2026

Prioridades revisables según datos reales. No ejecutar todas a la vez.

## Sprint exprés de beta 21–22/11/2026

**Congelación funcional:** no añadir nuevas fuentes, scraping, automatizaciones ni cambios de diseño. La [auditoría cuantificada y checklist beta](sprint_beta_2026-11-21.md) confirma en el último despliegue 181 fichas, 312 tests y continuidad correcta, pero documenta **51 fichas solo referenciadas a FADMES/Gesconchip/Runnink**, **88 solo a alguna de cinco fuentes con reservas** y P0 legal/privacidad sin resolver. Estas cifras no son carreras que deban retirarse automáticamente. Priorizar decisiones concretas de procedencia, identificación del titular y verificación real del navegador; GO condicionado a revisión documentada. Mantener `noindex` y sin campaña mientras siga pendiente. La beta por enlace ya es públicamente accesible.

## Puerta de lanzamiento (auditoría 21/11/2026)

La [auditoría integral de prelanzamiento](auditoria_prepublicacion_2026-11-21.md) y el [plan P0 de derechos/identificación](revision_p0_derechos_identificacion_2026-11-21.md) recomiendan **NO-GO para indexación o campaña de lanzamiento**, pero sí pruebas controladas con el enlace actual y sin ampliar derechos. Orden recomendado: (P0) análisis del uso factual reiterado por fuente y resolución del aviso legal, revisión de proveedores y cookies; (P1) prueba real Android/accesibilidad, datos prioritarios de próximas carreras, depuración documental del histórico; (P2) SEO e indexación tras autorización expresa y CI. La instantánea del PR #70 tenía 181 carreras y 308 tests. La instantánea más reciente de este sprint está en la auditoría enlazada; las cifras no sustituyen la siguiente ejecución ni la validación externa de la web.

1. Operación estable: verificar la inicialización del P0 de continuidad en ambos flujos tras integrar con autorización y seguir el [manual](MANUAL_OPERATIVO.md#verificación-tras-la-integración). Comprobar último despliegue, errores por fuente y pérdidas de cobertura; estudiar alertas tras fallos, comparar candidatas por fuente y recuperación temporal. Mantener CI y controles de publicación.
2. Revisión RSS: reducir trabajo manual con informes diarios de candidatos, comprobar edición, fecha, lugar, duplicados y procedencia; pedir autorización agrupada antes de incorporar candidatos. No convertir títulos de Google en carreras publicadas. Evaluar tasa de falsos positivos y nuevas ediciones que reutilizan URL.
3. Calidad: usar inventario de distancias pendientes, priorizar carreras próximas (30/90 días), completar horarios/plazos documentados. Mantener distancias aproximadas y orientativas diferenciadas.
4. Cobertura territorial: revisar provincias con menos pruebas y calendarios municipales, sin limitarse al recuento absoluto. Revisar periódicamente Jaén, Huelva, Almería, Córdoba y Sevilla. Identificar fuentes autorizadas y alternativas editoriales.
5. Experiencia de usuario: mejoras basadas en necesidades reales, filtros funcionales, rendimiento móvil, accesibilidad; no rediseñar portada sin petición.
6. Legal y privacidad: revisar condiciones, licencias, permisos y obligaciones de lanzamiento; no activar fuentes pausadas, indexación ni monetización sin decisión del responsable.
7. Organización: usar ChatGPT Projects para dirección y consultas, Codex para desarrollo con AGENTS.md, GitHub como memoria verificable, tareas recurrentes para supervisión. Evitar duplicar automatizaciones de GitHub.

Diagnóstico de Cruzando la Meta (P1, propuesta): investigar los 18 enlaces/0 fichas de la publicación 44827418106. Corregir extracción de localidades solo con evidencia estructurada, contabilizar motivos de rechazo sin datos de la fuente y validar con CI. No integrar hasta autorización; después comprobar producción y ausencias de duplicados.

Protección de lecturas silenciosas (P1): comparar la salida directa de cada lector con referencias recientes del despliegue confirmado y diagnosticar anomalías. Revisar en un PR los umbrales para evitar falsas alarmas; tras validar la primera ejecución, estudiar avisos de fallo de Actions sin ampliar permisos automáticamente.

Control de cancelaciones editoriales (P1): mantener los vetos expresos por edición frente a las entradas automáticas y los respaldos, sin deducir cancelaciones ni vetar otras fechas. Cada cambio en estas reglas necesita regresiones, CI y autorización antes de integrarlo.

Revisión editorial de la incidencia #68: distinguir cancelación del 15/11/2026 y edición anunciada del 07/02/2027. Preparar un cotejo fechado con localidad Vícar y enlaces al organizador/inscripción; incorporar solo tras autorización expresa, pruebas y control del despliegue. Mantener histórica la incidencia de anuncio inicial y registrar aclaración sin borrar el aviso anterior.

Criterio de completitud: objetivo acotado, pruebas, PR/commit, resultado del despliegue si corresponde, documentación actualizada, limitaciones y siguiente prioridad.
