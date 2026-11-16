# CorreRadar Andalucía

Calendario independiente de carreras populares, trail, cross, ultradistancia, obstáculos e híbridas de Andalucía. Proyecto en preparación.

## Principio editorial

**Fecha publicada en una fuente** no es lo mismo que **aprobación editorial**. El calendario diferencia:

- **Revisada**: confirmada por el equipo en la hoja editorial (`Publicar=Sí`, `Verificado` y URL de fuente).
- **Fecha en fuente**: leída directamente de una ficha o calendario de la fuente en la última captación. La fecha mostrada coincide con la publicada en esa fuente; no afirmamos que la carrera no pueda modificarse o cancelarse después.
- **Fecha cotejada**: recogida de un catálogo consultado previamente, con fecha de cotejo visible y advertencia de posibles cambios.
- **Modalidad por revisar**: una misma ficha profunda se clasificó de dos maneras y no se atribuye ninguna modalidad sin resolver la discrepancia.

**Las distancias se muestran cuando se recuperan expresamente** del título, de un campo de la ficha fuente o del registro cotejado, con su procedencia. No se deducen kilómetros por nombres como «Media Maratón» ni se ocultan datos solo por carecer de una aprobación editorial posterior. Cuando no se dispone de ellos, la web indica «Distancia no disponible». El filtro de distancia sigue retirado hasta mejorar la cobertura. Nunca inferir fechas, lugares, distancias ni inscripción a partir de la edición de años anteriores.

## Arquitectura

- `index.html`, `assets/styles.css` y `assets/app.js`: interfaz estática, búsqueda, filtros por provincia, mes, modalidad y fuente; paginación de 20 resultados.
- `scripts/captacion.py` y `scripts/captacion_extra.py`: lectura de fuentes autorizadas, con control de dominios y robots.txt.
- `scripts/distancias.py`: extrae únicamente medidas con unidades expresas en el título o en campos de distancia de una ficha.
- `scripts/multifuente.py`: semilla histórica fechada, no equivalente a una consulta en directo. A partir de 30 días requiere reconfirmación.
- `scripts/deduplicacion.py`: combina fichas según nombre, fecha, municipio, distancias y enlaces profundos; registra descartes y discrepancias.
- `scripts/build.py`: genera el directorio `_site/`, fichas individuales, JSON, auditoría, páginas informativas y sitemap.
- `config/site.json`: correo, titularidad y bandera `public_launch` (mantener `false` hasta completar los requisitos de lanzamiento).
- `data/carreras.csv`: datos editoriales locales; en GitHub Actions puede sustituirse por el CSV publicado mediante la variable `SHEET_CSV_URL`. El archivo `data/carreras.json` del repositorio NO representa el calendario desplegado: se genera en el build.

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

## Antes de abrir el sitio a buscadores

Completar la identidad del titular y revisar el aviso legal, privacidad y cookies. Confirmar calidad de las fuentes principales, comprobar enlaces y usabilidad. Solo entonces cambiar `public_launch` a `true`. Las fichas provisionales conservarán `noindex`; el sitemap incluye solo eventos confirmados.

## Limitaciones conocidas

La cobertura provincial no es uniforme. Los lectores dependen del formato de cada fuente y pueden dejar de funcionar. Algunas fichas solo enlazan a calendarios de terceros y no a la inscripción directa. **Una fecha publicada puede variar después**; siempre facilitar el enlace a la fuente para comprobar cambios. Las distancias que solo aparecen en imágenes, PDFs o secciones no estructuradas pueden seguir sin recuperarse automáticamente.
