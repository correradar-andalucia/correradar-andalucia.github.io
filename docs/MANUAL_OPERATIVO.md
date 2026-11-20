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

## Continuidad de GitHub Pages

Los dos flujos de publicación usan el mismo calendario anterior. Primero descargan el JSON público de Pages, validan su estructura y, cuando hay un despliegue confirmado en el diario, comprueban que coincida su SHA-256. Así se detecta también una respuesta anterior de la CDN. Ante error HTTP, JSON corrupto, calendario vacío, esquema inválido o huella distinta, usan la copia confirmada del diario si supera las comprobaciones de estructura, procedencia e integridad. Si ambas referencias fallan, la ejecución se bloquea antes de la captación y la web anterior sigue publicada. El resumen de Actions indica el origen elegido y los descartes. Si falla calidad, el log de compilación indica las ausencias por fuente.

El diario vive en la rama `estado-correradar-continuidad`, en `estado.json`. Conserva una copia confirmada sin caducidad de almacenamiento y un intento pendiente mientras Pages lo resuelve. La referencia permanece disponible después de la caducidad de los artefactos. Cada escritura reemplaza la punta con un commit independiente y exige que el SHA remoto siga siendo el leído. La rama mantiene una única versión alcanzable. GitHub puede conservar objetos antiguos durante su limpieza. Los artefactos de calendario de cada intento se guardan durante siete días. La copia registra versión de esquema, commit del código generado, ID de ejecución, número de intento, ID nativo de Pages, fecha UTC de generación y SHA-256 de los bytes desplegados.

Ambos workflows comparten la exclusión de GitHub Actions durante la generación, el despliegue y los avisos. El job de despliegue registra el intento antes de solicitar la publicación con el artefacto oficial y OIDC de GitHub. Guarda el identificador devuelto por Pages y confirma la copia únicamente cuando la API devuelve `succeed`. Ante un rechazo o fallo definitivo conserva la copia confirmada anterior. Si se interrumpe el job tras guardar el identificador, la ejecución siguiente consulta a Pages para reconciliar el resultado antes de usar cualquier copia. Los avisos y el cierre de incidencias se ejecutan después de guardar la copia. Con el historial de avisos se deduplican notificaciones. La rama operativa tampoco toma datos de `data/carreras.json` de `main`.

Se mantienen los límites de recuperación de carreras de siete días desde la consulta original y de distancias de 30 días cuando corresponde. Se conservan los vetos de acceso, las pausas por derechos, la procedencia y los criterios de identidad y calidad. La validación del archivo admite las fechas de carreras ya pasadas en una publicación anterior. Su uso en una nueva publicación queda sujeto a los controles de caducidad. `CORRERADAR_FETCH=0` sigue disponible para CI y pruebas locales.

### Inicialización y reintentos

1. Tras la integración autorizada, comprobar que Pages sirve un calendario válido. El primer flujo protegido lo usa como referencia y guarda su primera copia al confirmar el despliegue. Si Pages falla antes de ese primer éxito, esperar a que vuelva a servir el calendario o ejecutar la recuperación extraordinaria con evidencia de un despliegue anterior.
2. Si se bloquea una generación, consultar el resumen y los logs en Actions. Ante un despliegue de estado incierto, comprobar el ID que se registró y dejar que Pages alcance un resultado definitivo. Si el diario registra un pendiente sin ID, aplicar el procedimiento extraordinario.
3. Para volver a generar una publicación, ejecutar un flujo nuevo desde `main` o **Re-run all jobs** si el código del flujo sigue vigente. Un reintento del job de despliegue aislado no reutiliza artefactos de una compilación anterior. Un reintento de avisos puede continuar si ese intento sigue siendo el último confirmado. GitHub puede reemplazar un workflow que esté todavía en cola. Si afecta a una aprobación GT, revisar su incidencia y volver a aplicar la etiqueta tras comprobar su estado editorial.

### Recuperación extraordinaria

1. Coordinar la intervención con el responsable y pausar los dos flujos de publicación. Asegurarse de que no quede un despliegue en curso. Registrar la punta con `git ls-remote --refs origin refs/heads/estado-correradar-continuidad`. Usar `sin-inicializar` como valor esperado si la rama aún no existe.
2. Identificar en Actions el último despliegue correcto, su intento y su ID nativo de Pages. Si hay un intento pendiente sin ID y se localiza el ID **de ese mismo intento**, desde el checkout de `main` ejecutar `python scripts/publicacion.py asociar --estado SHA_DEL_DIARIO --despliegue ID_PAGES`. El comando exige un resultado definitivo y, en caso de éxito, verifica que Pages sirva exactamente el calendario pendiente. Si la solicitud nunca se aceptó, verificarlo en Actions y en el historial de Pages. En ese caso, al restaurar una copia que Pages esté sirviendo se puede usar `--descartar-intento-sin-id`. Si no se puede vincular el ID o confirmar el resultado, mantener el bloqueo.
3. Si la copia falta o está dañada, obtener los bytes exactos del último despliegue probado. Usar el JSON en Pages si es accesible y coincide con la evidencia del despliegue, o el artefacto `calendario-publicacion-INTENTO` de la ejecución identificada. El flujo ordinario anterior a esta protección lo llamaba `calendario-para-avisos`. Antes de usar un artefacto, confirmar en Actions que el job de despliegue de ese intento tuvo éxito y comprobar el ID nativo de Pages en sus logs. Calcular `sha256sum carreras.json`. En un calendario etiquetado, tomar commit, ejecución, intento y fecha de `publicacion_continuidad`. Para el formato anterior, documentarlos a partir de Actions y del commit con el que se generó la web.
4. En un checkout de `main`, con acceso autorizado al repositorio y un `GH_TOKEN` habilitado para consultar Pages, usar este comando. El token de Git usado para `origin` debe poder escribir en la rama del diario.

   ```bash
   export GITHUB_REPOSITORY=correradar-andalucia/correradar-andalucia.github.io
   python scripts/publicacion.py recuperar carreras.json \
     --estado SHA_DEL_DIARIO --despliegue ID_PAGES --sha256 SHA256_DEL_JSON \
     --commit SHA_DEL_CODIGO --ejecucion ID_DE_EJECUCION --intento NUMERO_DE_INTENTO \
     --fecha 2026-11-20T12:00:00Z
   ```

5. Verificar que se guardó la copia y reanudar los flujos previa coordinación. Si no hay bytes verificables del último despliegue, dejar el flujo bloqueado. Si la API devuelve un resultado incierto o el intento pendiente perdió su identificador, puede ser necesario consultar al soporte de GitHub antes de continuar. La copia no constituye una restauración del sitio HTML completo.

### Verificación tras la integración

- Comprobar en un flujo ordinario autorizado que se elige Pages o la copia confirmada, que no hay bloqueos de calidad y que aparece `Copia confirmada de GitHub Pages` antes del job de avisos.
- Comparar el SHA-256 registrado con el JSON servido por Pages una vez propagado y con `sha256` de `confirmado` en `estado.json`. Comprobar que coinciden el commit, la ejecución y el intento.
- En la siguiente aprobación editorial GT autorizada, comprobar la misma secuencia y que la incidencia se marca publicada tras confirmar la copia. Ejecutar `python -m unittest discover -s tests -p 'test_publicacion.py' -v` para verificar caídas, corrupción, reintentos y la pérdida de seis carreras sin provocar fallos en producción.
