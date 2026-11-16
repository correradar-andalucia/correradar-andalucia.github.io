# CorreRadar Andalucía

Calendario independiente de carreras populares, trail, cross, ultradistancia, obstáculos e híbridas de Andalucía. Proyecto en preparación.

## Principio editorial

**Una fuente leída automáticamente no significa que el organizador haya confirmado la fecha.** El calendario diferencia:

- **Confirmada**: aprobada expresamente en la hoja editorial (columna `Publicar=Sí`), con enlace de fuente y fecha de verificación. En la ficha se muestran los datos adicionales disponibles.
- **Pendiente de confirmación**: obtenida de una fuente directa o del catálogo histórico. Se muestra para ayudar a descubrir eventos, pero la fecha y los detalles deben revisarse en la fuente enlazada. No se muestran distancias ni precios no validados editorialmente.
- **Modalidad por revisar**: una misma ficha profunda se ha clasificado de dos maneras. Se publica una sola entrada sin atribuirle una modalidad fiable.

No se muestran kilómetros como filtro hasta disponer de una cobertura suficiente y verificada. Nunca inferir fechas, lugares, distancias ni inscripción a partir de la edición de años anteriores.

## Arquitectura

- `index.html`, `assets/styles.css` y `assets/app.js`: interfaz estática, búsqueda, filtros por provincia, mes, modalidad y fuente; paginación de 20 resultados.
- `scripts/captacion.py` y `scripts/captacion_extra.py`: lectura de fuentes autorizadas, con control de dominios y robots.txt.
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

La cobertura provincial no es uniforme. Los lectores dependen del formato de cada fuente y pueden dejar de funcionar. Algunas fichas solo enlazan a calendarios de terceros y no a la inscripción directa. **No se debe prometer una plaza, un precio o una fecha que la fuente no confirma.**
