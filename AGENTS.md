# CorreRadar Andalucía — instrucciones permanentes para agentes

Calendario independiente de carreras a pie de Andalucía. Idioma de trabajo: español. Zona horaria editorial: Europe/Madrid. El repositorio y las fuentes originales son la referencia, no los recuerdos de un chat.

## Antes de modificar
- Leer docs/ESTADO_PROYECTO.md (instantánea fechada), docs/DECISIONES.md, docs/MANUAL_OPERATIVO.md y docs/HOJA_DE_RUTA.md. Consultar main, CI, última publicación correcta e incidencias abiertas; no asumir que una instantánea sigue vigente.
- Trabajar en rama separada y PR de alcance limitado; no introducir secretos, datos privados, información de participantes, dependencias innecesarias ni cambios de diseño ajenos a la tarea.
- GitHub Pages es público aunque noindex. Mantener el prelanzamiento, las salvaguardas legales y el panel separado. No activar monetización, indexación, nuevas fuentes directas ni cambios de permisos sin aprobación específica.

## Datos y fuentes
- Solo hechos mínimos verificables de la misma edición futura: nombre, fecha, municipio/provincia, modalidad, distancia y hora documentadas, enlace HTTPS. Campos desconocidos vacíos; no inferir fecha del RSS, kilómetros por nombre, plazas por enlace ni cancelación por ausencia.
- Respetar condiciones, robots, dominios y límites de lectura. Consultar config/derechos_fuentes.json. Global Tempo y cuatro candidatas (DeporTime, CroniusSport, Cronofinisher, Patronato de Jaén) por RSS y cotejos puntuales, no scraping directo. No seguir formularios, resultados ni inscritos. No mostrar secretos ni URLs privadas RSS.
- Mantener identidad/deduplicación, prioridad editorial, procedencia y caducidad de los datos. Los respaldos conservan fecha de consulta original; no reetiquetar como vivos. No desactivar bloqueos de calidad para conseguir un despliegue.
- Ambos flujos de publicación requieren la referencia validada de Pages o la copia del último despliegue confirmado. Aplicar la inicialización y recuperación del manual operativo.
- En las fichas de Cruzando la Meta, no extraer municipio de una línea que combine fecha/hora/recinto, ni atribuir distancias de senderismo a carreras. Los diagnósticos de descarte solo incluyen recuentos por motivo y no requieren más descargas; respetar siempre robots y la evidencia por edición.
- Si un lector devuelve cero carreras pese a una referencia reciente suficiente, marcar lectura sospechosa y bloquear la publicación sin alterar la copia confirmada. Distinguir de calendarios legítimamente vacíos, pausas por derechos, fallos HTTP y pruebas sin red; registrar los avisos parciales y no inventar cancelaciones.
- Las cancelaciones/anulaciones/retiradas expresas del CSV editorial, con identidad de edición y evidencia, prevalecen sobre captación, cotejos, semilla y respaldos. No deducir cancelación por ausencia; una ficha aprobada contradictoria debe bloquear la compilación. Otras fechas requieren revisión, no veto automático.
- Los avisos rss-pendiente requieren verificación editorial y autorización de incorporación. No usar gt-aprobar para otras fuentes; mantener etiquetas tras cerrar. Cerrar un aviso como publicado solo tras verificar despliegue y ficha. Si una URL se reutiliza, revisar edición manualmente.

## Validación y entrega
- Ejecutar `python -m compileall -q scripts tests`, `python -m unittest discover -s tests -v`, `node --check assets/app.js`. Probar también JavaScript nuevo y generación offline si procede (`CORRERADAR_FETCH=0`), sin afirmar que demuestra captación real. Consultar workflows antes de cambiar pruebas.
- CI de PR correcto antes de integrar. Integrar solamente si autorizado por el responsable y sin saltar protecciones. Confirmar publicación mediante Actions y, si es accesible, JSON/ficha pública; distinguir compilación, despliegue y avisos. No inventar métricas ni afirmar entrega de Gmail sin evidencia.
- Informar enlaces, cambios, pruebas, decisiones, incidencias y bloqueos. Actualizar estado/hoja de ruta/decisiones cuando haya cambios sustanciales. No duplicar las tareas programadas existentes.
