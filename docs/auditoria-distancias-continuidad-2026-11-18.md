# Auditoría de distancias y continuidad del calendario — 18/11/2026

Punto de partida: ejecución 44270628811, 163 carreras, 64 con distancia (39,3 %), 99 sin distancia numérica y 10 de estas con rangos orientativos de cross. Las cifras cambian con cada actualización.

## Primera tanda de cotejos

El fichero `data/distancias_cotejadas_2026-11-18_lote2.json` registra siete cotejos de ediciones próximas y tres alias de carreras cordobesas previamente cotejadas. Se ha comprobado la fecha y sede, y se añaden únicamente hechos y enlaces. Los kilómetros de Camas y Faraján se marcan como aproximados; La Donaira excluye los 12 km de senderismo. We Run UMA se toma de la presentación de la universidad recogida por prensa; otras webs discrepan. Camas conserva los 7,2 km aproximados del reglamento municipal (art. 2), no los 7,5 km de la agenda turística.

No se deduce distancia a partir de una edición pasada o un nombre genérico. En carreras de categorías, se distingue una distancia principal anunciada de rangos sin itinerario definitivo. El objetivo del 80 % es orientativo, no se garantiza. No se ha investigado exhaustivamente cada una de las 99 fichas en esta tanda.

## Continuidad

Cada actualización obtiene el JSON de la última publicación propia antes de consultar las fuentes. Ante un fallo de red transitorio de una fuente habilitada, se conservan carreras futuras ausentes durante hasta siete días desde su última consulta real, con fecha original y aviso visible. No se reintroducen carreras ante lectura correcta sin resultado, veto de acceso, pausa por derechos, contradicción de fecha próxima o coincidencia con otro evento. No se realizan peticiones adicionales para obtener ese respaldo. No se confunde una incidencia con una cancelación. Los respaldos antiguos de la semilla histórica tienen reglas independientes; no confundir que una carrera figure en esa semilla con una validación reciente.

Este control cubre fallos completos identificables de cada fuente, no todas las posibles lecturas parciales ni las cancelaciones no comunicadas. Si no se obtiene el JSON previo, la compilación continúa sin el nuevo respaldo. Para distancias, se mantienen las reglas de 30 días y procedencia de la revisión anterior.

## Inventario para próximas revisiones

Cada despliegue genera `data/distancias_pendientes.json` a partir de las fichas finalmente publicables, con fecha, localidad, provincia, fuente, prioridad por proximidad (30/90 días), y distinción entre distancia orientativa y pendiente. No es una investigación automática en Google ni un permiso para descargar reglamentos en masa. Sirve para revisar las carreras una a una sin repetir cotejos ya integrados.

La extracción directa de Global Tempo y el enriquecimiento de Gesconchip permanecen desactivados. Las diez fuentes habilitadas y los avisos de GitHub no se modifican.
