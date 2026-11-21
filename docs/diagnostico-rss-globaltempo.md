# Diagnóstico seguro del RSS de Google Alerts — Global Tempo

**Estado:** mejora propuesta para revisión mediante PR; los datos reales se conocerán **solo tras integrar y ejecutar el detector**. No activar fuentes directas ni publicar candidatas automáticamente.

## Finalidad

El detector de `scripts/alertas_globaltempo.py` consulta **solo el RSS de Google Alerts** indicado mediante el secreto `GT_ALERT_RSS_URL`. No visita ni descarga fichas de Global Tempo. Antes mostraba únicamente «0 resultados RSS relevantes», algo que no diferenciaba RSS vacío, descartes por enlaces, resultados antiguos o duplicados.

Con este cambio, la ejecución añade una línea de registro `Global Tempo: diagnóstico RSS { ... }` con **contadores agregados**, sin volcar contenido del RSS, URL privada de Google Alerts, títulos de carreras, identificadores, enlaces, búsquedas ni datos personales.

## Dónde consultarlo

1. Abrir [GitHub Actions](https://github.com/correradar-andalucia/correradar-andalucia.github.io/actions/workflows/detectar-alertas-globaltempo.yml) → **Detectar novedades de Global Tempo para revisión**.
2. Elegir una ejecución **posterior a la integración del cambio** (programada o `Run workflow`).
3. Abrir el trabajo **detectar** → paso **Buscar enlaces indexados y crear incidencias pendientes**.
4. Buscar la línea `Global Tempo: diagnóstico RSS`, interpretar sus cifras y después la línea tradicional «resultados RSS relevantes / incidencias nuevas / 0 publicaciones automáticas».

La tarea está programada a las **07:41 y 19:41 UTC**, sujeta a retrasos del programador GitHub Actions. En España peninsular esto equivale a **08:41 y 20:41** en invierno, **09:41 y 21:41** en verano. No coincide con los informes de ChatGPT de las 08:00. Una ejecución correcta con cero incidencias **no crea correos**.

## Lectura de los contadores

| Campo | Qué cuenta |
|---|---|
| `entradas_rss` | Entradas Atom/RSS recibidas y procesadas desde Google Alerts (antes de filtros). |
| `titulo_invalido` | Entradas sin título válido o demasiado genérico. |
| `enlace_no_admitido` | Entrada cuyo enlace no corresponde a una ficha HTTPS profunda `/carreras.php?id=...` permitida o al redireccionamiento Google esperado. |
| `fecha_no_valida` | La entrada carece de fecha de aviso parseable. **No se trata de la fecha de la carrera.** |
| `fecha_futura` | La fecha del aviso es posterior al día de lectura. |
| `fecha_antigua` | El aviso supera los **45 días** permitidos. |
| `duplicado_en_rss` | Otra entrada válida del mismo feed ya se refería al mismo ID de enlace. |
| `candidatos_validos` | Enlaces que superan los filtros antes de cruzar el historial. |
| `ya_conocidos` | Candidatos válidos cuya ficha ya tiene una incidencia histórica `gt-pendiente` (abierta o cerrada), consta en aprobados o se había cotejado en el catálogo histórico. **Cambios de una ficha conocida no abren aviso nuevo.** |
| `aplazados_por_limite` | Candidatos válidos inéditos que exceden el límite de **20 incidencias por ejecución**. Podrán procesarse en otra ejecución si siguen apareciendo en el RSS. |
| `incidencias_nuevas` | Issues editoriales `gt-pendiente` creadas en esta ejecución; requieren revisión humana. |
| `publicaciones_automaticas` | Siempre **0** en este detector. |

**Consistencia:** `entradas_rss = candidatos_validos + titulo_invalido + enlace_no_admitido + fecha_no_valida + fecha_futura + fecha_antigua + duplicado_en_rss`; en una ejecución correcta, `candidatos_validos = ya_conocidos + aplazados_por_limite + incidencias_nuevas`.

## Cómo diagnosticar un «0 novedades»

- `entradas_rss=0`: Google Alerts devolvió un feed sin entradas. El programa puede funcionar correctamente, pero la alerta no tiene resultados en ese momento. Revisar **desde la cuenta propietaria de Google Alerts** el contenido, la consulta de búsqueda y la entrega en formato RSS. No revelar ni pegar la URL secreta en un Issue.
- `entradas_rss>0`, pero `enlace_no_admitido>0` y `candidatos_validos=0`: probablemente el feed devuelve otro tipo de enlaces. Comprobar qué formato produce Google Alerts en la cuenta del titular **sin copiar enlaces privados a logs públicos**; proponer un ajuste validado con ejemplos sintéticos en PR independiente. No ampliar automáticamente dominios, parámetros ni visitar Global Tempo.
- `fecha_antigua>0`: Google devolvió resultados indexados antiguos; no tratarlos como ediciones actuales.
- `candidatos_validos>0` y `ya_conocidos=candidatos_validos`: no hay enlace nuevo; el mecanismo deduplica por ID, por lo que **no detecta cambios de fecha, distancia, horario ni inscripción** en enlaces conocidos.
- `incidencias_nuevas>0`: consultar [Issues pendientes](https://github.com/correradar-andalucia/correradar-andalucia.github.io/issues?q=is%3Aissue+is%3Aopen+label%3Agt-pendiente); seguir el protocolo de cotejo y aprobación manual. Correo/push depende de **Watch → Custom → Issues** y las notificaciones de la cuenta personal GitHub, no de Gmail SMTP ni de ChatGPT.
- Si el workflow informa **«pendiente configurar Google Alerts RSS»**, falta el secreto; si falla al leerlo, comprobar su existencia y validez desde Settings → Secrets and variables → Actions, **sin imprimir ni compartir su contenido**.

## Límites y privacidad

- No cambia `GT_ALERT_RSS_URL`, su URL, permisos, cron, flujo de aprobación, formato de Issues, ni `data/globaltempo_enlaces_aprobados.json`.
- No introduce consultas directas a Global Tempo, nuevas solicitudes a Google, seguimiento por cookies, ni descargas de resultados o inscritos.
- No descubre modificaciones de entradas antiguas: un RSS de alertas de buscador no equivale a una API oficial de estado de inscripciones.
- Los contadores se imprimen únicamente tras analizar el feed con éxito. La validación/errores siguen usando los mensajes de error existentes, sin mostrar el secreto.
- Pruebas automatizadas: Atom y RSS con entradas sintéticas, clasificación de cada descarte, deduplicados y límite de 20, **captura de logs para comprobar que no aparecen URLs, títulos ni secreto**. No confundir pruebas simuladas con la lectura real de Google Alerts.

## Qué exigir antes de integrar

- CI completa verde en PR: `python -m compileall -q scripts tests`, `python -m unittest discover -s tests -v`, `node --check assets/app.js`.
- Revisar que `scripts/alertas_nuevas_fuentes.py` siga pudiendo importar `read_feed` y `parse_timestamp`.
- Con aprobación de integración, examinar **la primera ejecución en Actions** y documentar el resultado real. No crear carreras nuevas sin revisión editorial ni activar scraping directo.
