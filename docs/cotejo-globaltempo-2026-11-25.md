# Global Tempo — cotejo de cobertura y edición faltante (25/11/2026)

## Alcance y límites

Revisión **puntual y limitada** de la primera página pública de `https://www.global-tempo.com/index.php` y de la **copia confirmada de 156 carreras** del workflow [45626878063](https://github.com/correradar-andalucia/correradar-andalucia.github.io/actions/runs/45626878063). No se descargó masivamente su calendario ni se activó un lector; no es una auditoría exhaustiva de todas las páginas ni de nuevas inscripciones futuras. El trabajo mantiene `noindex`, los diez lectores anteriores y la revisión editorial.

El proveedor advierte en [su aviso legal, apartado 8](https://www.global-tempo.com/avisolegal.pdf) que la reproducción y el uso de contenidos requieren autorización previa por escrito independientemente de la finalidad. GitHub Pages **no es privado** aunque solo lo conozca una persona. Se mantiene `config/derechos_fuentes.json:fuentes_externas.globaltempo.feed_directo_autorizacion.estado=pendiente`, sin permitir descarga periódica. El adaptador autorizado `scripts/globaltempo_feed.py` ya existe, pero sigue desactivado.

## Comparación de las pruebas competitivas visibles

- **Ya presentes** en la copia confirmada: Neptune Race (Torrenueva Costa, 05/12/2026), II San Silvestre de Armilla (12/12/2026), VII Carrera San Silvestre Alhendín (19/12/2026), CxM Albuñuelas (20/12/2026), Carrera Solidaria Navidad Villa de Otura (22/12/2026), III Carrera Navideña Escúzar (27/12/2026), XXV Carrera Nocturna Las Gabias (30/12/2026), XIII Subida Cruz de la Atalaya (Padul, 31/01/2027), La Última Fortaleza OCR (Lanjarón, 01/05/2027). Las variantes de nombre no son nuevas ediciones.
- **No se cuentan como carreras** independientes los circuitos globales (CXM Diputación y Mamut de Padul) o senderismo, natación, mushing, duatlón y ciclismo, ni el pasacalles no competitivo de Alhendín.
- **Ausencia concreta documentada:** XVI CxM Valle de los Guájares, **Los Guájares (Granada), 07/02/2027**. La búsqueda en las 156 fichas no localiza su edición. No confundir con la XV edición de 2026 ni con otro evento del mismo día en la provincia.

## Cotejo por reglamento de la organización de 2027

El [reglamento específico de la XVI edición](https://www.global-tempo.com/documentos/6b054bea321ca_2ff0acf70406a407ac92.pdf) (artículos 2 y 3, página 2) indica:
- Fecha 7/02/2027; municipio de **Los Guájares**, salida desde Guájar Alto.
- **CXM 24 km** salida **09:00**; **Mini CXM 12 km** salida **10:00**. Dos recorridos dentro de la misma edición.
- Información de plazas/inscripción no incorporada al catálogo, porque es variable y las páginas pueden tener estados contradictorios.
- La propia ficha de inscripción pública [edición #3329](https://www.global-tempo.com/carreras.php?id=3329) identifica esta edición, y [Social Trail](https://calendario.socialtrail.es/evento/cxm-valle-de-los-guajares/CxMValledelosGuajares_2027) coincide en municipio, fecha y distancias. Otros agregadores proyectan septiembre de 2027 desde la edición anterior: no usar esa **estimación** frente a un reglamento explícito de XVI 2027.

La ficha se registra **una sola vez**, de forma **editorial puntual** y con enlace a la edición; no se implementa descarga ni reproducción masiva del sitio de Global Tempo. `hora=09:00` refleja la salida principal; la Mini está documentada aquí para evitar atribuirle el horario de la CXM larga. La fila sigue siendo `fuente oficial cotejada`, no se hace pasar una lectura automatizada por aprobación humana.

## Avisos y siguientes pasos

El detector Google Alerts ha recibido 0 entradas en 5 ejecuciones del 23 al 25/11/2026. El [issue #87](https://github.com/correradar-andalucia/correradar-andalucia.github.io/issues/87) guarda el seguimiento del vacío. El [PR #88](https://github.com/correradar-andalucia/correradar-andalucia.github.io/pull/88) introduce aviso de salud deduplicado, **sin mejorar por sí mismo la cobertura de Google Alerts**.

Si se aprueba esta alta editorial, comprobar que el PR pasa CI y que la ejecución de publicación confirma la ficha nueva en /data/carreras.json, la continuidad, `noindex`, ausencia de duplicados y avisos sin errores. No prometer notificación email ni afirmar estado de inscripción a partir del reglamento.

**La revisión del primer listado no es prueba de que no existan más carreras faltantes fuera de él.** Para cobertura sistemática de Global Tempo debe acordarse feed de hechos mínimos con licencia o autorización del proveedor, comprobar robots y activar el adaptador únicamente después de documentarlo.
