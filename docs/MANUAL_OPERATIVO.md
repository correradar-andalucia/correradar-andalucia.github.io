# Manual operativo

## Trabajo habitual
Abrir [panel](https://correradar-andalucia.github.io/panel/) y [Actions](https://github.com/correradar-andalucia/correradar-andalucia.github.io/actions). El panel representa la última publicación correcta; no demuestra que el último intento haya funcionado. Si falla, consultar pasos y logs sin exponer secretos. No descargar fuentes vetadas para diagnosticar.

## Revisar avisos
- [RSS cuatro fuentes](https://github.com/correradar-andalucia/correradar-andalucia.github.io/issues?q=is%3Aissue+is%3Aopen+label%3Arss-pendiente) y [Global Tempo](https://github.com/correradar-andalucia/correradar-andalucia.github.io/issues?q=is%3Aissue+is%3Aopen+label%3Agt-pendiente).
- Verificar mismo año/edición, fecha futura, municipio y provincia andaluces, carrera a pie, ausencia de cancelación o duplicación, distancias/horarios si constan. Usar organizador, administración o ficha de cronometraje pública; no consultar inscritos. Fecha del aviso no es fecha de carrera.
- Presentar resultados con enlace y pedir autorización editorial agrupada (si no consta ya autorización específica). Para las cuatro nuevas fuentes: crear/actualizar catálogo de fichas fechado y registrado en scripts/oficiales.py; PR y pruebas, verificar deduplicación. No basta marcar casillas.
- Para Global Tempo: el flujo gt-aprobar publica únicamente nombre y enlace en sección separada, con revisión y sus tres casillas; la carrera fechada requiere fuente independiente. No usar etiqueta GT para otros proveedores.
- Cerrar como publicada tras éxito de despliegue y comprobación de incorporación (o descartar tras verificación y autorización). Mantener etiqueta de origen para deduplicar. Si el JSON no es accesible, usar ejecución y evidencia del histórico y declarar el límite.
- Notificaciones de nuevas carreras: Issues tras despliegue, seguimiento Watch > Custom > Issues y email en GitHub. Un aviso de descubrimiento y uno de publicación no son lo mismo.

## Gestión con ChatGPT y Codex
Crear Proyecto ChatGPT «CorreRadar Andalucía» y mover el chat original desde su menú. Pegar en instrucciones del proyecto el texto de TRASPASO_CHATGPT.md. Abrir nuevos chats por tarea; no depender de una única conversación ni asumir memoria habilitada. GitHub conserva instrucciones y hechos.
Abrir https://chatgpt.com/codex, conectar repositorio si la interfaz lo solicita y comenzar con una tarea de inspección sin cambios. Codex lee AGENTS.md. Pedir PR acotada y pruebas; decidir antes de publicar. En ChatGPT usar Work para investigación, revisión y coordinación si está disponible. La conexión de apps y creación/movimiento del proyecto requieren intervención del titular; no compartir credenciales.

## Supervisión programada
Propuesta: una comprobación diaria de salud e incidencias, un informe semanal de cobertura y candidatos, una revisión mensual de fuentes/seguridad/privacidad. Consultar Scheduled de ChatGPT para las tareas efectivamente activadas. Las tareas de supervisión deben ser de solo lectura y recomendaciones, sin fusiones, publicación ni cierres automáticos; el responsable puede aprobar después. Verificar acceso en cada ejecución y declarar bloqueos. No sustituir GitHub Actions ni repetir sus descargas.
