# Avisos RSS de DeporTime, CroniusSport, Cronofinisher y Patronato de Jaén

## Configuración

Workflow: `.github/workflows/detectar-alertas-nuevas-fuentes.yml`.
Secretos de repositorio (cada valor es exclusivamente su URL de Google Alerts RSS):

| Fuente | Secret |
|---|---|
| DeporTime | DEPORTIME_ALERT_RSS_URL |
| CroniusSport | CRONIUSSPORT_ALERT_RSS_URL |
| Cronofinisher | CRONOFINISHER_ALERT_RSS_URL |
| Patronato de Jaén | PATRONATO_JAEN_ALERT_RSS_URL |

Se ejecuta al integrar el detector y cada 12 horas aproximadamente (07:17 y 19:17 UTC), o manualmente desde Actions. Global Tempo conserva su flujo, secretos y aprobación independiente.

## Funcionamiento

Lee solo los cuatro feeds Google Alerts. Comprueba origen HTTPS, rutas de fichas públicas o noticias pertinentes y fecha del aviso (máximo 30 días). No sigue las URLs de las fichas ni descarga participantes, resultados, reglamentos, textos o imágenes. Limita a cinco incidencias nuevas por fuente y ejecución. Deduplica URLs canónicas frente a los catálogos oficiales de ediciones futuras y los marcadores de incidencias abiertas/cerradas con etiqueta rss-pendiente. Conservar esa etiqueta aunque se cierre el aviso. Si no puede consultar el historial, se detiene; cada RSS se procesa independientemente. Nunca imprime las claves ni direcciones privadas de alertas.

## Revisión editorial

Abrir Issues y filtrar por rss-pendiente. Abrir solo la ficha pública de la que se dispone de enlace y verificar edición futura, fecha, municipio/provincia de Andalucía, modalidad, kilómetros y hora cuando figuren, ausencia de duplicado o cancelación. Incorporar hechos mínimos al catálogo mediante revisión del repositorio y cerrar la incidencia (o cerrarla como descartada). No se publica por marcar una etiqueta. Google Alerts no certifica las fechas ni garantiza cobertura de todas las pruebas. Las alertas pueden incluir pruebas de otras comunidades; la comprobación geográfica es editorial. Se rechazan algunas rutas ambiguas deliberadamente. Una URL reutilizada para otra edición puede requerir reabrir manualmente la incidencia anterior: no se interpreta la actualización del índice como una nueva edición.

El aviso de GitHub y el aviso posterior de nueva carrera publicada son distintos. La entrega de emails depende de Watch > Custom > Issues y notificaciones por email activadas; ningún workflow accede a Gmail. El detector no tiene permisos para cambiar el calendario. Las cuatro fuentes siguen en revisión editorial, sin scraping directo.
