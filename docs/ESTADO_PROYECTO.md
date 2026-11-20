# Estado de CorreRadar — 20/11/2026

Instantánea del último despliegue comprobado al preparar el traspaso. **No es un contador en vivo.** Consultar [Actions](https://github.com/correradar-andalucia/correradar-andalucia.github.io/actions) y el [panel](https://correradar-andalucia.github.io/panel/) antes de tomar decisiones.

- [Web](https://correradar-andalucia.github.io/), GitHub Pages público con noindex en prelanzamiento; sin analítica ni cuentas de visitantes.
- Repositorio: correradar-andalucia/correradar-andalucia.github.io, rama main.
- PR #61, commit 1e8c0dee9d4fec7a2649202c11b96445458a48ac; CI 246 pruebas correctas; [ejecución 44805527182](https://github.com/correradar-andalucia/correradar-andalucia.github.io/actions/runs/44805527182): build, deploy y avisos correctos.
- 179 carreras, 94 con distancia, 50 con horario, 179 con enlace; diez lectores consultados. Inscripciones: 9 abiertas, 1 agotada, 5 cerradas, 3 próxima apertura, 161 desconocidas; 2 plazos anunciados. Estados correspondientes a aquella generación, no plazas garantizadas.
- Provincias: Almería 10, Cádiz 39, Córdoba 13, Granada 35, Huelva 16, Jaén 11, Málaga 41, Sevilla 14. 71 fusiones de duplicados, sin conflictos informados, 10 carreras con distancia orientativa, 0 recuperadas por respaldo.
- PR #58: cuatro RSS adicionales, primera ejecución 44804249817 correcta; CroniusSport generó #59. PR #61 incorporó la I Media Maratón Vega del Guadalquivir, Alcalá del Río, 10/01/2027 10:00, 21 km anunciados, fuente municipal. El histórico de avisos incluye la edición y #59 está cerrada; no demuestra recepción del email.

## Verificación operativa posterior (20/11/2026)

La ejecución [#44827418106](https://github.com/correradar-andalucia/correradar-andalucia.github.io/actions/runs/44827418106) del commit `4ec20ba` terminó correctamente con 290 pruebas y 179 carreras, 94 distancias y 50 horarios; las diez fuentes directas respondieron y la rama de continuidad guardó la copia confirmada. El nuevo diagnóstico de fuentes señaló **Cruzando la Meta: 18 enlaces, 0 fichas**, sin errores de detalle: aviso de revisión, no fallo de publicación. La corrección está propuesta en PR independiente y no se cuenta como instalada hasta su integración y publicación. Estas cifras son del despliegue fechado, no métricas en vivo.

### Publicación del PR #67 y observación de calidad (20/11/2026)

El despliegue [44828972327](https://github.com/correradar-andalucia/correradar-andalucia.github.io/actions/runs/44828972327), commit `7f447de`, publicó 181 carreras; Cruzando la Meta consultó 18 fichas, aceptó 3 y descartó 15 (7 recintos sin municipio, 7 ubicaciones insuficientes, 1 sin fecha verificable). Hubo 2 altas netas en Almería; la [incidencia #68](https://github.com/correradar-andalucia/correradar-andalucia.github.io/issues/68) recoge el aviso. **Defecto detectado tras desplegar:** `II CXM LA CALZADA 2027` aparece con localidad `Palacio de Deportes de Vícar`, que es un recinto, no un municipio. La mejora pendiente en PR específico debe evitar que se repita y comprobar la siguiente publicación. Diputación de Huelva no pudo verificar robots.txt por un error de red; no consultar ni eludir el bloqueo. La copia confirmada contiene 181 carreras y sigue en vigor hasta un nuevo despliegue válido. No considerar la incidencia resuelta sin verificar la publicación corregida.

## Componentes
- scripts/build.py: catálogo final y artefacto _site; data/carreras.json del repo no es la publicación real.
- scripts/captacion.py y captacion_extra.py: lectores; oficiales.py y data/fichas_oficiales_*.json: cotejos editoriales con lista explícita FILES.
- deduplicacion.py, persistencia.py, distancias.py, estado_inscripciones.py, control_calidad.py, verificar_salida.py: identidad, continuidad, datos y calidad.
- panel.py y assets/panel.css: panel estático con última generación correcta; no monitoriza intentos fallidos posteriores.
- alertas_globaltempo.py, globaltempo_feed.py y alertas_nuevas_fuentes.py: vigilancia editorial y feed GT directo solo tras autorización; notificar_carreras.py: avisos tras desplegar.
- Publicación: /data/carreras.json, /data/estado_fuentes.json, /data/cobertura.json, /data/control_calidad.json, /data/auditoria_duplicados.json, /data/distancias_pendientes.json. Si no son accesibles, usar informes de Actions y declarar el límite.
- Workflows: publicar.yml (cada 12 h, push main y manual); verificar-multifuente.yml (CI); detectar-alertas-globaltempo.yml, detectar-alertas-nuevas-fuentes.yml (cada 12 h), aprobar-enlace-globaltempo.yml. Histórico rama estado-correradar-avisos: no es inventario vivo.

Consultar documentación original para cambios detallados: [continuidad y fuentes](estabilidad-y-nuevas-fuentes-2026-11-18.md), [RSS](alertas-nuevas-fuentes.md), [panel](panel-mantenimiento.md), [inscripciones](estados-inscripciones-2026-11-18.md), [avisos](avisos-carreras-email.md).

## Cambio P0 de continuidad

El cambio de código cubre la referencia compartida entre ambos workflows, el diario de la última copia confirmada y el bloqueo ante falta de referencias válidas. La instantánea de producción de arriba corresponde al despliegue comprobado antes de este cambio. El [manual operativo](MANUAL_OPERATIVO.md#continuidad-de-github-pages) recoge la inicialización, la recuperación y la verificación posterior a la integración.
