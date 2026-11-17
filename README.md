# CorreRadar Andalucía

Calendario independiente de carreras populares, trail, cross, ultradistancia, obstáculos e híbridas de Andalucía. Proyecto en preparación.

## Principio editorial

**Fecha publicada en una fuente** no es lo mismo que **aprobación editorial**. El calendario conserva internamente la procedencia y la fecha de consulta; **la portada no muestra etiquetas técnicas redundantes** junto a cada fecha. Las fichas ofrecen el enlace original para comprobar posibles cambios. Distinguimos internamente:

- **Revisada**: confirmada por el equipo en la hoja editorial (`Publicar=Sí`, `Verificado` y URL de fuente).
- **Fecha en fuente**: leída directamente de una ficha o calendario de la fuente en la última captación. La fecha mostrada coincide con la publicada en esa fuente; no afirmamos que la carrera no pueda modificarse o cancelarse después.
- **Fecha cotejada**: recogida de un catálogo consultado previamente, con fecha de cotejo visible y advertencia de posibles cambios.
- **Modalidad por revisar**: una misma ficha profunda se clasificó de dos maneras y no se atribuye ninguna modalidad sin resolver la discrepancia.

**Las distancias se muestran cuando se recuperan expresamente** del título, de un campo de la ficha fuente o del registro cotejado, con su procedencia. No se deducen kilómetros por nombres como «Media Maratón» ni se ocultan datos solo por carecer de una aprobación editorial posterior. Cuando no se dispone de ellos, la tarjeta no repite un aviso de distancia desconocida. El filtro de distancia es opcional: todas las carreras, incluidas las que no tienen kilómetros publicados, aparecen al dejarlo en «Todas». Nunca inferir fechas, lugares, distancias ni inscripción a partir de la edición de años anteriores.

## Cobertura territorial y fichas de fuentes originales

CorreRadar incorpora **fichas puntuales cotejadas** en fuentes identificables de Sevilla, Jaén y Huelva, para reducir el desequilibrio territorial. Están almacenadas en `data/fichas_oficiales_2026-11-16.json`, con nombre, fecha, municipio, modalidad, kilómetros y hora **solo cuando constan expresamente en la fuente**. Cada entrada conserva el enlace exacto y el nombre de la fuente.

- `scripts/oficiales.py` valida el esquema, los enlaces HTTPS y la fecha de cotejo. Una revisión manual **no equivale a un lector automático permanente**.
- A los 30 días los datos dejan de mostrarse como lectura reciente y pasan a «fecha cotejada» para evitar prometer vigencia indefinida.
- La ficha publica la hora cuando se ha documentado. No se inventan recorridos, precios o desniveles.
- No se añade una distancia ante discrepancias. Por ejemplo, Camas figura con fecha y hora, pero con distancia pendiente de contraste entre fuentes.
- `_site/data/cobertura.json` mide las carreras por provincia y los campos de distancia y hora disponibles, sin necesidad de calcularlos manualmente.
- El filtro de distancia permite ver rangos de kilómetros **sin ocultar por defecto las carreras sin distancia**; estas solo se excluyen cuando el corredor selecciona expresamente un rango.
- La pantalla principal se simplifica a búsqueda, provincia, mes, distancia y seis grupos de modalidades. Se retiran los filtros técnicos por proveedor y por fecha consultada: la procedencia sigue visible en cada carrera, sin confundir al usuario con controles que no ayudan a escoger prueba.

La cobertura actual no garantiza que aparezcan **todas** las carreras. Solo deben añadirse eventos verificables; las nuevas provincias y fuentes se incorporarán de forma incremental y con pruebas automatizadas.

## Ampliación de fuentes del 17/11/2026

El archivo aportado `fuentes_oficiales_carreras_andalucia_ampliado.xlsx` contiene **45 fuentes en seis pestañas**, no 45 carreras ni 45 conectores habilitados. `config/fuentes_ampliadas_2026-11-17.json` conserva los 45 registros y su enlace original, clasificados por rol. Parte de ellos se solapan con las 50 fuentes del catálogo anterior: **no deben sumarse como si fueran fuentes diferentes**.

**Política editorial obligatoria:** los calendarios recopilatorios de terceros (Andalucía Running, Runnea, Corredores Populares, CarrerasPopulares.com, ClubRunning, RunAgain, Hybrid Race Map, Hybrid Race Hub, Metahíbrida y Sportplan) son **solo pistas para investigar**. No permiten crear una carrera, validar su fecha ni atribuirle distancias. Una carrera se incorpora únicamente si la edición actual está publicada por el organizador, una federación, un circuito provincial institucional o la plataforma responsable de su inscripción, y si se dispone de fecha, nombre, municipio y enlace de procedencia. `scripts/oficiales.py` impide usar estos diez dominios de agregadores como fuente final, incluso si alguien los etiqueta incorrectamente como «organizador».

Existe una **excepción muy restringida**: Corredores Populares, además de un calendario recopilatorio, aloja inscripciones activas con reglamento. La carrera de Navidad de El Rubio (20/12/2026) ya incluida anteriormente se cotejó en ese listado de inscripciones y se admite únicamente esa combinación de prueba/fecha/URL. Los demás resultados de ese dominio siguen sin validar fechas automáticamente. La excepción no autoriza a replicar su calendario.

- `data/fichas_oficiales_2026-11-17.json`: once carreras nuevas con año, fecha, localidad, distancia, origen y horarios contrastados en fuente primaria; incluyen el Medio Maratón de Sevilla que cambió al **13/12/2026**, pruebas de diciembre del Circuito Cordobés, Zurich Maratón de Sevilla 2027, Ultra Sierra Nevada 2027 y 101 km en 24 h de La Legión 2027.
- `data/distancias_cotejadas_2026-11-17.json`: mejora los kilómetros de cuatro fichas cordobesas ya presentes, sin añadir carreras duplicadas ni modificar sus fechas. Los cotejos nunca reemplazan distancias contradictorias leídas de fuentes actuales.
- Los dos lotes fechados del 16 y 17 de noviembre conservan sus **fechas de revisión individuales**: añadir una fuente nueva no convierte datos antiguos en datos recién consultados.
- **Excluidas sin inventar ediciones:** algunas competiciones nacionales de OCR, La Desértica o el Cross de Itálica no tienen una próxima fecha concreta cotejada durante esta revisión; la edición 2026 del Cross de Itálica y el Maratón de Málaga ya pasaron. HYROX Málaga 2027 presenta **discordancia en el comienzo del evento** entre páginas oficiales (14 y 15 de abril), así que no se publica una fecha de salida arbitraria para todas las modalidades.
- No se incorpora duatlón ni triatlón por defecto: CorreRadar prioriza carreras a pie.

## Global Tempo: nuevas carreras y control de publicaciones

**Causa de las omisiones:** Global Tempo aparecía en la semilla del 15/11/2026, pero **no formaba parte de los lectores automáticos ejecutados cada 12 horas**. Un evento nuevo podía quedarse fuera indefinidamente.

La revisión del **17/11/2026** incorpora en `data/fichas_globaltempo_2026-11-17.json` diez fichas individuales de la plataforma de inscripciones, mediante **cotejo manual de fechas, municipio y modalidades**. Entre ellas aparecen dos carreras nuevas no presentes en la semilla:

- **VII Carrera San Silvestre Alhendín**, 19/12/2026, 18:00, sin kilómetros comprobados (varían según categoría).
- **XIII Subida a la Cruz de la Atalaya**, Padul, 31/01/2027, 10:00, 8,72 km. Fecha y distancia contrastadas con el artículo 3 y la tabla técnica del reglamento; el encabezado reutilizado del PDF contiene un año anterior, pero la fecha operativa del artículo es 2027.

Además se completan kilómetros, horarios y enlaces específicos para Neptune Race, CxM Albuñol Trail, CxM Albuñuelas y Carrera Navideña de Escúzar, entre otras, sin crear fichas repetidas. El Trail de la Contraviesa tiene una excepción de deduplicación explícita: FADMES lo ubica en «Albuñol y Sorvilán» y Global Tempo en «Albuñol».

**No se ha incluido Playa Cambriles Race**: Global Tempo muestra 22/11/2026 en la ficha, pero su reglamento sitúa la celebración en 02/08/2026. Tampoco se han importado eventos de natación, ciclismo, duatlón, circuitos genéricos, pasacalles ni inscripciones sin carrera competitiva a pie.

**Importante:** esta revisión puntual no significa que Global Tempo se actualice automáticamente. Su aviso legal requiere autorización para reutilizar contenido del sitio. Antes de integrar un lector o una API en las ejecuciones de GitHub Actions, se debe acordar expresamente con Global Tempo un acceso a sus **datos mínimos de eventos** o una fuente autorizada (enlace, fecha, localidad, modalidad, kilómetros). No se copian descripciones, imágenes, reglamentos ni listados de participantes. Hasta entonces, las fichas se añaden por cotejo puntual, conservan su fecha de revisión y se etiquetan como antiguas tras 30 días. La fuente `globaltempo` sigue declarada **sin consulta automática** en el informe de captación.

## Arquitectura

- `index.html`, `assets/styles.css` y `assets/app.js`: interfaz estática, búsqueda, filtros por provincia, mes, modalidad agrupada y distancia; paginación de 20 resultados.
- `scripts/captacion.py` y `scripts/captacion_extra.py`: lectura de fuentes autorizadas, con control de dominios y robots.txt.
- `scripts/distancias.py`: extrae medidas explícitas de títulos, campos, apartados de modalidades y descripciones de la misma carrera. Normaliza metros y kilómetros sin deducir distancias por el tipo de carrera.
- Para Runnink y Gesconchip, el captador consulta la ficha concreta y, si se puede, sus modalidades de inscripción. Se respetan `robots.txt`, límites de tamaño, tiempos de respuesta y pausas entre consultas; un fallo no elimina la carrera.
- Cada distancia recuperada de una ficha concreta conserva `distancia_fuente`, enlazable en la ficha de CorreRadar.
- `scripts/multifuente.py`: semilla histórica fechada, no equivalente a una consulta en directo. A partir de 30 días requiere reconfirmación.
- `scripts/deduplicacion.py`: combina fichas según nombre, fecha, municipio, distancias y enlaces profundos; registra descartes y discrepancias.
- `scripts/build.py`: genera el directorio `_site/`, fichas individuales, JSON, auditoría, páginas informativas y sitemap.
- `config/site.json`: correo, titularidad y bandera `public_launch` (mantener `false` hasta completar los requisitos de lanzamiento).
- `data/carreras.csv`: datos editoriales locales; en GitHub Actions puede sustituirse por el CSV publicado mediante la variable `SHEET_CSV_URL`. El archivo `data/carreras.json` del repositorio NO representa el calendario desplegado: se genera en el build.
- `data/respaldo_runnink_2026-11-16.json`: copia de las 13 referencias obtenidas de Runnink el 16/11/2026, usada como respaldo cuando falla temporalmente la consulta en vivo. Se muestran como «fecha cotejada», nunca como consulta reciente; tras 30 días exigen reconfirmación.
- `data/distancias_cotejadas_2026-11-16.json` y `data/distancias_cotejadas_2026-11-17.json`: kilómetros corroborados para la edición y municipio exactos en fuentes oficiales. Solo se rellenan campos vacíos: los conflictos con fuentes actuales no se sobreescriben y se auditan.

## Desarrollo y pruebas locales

Se requiere Python 3.12; Node.js se usa para comprobar sintaxis JavaScript.

```sh
python -m unittest discover -s tests -v
node --check assets/app.js
CORRERADAR_FETCH=0 SHEET_CSV_URL='' python scripts/build.py
```

En Windows, configura las variables equivalentes para desactivar la captación en red. El resultado estará en `_site/` y `_site/data/carreras.json`.

## Publicación

- `.github/workflows/verificar-multifuente.yml`: pruebas sobre solicitudes de cambio y ejecución manual.
- `.github/workflows/publicar.yml`: ejecuta pruebas **antes de cada publicación**, genera el sitio y despliega GitHub Pages desde `main`. También se ejecuta de forma programada cada 12 horas.
- La generación falla ante una fila editorial publicada sin fuente o validación, y no admite localidades con horarios incrustados.
- `_site/data/auditoria_duplicados.json` muestra duplicados fusionados, conflictos y candidatas descartadas por localidad inválida.
- `_site/data/estado_fuentes.json` muestra fuentes consultadas e incidencias. Una fuente no disponible nunca debe tratarse como confirmada.

## Incorporación de una carrera confirmada

1. Confirmar en una fuente específica nombre, fecha, municipio, modalidad y enlace.
2. Completar la fila del CSV editorial con la fecha de revisión en `Verificado`, URL en `Fuente`, estado adecuado y `Publicar=Sí`.
3. Introducir distancias, precio y otros detalles **solo si están contrastados**.
4. Ejecutar los tests, generar el sitio y comprobar que la carrera se presenta como confirmada.
5. Si las fuentes discrepan, detener la aprobación y resolver el conflicto manualmente.

## Control automático previo al lanzamiento

Cada actualización programada tiene ahora **dos comprobaciones** antes de desplegar:

- `scripts/control_calidad.py` y `_site/data/control_calidad.json`: validan fechas, localidades, provincias, modalidades, HTTPS y procedencia, y registran cobertura por provincia, distancias y horarios. Cuando menos de **dos fuentes de captación** han podido leerse en una actualización con red, **se detiene la publicación y se conserva el último sitio desplegado**. Las pruebas sin red se identifican claramente y no se hacen pasar por una captura en directo.
- `scripts/verificar_salida.py`: comprueba que todas las páginas de carrera y archivos esenciales existen y que la portada y **todas las fichas** siguen llevando `noindex,nofollow` mientras `public_launch` sea falso.

La página principal muestra el **año junto al día y al mes** (importante para carreras de 2026 y 2027), y su botón de fuente prioriza el enlace a la **ficha individual** frente a portadas o calendarios generales cuando ambos están disponibles. El recuento de resultados se anuncia de forma accesible sin leer todos los artículos en cada filtro.

Estas comprobaciones detectan errores técnicos y ciertas inconsistencias editoriales: **no confirman de forma autónoma que una carrera vaya a celebrarse**. El enlace al organizador sigue siendo necesario.

## Antes de abrir el sitio a buscadores

Completar la identidad del titular y revisar el aviso legal, privacidad y cookies, incluida la conveniencia de informar un domicilio según corresponda. Confirmar calidad de las fuentes principales, comprobar enlaces y usabilidad. **No basta con poner `public_launch: true`:** se exige además un correo de contacto, `legal_name` y `legal_review_complete: true`, que solo debe introducirse tras la revisión del responsable. Mientras tanto, mantener `public_launch: false`. Las fichas provisionales conservarán `noindex`; el sitemap incluye solo eventos aprobados editorialmente.

## Limitaciones conocidas

La cobertura provincial no es uniforme. Los lectores dependen del formato de cada fuente y pueden dejar de funcionar. Algunas fichas solo enlazan a calendarios de terceros y no a la inscripción directa. **Una fecha publicada puede variar después**; siempre facilitar el enlace a la fuente para comprobar cambios. Las distancias que solo aparecen en imágenes, PDFs o secciones no estructuradas pueden seguir sin recuperarse automáticamente.
