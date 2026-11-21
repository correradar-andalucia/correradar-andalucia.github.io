# Sprint exprés de preparación de la beta · 21–22/11/2026

**Fecha de análisis:** 21/11/2026 (Europe/Madrid). **Estado:** auditoría ejecutada; **preparación de beta, NO autorización de difusión general o indexación**. Ningún lector, carrera, permiso, secreto, indicador legal ni ajuste de publicación cambia por este documento.

## Objetivo y decisión de alcance

Entregar este fin de semana una primera beta estable para uso controlado **a través del enlace ya público**, congelando funcionalidades nuevas. No supeditarla a aumentar el número de eventos, perfeccionar Google Alerts ni automatizar modificaciones de inscripciones. No usar esta auditoría como licencia para reutilizar contenido ni como confirmación jurídica. Para una campaña pública o indexación, completar las puertas legales/documentadas.

**No confundir:** el sitio en GitHub Pages ya es accesible públicamente aunque lleve `noindex`; una beta por enlace no es privada ni está exenta de obligaciones jurídicas.

## 1. Evidencia técnica comprobada

- `main` al iniciar: `eafd84219513c285c214c3eda43e54a023f1133e` (PR #75 integrado).
- [Ejecución de publicación #44882176383](https://github.com/correradar-andalucia/correradar-andalucia.github.io/actions/runs/44882176383): `build`, `deploy`, `avisos` correctos; 312 tests; 181 carreras, 95 distancias, 51 horarios, 10/10 fuentes directas leídas, 72 duplicados fusionados, sin conflictos de fecha/distancia y `bloqueos=[]`, `avisos=[]`. No se enviaron notificaciones de alta porque no se detectaron nuevas carreras.
- Rama `estado-correradar-continuidad`, `estado.json`: commit `eafd842`, ejecución `44882176383`, `pendiente:null` y calendario confirmado con 181 fichas; Página confirmada por Actions y SHA-256. La última salida se usa **como fotografía de ese despliegue**, no como inventario inmóvil.
- Inspección offline del artefacto `github-pages-1` (ID `14697583701`) de esa ejecución: **181 páginas de fichas**, 181 `slug` únicos, fechas entre 21/11/2026 y 16/10/2027. Todas contienen fecha, título, localidad, provincia y enlace. Provincias: Almería 12, Cádiz 39, Córdoba 13, Granada 35, Huelva 16, Jaén 11, Málaga 41 y Sevilla 14.
- Comprobación estática de enlaces locales `href/src` de todas las páginas HTML del artefacto: **1.947 referencias internas evaluadas, 0 destinos locales ausentes** (recursos externos no comprobados).
- En el artefacto existen `/`, `/panel/`, `/contacto/`, `/aviso-legal/`, `/privacidad/`, `/cookies/` y las fichas. La portada y páginas legales incorporan `noindex,nofollow`; `robots.txt` y sitemap existen. En las cinco páginas públicas principales inspeccionadas no se encontraron scripts externos de analítica ni formularios de terceros. **Esto no prueba** ausencia de cookies técnicas del hosting.
- **Limitación de revisión visual:** la herramienta de navegación externa no pudo acceder a GitHub Pages; un intento de prueba local de Chromium con servidor HTTP fue bloqueado por la política de red de este entorno (`net::ERR_BLOCKED_BY_ADMINISTRATOR`). No se realizó una prueba interactiva real en Android, ni se certifica WCAG; las comprobaciones estáticas y CI no las sustituyen.

## 2. Auditoría agregada de procedencia: 181 fichas

Base: campo `fuentes_origen` del JSON publicado y riesgos registrados en `config/derechos_fuentes.json`. La pertenencia a una fuente **no demuestra** extracción de datos protegidos ni que una carrera no tenga evidencia externa no vinculada en ese campo. El total de menciones por fuente puede superar 181 por fichas multifuente.

| Fuente/categoría en `fuentes_origen` | Fichas que la mencionan | Fichas con esa fuente como única referencia en el campo |
|---|---:|---:|
| FADMES · reserva expresa registrada | 21 | 17 |
| Gesconchip · reserva expresa registrada | 19 | 19 |
| Runnink · reserva expresa registrada | 15 | 15 |
| Diputación de Granada · reserva expresa registrada | 10 | 10 |
| FAA · reserva general registrada | 28 | 27 |
| Dorsalchip | 25 | 23 |
| Cruzando la Meta | 9 | 9 |
| GCC | 3 | 2 |
| Circuito Córdoba | 6 | 2 |
| Diputación de Huelva | 2 | 1 |
| Categoría editorial `oficial` (NO licencia acreditada) | 50 | 39 |
| `globaltempo` (cotejos o históricos; no lectura directa) | 7 | 0 |
| `rockthesport` | 1 | 1 |

**Agrupaciones prioritarias (sin contar una ficha dos veces):**

- FADMES + Gesconchip + Runnink: **55 fichas mencionan al menos una**, **51** no muestran otra categoría ajena a estas tres en `fuentes_origen`; **4** sí tienen otra fuente registrada.
- Las cinco fuentes con reservas documentadas (anteriores + Diputación de Granada + FAA): **93 fichas mencionan al menos una**, **88** sin otra fuente fuera de ese conjunto, **5** con fuente adicional fuera del conjunto.
- **1 ficha** carece de `fuentes_origen` a pesar de tener enlace y cotejo editorial: es un **hueco de trazabilidad**, no una ficha sin fuente pública. Revisión a proponer por separado, sin modificar esta edición en este sprint.
- **165** fichas tienen una fuente en ese campo, **15** varias y **1** ninguna. La procedencia declarada de la fecha es `fuente` en 153, `catalogo` en 27 y `editorial` en 1. Únicamente 1 ficha tiene `confirmada:true`; esto **no** implica que las otras 180 estén canceladas o que sus fechas sean falsas: es un indicador del método y grado de validación.
- Las 51/88 son **colas de revisión editorial prioritaria**, no conteos de carreras ilícitas ni instrucciones de retirada. No se han eliminado fichas ni alterado lectores.

**Cómo repetir offline:** `python scripts/auditar_prebeta.py /ruta/al/artefacto/carreras.json` (registro de derechos de `main` por defecto; también `--derechos`). Solo procesa archivos locales, emite estadísticas sin nombres/URLs de carreras, no descarga fuentes ni cambia configuraciones. Pruebas sintéticas en `tests/test_auditar_prebeta.py`. Ejecutar sobre la copia confirmada, no sobre datos simulados si se comunican cifras reales.

## 3. Requisitos legales y derechos no resueltos

En `config/site.json`:
- `holder_type=persona_fisica`; `legal_name` y `contact_email` configurados; **`legal_address` vacío**.
- `public_launch:false`, `monetized:false`.
- `legal_review_complete:false`, `source_rights_review_complete:false`, `hosting_privacy_review_complete:false`, `cookie_behavior_review_complete:false`.

**P0-A · Reutilización de fuentes:** cinco con reservas registradas, cinco adicionales sin licencia general acreditada por el mero hecho de poder acceder. El criterio `consulta_minima` es una política técnica limitada, **no autorización**. Revisar caso, alcance y repetición; aclarar con responsables o asesoría profesional el fundamento concreto para el uso público. Las consultas formales a FADMES, Gesconchip y Runnink **tienen texto aprobado pero no se han enviado**. No afirmar que el silencio equivale a permiso. Seguir [incidencia #38](https://github.com/correradar-andalucia/correradar-andalucia.github.io/issues/38) y la [matriz P0](revision_p0_derechos_identificacion_2026-11-21.md).

**P0-B · Identificación del titular:** definir si se aplica la LSSI y, si se aplica, resolver la dirección/datos exigibles mediante una vía adecuada y revisada. No exigir ni guardar en GitHub direcciones privadas ni datos sensibles antes de decidirlo. La existencia de email y nombre no acredita por sí sola cumplimiento del artículo 10. Fuente: [LSSI, art. 10](https://www.boe.es/eli/es/l/2002/07/11/34/con).

**P0-C · Privacidad/hosting/cookies:** revisar la documentación real del proveedor, responsabilidades de datos y transferencias internacionales que correspondan, y probar cookies/almacenamiento desde navegador; sin insertar un banner ficticio ni afirmar que la ausencia de analítica equivale a ausencia de tratamientos. No modificar indicadores sin evidencia.

**Límite legal:** [TRLPI, arts. 133 y ss.](https://www.boe.es/eli/es/rdlg/1996/04/12/1/con): el alcance de la extracción/reutilización de bases requiere análisis por caso, también cuando se realizan lecturas repetidas de partes pequeñas. Esta auditoría técnica no es un dictamen jurídico.

## 4. Decisión para el domingo 22/11

| Puerta | Estado actual | Acción mínima |
|---|---|---|
| Despliegue y continuidad | **Apto según Actions** | Comprobar nueva ejecución solo si cambia `main` o se publica un PR |
| 181 fichas, enlaces internos y provincias | **Apto en control estático; reservas de procedencia** | No añadir ni retirar; priorizar la revisión de las 51 fichas que dependen de tres fuentes y decidir cualquier intervención explícitamente |
| Dispositivo móvil y enlaces externos | **Pendiente** | Un recorrido real breve por portada, filtros, ficha, enlaces y páginas legales en Android/otro navegador |
| Derechos/fundamento por fuente | **Pendiente / condiciona difusión** | Resolución documentada por titular/asesoría; si resulta necesario excluir una fuente, requiere aprobación expresa y PR |
| Aviso legal, tratamiento de datos, cookies | **Pendiente / condiciona difusión** | Validar datos exigibles y políticas; no marcar revisiones `true` unilateralmente |
| Indexación, campañas, monetización | **NO autorizado** | Permanecen desactivadas |

**Criterio de cierre del sprint:** PR auditado con CI verde, diagnóstico disponible, lista corta de decisiones, congelación técnica respetada. Eso **no equivale** al GO jurídico de difusión general. Si los P0 siguen sin resolverse, mantener la beta **enlace solo, sin campaña**, hasta autorización y evidencia; la URL pública no se considera privada.

### Guion de 10 minutos para una prueba real Android

1. Abrir [portada](https://correradar-andalucia.github.io/) y comprobar que carga, muestra carreras y no hay desplazamiento horizontal.
2. Buscar una palabra con acento; filtrar por provincia, mes, modalidad y distancia; limpiar filtros.
3. Abrir una ficha de carrera y comprobar texto, fecha, localidad y enlaces a la fuente sin datos inventados. No inscribirse ni enviar formularios.
4. Abrir [contacto](https://correradar-andalucia.github.io/contacto/), [aviso legal](https://correradar-andalucia.github.io/aviso-legal/), [privacidad](https://correradar-andalucia.github.io/privacidad/) y [cookies](https://correradar-andalucia.github.io/cookies/).
5. Comprobar legibilidad con tamaño de texto aumentado y, desde ajustes del navegador, si aparecen cookies/almacenamiento del sitio; registrar hechos, no asumir un resultado.
6. En caso de error, registrar URL concreta, navegador y comportamiento, sin capturas ni datos privados innecesarios.

### Cambios excluidos expresamente del sprint

Ninguna nueva fuente ni lector; sin consulta directa a Global Tempo; sin edición de `config/derechos_fuentes.json`, `config/site.json` o secretos; sin retirada/incorporación de carreras; sin cambios de `robots.txt`, `noindex`, permisos o monetización; sin cierre de Issues editoriales ni envío de correos. Evitar que la urgencia del fin de semana se interprete como autorización de esas acciones.
