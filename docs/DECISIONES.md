# Decisiones de proyecto

Registro de criterios consolidados a 20/11/2026; revisar explícitamente si se cambian.

- Sitio público en GitHub Pages, sin indexación mientras esté en prelanzamiento. El panel /panel/ también es público, no autentica y no contiene información privada. Sin cambio de hosting ni monetización aprobado.
- Mantener diez lectores directos actuales con consulta factual limitada y reservas documentadas (config/derechos_fuentes.json). Consulta mínima no equivale a licencia general. Respetar robots, condiciones, límites, dominios; no sumar lectores sin revisión y autorización específica.
- Global Tempo: exclusivamente Google Alerts y revisión de enlaces; no lectura directa salvo feed autorizado documentado. Los enlaces aprobados no crean automáticamente carreras fechadas.
- DeporTime, CroniusSport, Cronofinisher y Patronato de Jaén: vigilancia RSS, revisión individual; condiciones de reutilización y robots pendientes de aclarar. Workflow independiente y secretos ya configurados; no divulgar URL privada.
- Calidad antes de cantidad: procedencia de fecha, distancia y hora; no inventar datos, no inferir plazas; estados de inscripción caducables, respaldo temporal hasta siete días bajo condiciones, controles ante pérdida anómala, no asumir cancelaciones. No conservar inscripciones como actuales desde respaldo.
- Los dos flujos bloquean la publicación sin una referencia de continuidad válida. Pages tiene prioridad. El diario conserva la última copia confirmada y permite recuperar un intento interrumpido mediante el estado nativo de Pages y el SHA-256 del JSON bajo la URL pública. El registro provisional contiene metadatos y huella. La escritura queda limitada a la rama operativa con comprobación de su SHA. En el flujo ordinario, `contents: write` se concede al job de despliegue, con autorización expresa del responsable para la futura integración.
- Mantener histórico de avisos y etiqueta de los candidatos; preservar separación de candidato, aprobación y publicación. Emails nativos de GitHub, sin SMTP propio.
- El responsable delega mejoras y revisión en asistentes; autoriza publicación por edición o lote, no publicación indiscriminada. Cambios de política legal, permisos, monetización, indexación y diseño significativo requieren decisión explícita.
- GitHub pasa a ser la memoria operativa permanente: instrucciones en AGENTS.md, estado fechado, manual, decisiones y hoja de ruta. ChatGPT coordina y supervisa; Codex desarrolla; Actions ejecuta. Un chat largo no es un requisito para operar.
