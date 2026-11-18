# Estados de inscripción — 18/11/2026

## Alcance
El calendario diferencia abiertas, cerradas, agotadas, próxima apertura y estado desconocido. El filtro se combina con provincia, mes, modalidad y distancia. La etiqueta se refiere a lo observado en la fuente y **no garantiza una plaza disponible**. Las fichas incluyen fecha de consulta, enlace de evidencia y cierre/apertura si están documentados.

- **Runnink**: el CTA del listado público asociado a la misma URL de ficha identifica el estado. La etiqueta «Inscripciones» se interpreta como vía de inscripción disponible según la convención del listado, no como comprobación de plazas. Una apertura sin año solo se fecha si existe una única interpretación entre el día de consulta y la celebración.
- **FAA**: únicamente las advertencias expresas de agotamiento/cierre junto al nombre.
- **GCC**: fecha y hora de cierre en campos propios de la ficha; solo se indica apertura cuando la ficha muestra la opción de inscripción, indica plazas positivas y el plazo no ha pasado. No se guardan cantidades de plazas.
- Resto de fuentes: desconocido salvo evidencia incorporada en futuras revisiones.

No se añaden solicitudes de red, ni se siguen formularios, ni se descargan datos de atletas. No se modifica Global Tempo ni se amplía la consulta de Gesconchip. El estado se asocia por fecha, nombre, municipio, provincia y modalidad; fechas distintas, identidades ambiguas o fuentes contradictorias no se mezclan. No se conserva el estado desde el calendario previo tras un fallo de la fuente.

La interfaz oculta el estado si han pasado más de un día natural desde el cotejo, y oculta el estado abierto cuando el plazo anunciado termina, usando la hora de Madrid. El vencimiento anunciado no permite inferir automáticamente que se han cerrado definitivamente las inscripciones: podrían existir ampliaciones. La ficha estática indica explícitamente que el estado corresponde a la fecha de la última consulta, no es un indicador en tiempo real.

El informe de auditoría y la cobertura generada indican el número de carreras por estado, los plazos conocidos y los conflictos. Los estados desconocidos no se interpretan como cerrados, y cambiar el estado no es una nueva carrera ni genera un nuevo aviso de carreras.
