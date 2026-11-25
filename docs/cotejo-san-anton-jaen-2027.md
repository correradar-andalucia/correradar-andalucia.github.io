# XLIV Noche de San Antón (Jaén) — propuesta editorial, NO publicable

**Revisión:** 22/11/2026 (Europe/Madrid)  
**Estado:** cotejo iniciado; aún falta reglamento de 2027 y aprobación editorial.  
**Incidencia:** [#78](https://github.com/correradar-andalucia/correradar-andalucia.github.io/issues/78).  
**Archivo estructurado:** [candidato JSON no publicable](candidatos_editoriales/san-anton-jaen-2027.json). Nunca incorporarlo a `scripts/oficiales.py:FILES` sin decisión explícita.

## Hechos y certeza

| Campo | Resultado |
|---|---|
| Nombre | XLIV Carrera Urbana Internacional «Noche de San Antón» |
| Municipio y provincia | Jaén, Jaén |
| Edición | 2027 |
| Fecha | **16/01/2027, prevista en el título de una licitación municipal**; confirmar por reglamento deportivo |
| Modalidad | Carrera a pie (RUNNING) |
| Distancia | **Sin acreditar para 2027** |
| Hora | **Sin acreditar para 2027** |
| Inscripción | **Desconocida** (prerreserva de algunos corredores no equivale a apertura de inscripciones) |
| Publicable | **No**. Cotejo sin aprobación editorial |

### Procedencia

1. [Comunicado del Patronato Municipal de Deportes de Jaén, 10/11/2026](https://patronatodeportesjaen.es/el-ayuntamiento-presenta-la-mejor-media-maraton-de-jaen-de-la-historia-con-motivo-de-su-trigesimo-aniversario/): menciona explícitamente la «San Antón» **2027** y la prerreserva de dorsal para quienes finalicen la Media Maratón de Jaén. **No** atribuir al evento de enero las distancias, horarios, recorridos o cifras de la Media Maratón de noviembre.
2. Expediente municipal **Expd.14/2026/CONM-PMD** para bolsas de participantes: el propio objeto identifica **XLIV Carrera Urbana Internacional Noche de San Antón 2027**, **Jaén, 16/01/2027**. [Entrada que reproduce el título del expediente](https://contratos.gobierto.es/licitaciones/5220778). [Enlace a la Plataforma de Contratación del Sector Público](https://contrataciondelestado.es/wps/poc?idEvl=LO46T48UN296nTs9LZ9RhQ%3D%3D&uri=deeplink%3Adetalle_licitacion): el servidor oficial rechazó la consulta en el entorno de investigación. **La fecha es de documentación contractual, no de reglamento final; puede cambiar**.
3. No se ha encontrado en esta revisión el reglamento deportivo de **2027** que acredite la hora, la distancia exacta, el proceso de inscripción o una posible modificación posterior. **No** emplear reglamento de **2026** para completar esos campos.

### Comprobación de automatización y publicación

- [Detector de cuatro alertas RSS — ejecución 45005367097](https://github.com/correradar-andalucia/correradar-andalucia.github.io/actions/runs/45005367097): finalizada con **success** para commit `4c0b4ffc`. En el paso **real** `python scripts/alertas_nuevas_fuentes.py`: `Patronato de Jaén: RSS leído; 0 resultados candidatos, 0 avisos nuevos, 0 publicaciones automáticas`. En las **pruebas sintéticas** aparecen candidatos simulados; no confundirlos con el resultado real.
- [Publicación de Pages — ejecución 45005367074](https://github.com/correradar-andalucia/correradar-andalucia.github.io/actions/runs/45005367074): `build`, `deploy`, `avisos` **success**. La copia confirmada de `estado-correradar-continuidad/estado.json` del commit `4c0b4ffc` contiene **174 carreras**, `pendiente:null`, sin la Noche de San Antón de Jaén capital. Sí hay carreras distintas: San Antón de **Escañuela** y Canicross **Pinar de San Antón (Cádiz)**.
- La mejora del [PR #79](https://github.com/correradar-andalucia/correradar-andalucia.github.io/pull/79) ha sido integrada: admite `/events/<slug>/` del Patronato en títulos de carreras **si llegan al RSS**, pero **no recupera eventos que Google Alerts no devuelve**.
- La [auditoría de cobertura #81](https://github.com/correradar-andalucia/correradar-andalucia.github.io/pull/81) permite seguir la ausencia desde el **calendario confirmado** sin lectores adicionales.

## Próxima acción editorial

1. Comprobar una ficha/reglamento **del organizador para la edición 2027** y fecha definitiva del 16/01; completar hora y distancia únicamente si constan de forma expresa.
2. Confirmar que no se ha cancelado, trasladado o sustituido la edición y cotejar procedencia y condiciones de reutilización.
3. Comprobar deduplicación **por edición/municipio/provincia**, no solo por palabras «San Antón».
4. Solicitar **autorización editorial explícita** para incorporar la ficha fechada; solo entonces copiar datos mínimos verificados a `data/fichas_oficiales_*.json`, registrar el archivo en la lista explícita `scripts/oficiales.py:FILES`, preparar PR independiente con pruebas y validar despliegue.

Este cotejo **no añade carreras**, **no activa fuentes**, **no abre registros de inscripción**, **no altera robots, permisos o indexación**, y **no cierra la incidencia #78**.
