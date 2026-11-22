# Auditoría de cobertura de grandes carreras — 22/11/2026

## Propósito y límites

La investigación editorial [#80](https://github.com/correradar-andalucia/correradar-andalucia.github.io/issues/80) identifica familias de carreras con más de 500 inscritos/participantes **en ediciones históricas documentadas**, en las ocho provincias de Andalucía. No son carreras nuevas aprobadas, ni altas para `scripts/oficiales.py`. Cifras de varias modalidades/edades no deben presentarse como corredores de una distancia concreta. Las cifras aproximadas están identificadas como tales.

- Inventario: `data/prioritarios_carreras.json` (21 familias; nombre, localidad, provincia, alias conservadores, exclusiones, edición histórica, tipo de participación y enlace de evidencia).
- Fuentes para campeonatos: FAA y FADMES, documentadas en el inventario, solo como **referencias de seguimiento**. Un campeonato tiene prioridad independientemente de 500 participantes; copa, circuito, proyecto y campeonato no son equivalentes.
- Auditor: `scripts/auditar_prioritarios.py` cruza inventario con el **`confirmado.calendario` de `estado.json`**, rama `estado-correradar-continuidad`, verificando su SHA-256. **No** usa el archivo vacío `data/carreras.json` de `main`, no consulta páginas ajenas ni altera fichas, indicadores legales o fuentes.
- Workflow: `auditar-cobertura-prioritaria.yml` se ejecuta los lunes a las 08:11 UTC y manualmente. Solo lectura de GitHub; publica el informe en el resumen de Actions y en un artefacto de 30 días, **no** abre incidencias automáticamente ni manda emails, ni despliega GitHub Pages. Antes de integrar el PR, el calendario no ejecutará este workflow.

## Interpretación de los resultados

- `edicion_cubierta`: coincidencia en el municipio, provincia, familia y año de una edición anunciada. No acredita que otros datos, plazas u horarios sigan vigentes.
- `edicion_no_localizada`: edición anunciada que no coincide con una ficha de la copia confirmada. **Pide revisión**, pero no es prueba de que no exista la carrera.
- `otra_edicion_localizada`: hay una ficha de esa familia, pero corresponde a otro año. No sustituye a la edición objetivo.
- `familia_localizada`: hay alguna ficha futura de la familia, pero no consta en el inventario una edición objetivo independiente.
- `sin_ficha_actual`: no hay ficha futura que coincida; **NO** inferir suspensión, cancelación o fallo de captación, particularmente si la edición histórica ya pasó y no se anunció la siguiente.

Se exige coincidencia de **nombre / alias, municipio y provincia**; excluir otras carreras de nombre cercano. La edición objetivo solo se informa si hay evidencia específica de ese año. Una ficha puede existir con un título alternativo o localidad distinta: revisar manualmente antes de declarar fallo. Las cifras históricas no son datos de inscripción vivos.

## Primera comparación exploratoria (copia confirmada 22/11/2026, 01:35:43 UTC)

Se consultó la rama `estado-correradar-continuidad`, cuyo diario muestra 174 fichas y `pendiente:null` para la publicación `44972060384`; la validación automática con SHA-256 queda implementada en el workflow propuesto.

| Clasificación | Familias | Ejemplos |
|---|---:|---|
| Edición objetivo localizada | 2 | Zurich Maratón de Sevilla 2027; Medio Maratón Ciudad de Málaga 2027 |
| Edición anunciada no localizada | 3 | Noche de San Antón Jaén 2027; Media Maratón Córdoba 2026; Snow Running Sierra Nevada 2027 |
| Otra edición localizada | 1 | Medio Maratón de Sevilla (copia contiene edición 2026, inventario vigila 2027) |
| Familia localizada sin objetivo anunciado | 2 | San Silvestre Cordobesa; San Silvestre Onupolis |
| Sin ficha actual de la familia | 13 | No implica carrera ausente para una edición todavía no anunciada |

**Prioridad editorial:** confirmar 2027 San Antón de Jaén mediante fuente de edición oficial y resolver [#78](https://github.com/correradar-andalucia/correradar-andalucia.github.io/issues/78) / [PR #79](https://github.com/correradar-andalucia/correradar-andalucia.github.io/pull/79), que corrige el filtro del RSS preexistente y permanece separado. Para Córdoba/Snow Running, comprobar edición y fuente, sin asumir datos. En la auditoría federativa, distinguir campeonatos oficiales de proyectos de temporada.

## Ejecución manual sin red de fuentes

Desde un checkout de `main`, con el `estado.json` previamente obtenido de la rama de continuidad:

```bash
python scripts/auditar_prioritarios.py \
  --estado /ruta/al/estado.json \
  --salida-json /tmp/cobertura-prioritarios.json \
  --salida-md /tmp/cobertura-prioritarios.md
```

Si la copia no existe, está dañada, o su huella no coincide, el comando **falla sin informe nuevo**. No descargar de nuevo las fuentes para simularlo. Las regresiones están en `tests/test_auditar_prioritarios.py`.

## Decisiones no adoptadas

No se habilita ningún lector directo, Google Alert nuevo ni ampliación de búsquedas. No se toca el flujo de publicación, no se indexa la web y ninguna ficha se crea, modifica, retira o cancela. La mejora del RSS del Patronato está en el PR independiente #79 y necesita validación y autorización antes de integrar.
