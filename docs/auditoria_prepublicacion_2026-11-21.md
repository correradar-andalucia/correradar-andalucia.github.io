# Auditoría integral de preparación para lanzamiento — 21/11/2026

**Proyecto:** CorreRadar Andalucía · **Estado recomendado:** **NO-GO para indexación, monetización o campaña pública**; **GO condicionado para pruebas controladas con el enlace actual**, sin alterar la configuración.
**Alcance:** auditoría técnica/documental y comprobaciones de GitHub. No es certificación legal, auditoría de penetración ni test exhaustivo de accesibilidad. **No se modifica ninguna fuente, permiso, secreto, publicación, indexación ni contador.**

## 1. Evidencia y alcance de la comprobación

- Rama `main` consultada: `fb81130190bc35acf7634cccbb5ab558f16ed116` (PR #70 integrado); [ejecución de publicación #44831305085](https://github.com/correradar-andalucia/correradar-andalucia.github.io/actions/runs/44831305085) del 20/11/2026: `build`, `deploy` y `avisos` concluyeron con éxito, **308 tests correctos**.
- Diario `estado-correradar-continuidad/estado.json`: commit coincidente; ejecución `44831305085`, intento 1, `pendiente:null`, **181 carreras**, SHA-256 `1732c5f65f28eb74671b46836a90feb30cce69cc95fd974cf5b3d0d87b0423ba`. Actions registró Pages `succeed` y comprobación de bytes.
- Control de calidad en logs: **apto**, 181 enlaces, **95 distancias**, **51 horarios**, sin bloqueos; ocho provincias: Almería 12, Cádiz 39, Córdoba 13, Granada 35, Huelva 16, Jaén 11, Málaga 41, Sevilla 14.
- Auditoría de deduplicación: **72 fusiones**, sin conflictos de fechas ni de distancias declarados; no equivale a 72 fichas duplicadas en el calendario. **10/10 lectores** leídos, sin alerta de captación silenciosa. Procedencia de fecha: 153 `fuente`, 27 `catalogo`, 1 `editorial`. No presentar las 181 como carreras aprobadas individualmente.
- `scripts/verificar_salida.py` comprobó 181 fichas, `noindex` de prelanzamiento y control de calidad. Las tareas ordinarias están programadas cada ~12 h.
- **Limitación importante:** no fue posible abrir las páginas de GitHub Pages con el navegador externo disponible en la auditoría. La verificación de publicación deriva de Actions y de su diario confirmado. No se ha ejecutado una auditoría Lighthouse/axe, prueba real de móvil Android, carga/rendimiento extremo, comprobación visual de contraste ni revisión interactiva de cada ficha. Son tareas pendientes, no pruebas superadas.

## 2. Dictamen por área

| Área | Estado | Evidencia | Implicación |
|---|---|---|---|
| CI y despliegue | FAVORABLE | 308 tests, `build/deploy/avisos` correctos | No hay bloqueo técnico observado en el último intento |
| Recuperación/continuidad | FAVORABLE | Pages `succeed`, huella del calendario confirmada, sin intento pendiente | La copia anterior se preserva ante fallos, según código y pruebas |
| Calidad/duplicados | FAVORABLE CON RESERVAS | 181 fichas, 8 provincias, 72 fusiones sin conflictos | No sustituye verificación editorial de cada carrera |
| Completitud | MEJORABLE | 86 sin distancia y 130 sin horario | Revisar datos prioritarios de próximas ediciones sin inventar |
| Móvil y accesibilidad | VALIDACIÓN PARCIAL | CSS adaptable a 860/620 px, `focus-visible`, salto a calendario, etiquetas de filtro, `prefers-reduced-motion`; DOM usa `textContent` | Pendientes pruebas reales de Android, teclado/lector pantalla, contraste, navegación y rendimiento |
| SEO técnico | PREPARADO PARA PRELANZAMIENTO | Metaetiquetas, canonical, `sitemap.xml`, `robots.txt`; salida comprueba `noindex,nofollow`; panel fuera del sitemap | No activar indexación ni Search Console como campaña hasta autorización y requisitos cumplidos |
| Privacidad/legal | **BLOQUEO DE LANZAMIENTO** | `config/site.json`: identidad y email presentes; domicilio legal vacío y revisiones legales/proveedores/cookies incompletas | Resolver según LSSI/RGPD aplicables con revisión del responsable o profesional competente |
| Derechos de fuentes | **BLOQUEO DE LANZAMIENTO** | `config/derechos_fuentes.json`: 10 en `consulta_minima`, ninguna licencia general afirmada; 5 con reservas | Revisar autorización o fundamento aplicable por fuente, volumen acumulativo y régimen de bases de datos |
| Gestión editorial | EN MARCHA | RSS/Google Alerts y Issues; histórica #68 aclarada, #71 de reincorporación | No convertir detección en publicación automática ni cierre indiscriminado |

## 3. Bloqueos P0: antes de abrir a Google y promocionar

### P0.1. Alcance de reutilización de las fuentes

`config/derechos_fuentes.json` registra **reservas expresas** en `fadmes`, `runnink`, `gesconchip` y `dipgra`, y **reserva general** en `faa`. Los otros cinco lectores no tienen licencia general acreditada por ello. **Una reserva de derechos no convierte automáticamente la noticia factual aislada en ilícita**; tampoco el acceso permitido por `robots.txt`, la cita de origen o `noindex` autorizan la extracción recurrente de una base. El art. 133 TRLPI contempla supuestos de extracción/reutilización reiterada de partes no sustanciales que perjudiquen la explotación normal.

Acción recomendada: revisión documentada fuente a fuente y por caso de uso, identificando calendario, campos, frecuencia, profundidad, volumen y condiciones, incluyendo normativa sobre reutilización pública cuando proceda; solicitar aclaración o autorización por escrito allí donde sea necesaria y obtener asesoramiento legal proporcional antes de indexación. Ante objeción fundada o prohibición técnica, no eludirla; evaluar pausar solo esa fuente mediante decisión autorizada. Usar la [incidencia #38](https://github.com/correradar-andalucia/correradar-andalucia.github.io/issues/38) como registro de seguimiento. **No habilitar Global Tempo directo**; Google Alerts continúa solo con revisión editorial.

**Discrepancia documental concreta a corregir:** algunos documentos generales describen el enriquecimiento de distancias como desactivado por defecto, pero en el último log operativo aparece `runnink_detalle` con **12 consultas y 8 distancias recuperadas**; el workflow define `CORRERADAR_DISTANCE_ENRICHMENT` con valor por defecto `yes`. La consulta limitada de Runnink está documentada específicamente en `docs/criterios-fuentes-2026-11-18.md`, pero la descripción general puede inducir a error. Alinear texto y configuración tras valorar derechos; **sin modificar automáticamente los límites**.

Fuentes jurídicas de referencia: [TRLPI art. 133](https://www.boe.es/buscar/act.php?id=BOE-A-1996-8930), [Ley 37/2007](https://www.boe.es/buscar/act.php?id=BOE-A-2007-19814). La comprobación de derechos concreta requiere criterio jurídico aplicado, no se resuelve solo con herramientas.

### P0.2. Aviso legal, titular y datos de contacto exigibles

`config/site.json` tiene `contact_email` y `legal_name` configurados, pero `legal_address` vacío. `scripts/build.py` genera actualmente el texto de domicilio como **pendiente de determinar cuando sea exigible**, y mantiene aviso de revisión legal. Valorar con un profesional si el proyecto entra en los supuestos de la LSSI y cómo satisfacer la información de su art. 10 sin publicar datos personales innecesarios o equivocados. No incorporar un domicilio privado al repositorio público sin una decisión consciente y revisión.

Referencia: [Ley 34/2002, art. 10](https://www.boe.es/buscar/act.php?id=BOE-A-2002-13758). También revisar la información de reclamaciones, contacto, responsable, obligaciones de información y procedimientos de rectificación. El código no es por sí solo un dictamen jurídico.

### P0.3. Revisión de proveedores, privacidad y cookies

La web describe GitHub Pages, GitHub, Gmail y Google Alerts y carece de herramientas propias de analítica y publicidad en el código revisado. Eso **no sustituye** verificar los tratamientos y roles de los proveedores, plazos, transferencias internacionales y cookies reales de alojamiento/navegador. El texto declara expresamente que esa revisión sigue pendiente. Sin analítica o cookies no esenciales, no se debe colocar un banner ficticio; si se añaden después, revisar previamente la necesidad de consentimiento. Referencia: [AEPD, cookies](https://www.aepd.es/preguntas-frecuentes/17-internet-y-redes-sociales/FAQ-1707-importancia-de-las-cookies-en-la-proteccion-de-datos).

**Barrera técnica ya existente:** `scripts/control_calidad.py:check_launch_ready` impide construir una versión con `public_launch:true` si faltan los indicadores de contacto, titular y cuatro revisiones. Actualmente **todos estos indicadores son `false`**: `legal_review_complete`, `source_rights_review_complete`, `hosting_privacy_review_complete`, `cookie_behavior_review_complete`. `public_launch:false` y `monetized:false`. No cambiar ningún flag sin evidencia, autorización y control CI.

## 4. P1: antes de un lanzamiento beta de difusión limitada

1. **Comprobación real en Android:** portada, búsqueda acentuada, filtros provincia/mes/modalidad/distancia, fichas, enlaces externos, botones, rotación, textos con zoom 200 %, navegación teclado/lector pantalla y conexiones lentas. Registrar incidencias con capturas de pantalla voluntarias que no contengan datos sensibles. El CSS demuestra diseño responsive, **no** que la experiencia esté aprobada.
2. **Accesibilidad:** pruebas automáticas y manuales de contraste, navegación por teclado, foco, anunciación dinámica de resultados y controles táctiles. No declarar conformidad WCAG basándose solo en clases `focus-visible` o etiquetas semánticas.
3. **Calidad editorial:** priorizar las **86 fichas sin distancia** y **130 sin hora** por cercanía (30/90 días), y comparar Jaén (11), Almería (12), Córdoba (13) y Sevilla (14) con otras provincias; no perseguir números a costa de precisión.
4. **Gestión de incidencias:** distinguir Issues históricos de publicación de solicitudes pendientes. La #68 documenta una ficha corregida que ya figura en el calendario; #71 es el aviso de la incorporación con datos correctos. No borrar trazabilidad ni asumir entrega de emails. Gestionar la #38 sobre derechos y la #27 sobre Global Tempo. Preparar reglas documentales de cierre y etiquetado, sin cierres masivos automáticos.
5. **Documentación permanente:** `docs/ESTADO_PROYECTO.md` y `docs/HOJA_DE_RUTA.md` aún contienen secciones redactadas antes de integrar PR #70 y alusiones a tareas que ya concluyeron. Añadir una instantánea posterior que no borre el historial y refleje la última publicación efectiva.
6. **Observabilidad externa:** verificar desde navegador externo la portada, `/contacto/`, `/privacidad/`, `/aviso-legal/`, `/cookies/`, `/panel/`, `/robots.txt` y un conjunto de fichas. El panel informa de la última publicación buena, no de fallos posteriores. Preferir el flujo y las alertas ya existentes a duplicar descargas.

## 5. P2: solo después de completar P0/P1 y autorizar lanzamiento

- Preparar checklist de cambio controlado a `public_launch:true` **en PR específico**, tras revisar los flags, sin introducir monetización ni fuentes nuevas.
- Revisar SEO por página: URL canónica, títulos, descripción, sitemap, robots, `noindex`, enlaces internos, datos estructurados y datos de las fichas; contemplar que el sitemap del código actualmente incluye las páginas institucionales y solo las fichas con `confirmada`, por lo que no puede asumirse que incluya 181 fichas. No enviar sitemap/indexación a buscadores todavía.
- Configurar Search Console y posibles herramientas de medición únicamente con política de privacidad/consentimiento y autorización expresos.
- Lanzar primero a un grupo pequeño de usuarios con invitación voluntaria y canal de correcciones, y después a clubes/organizadores. Definir objetivos de calidad por encima del volumen de eventos.
- **No monetizar en la primera versión.**

## 6. Matriz de responsabilidades y decisión

| Trabajo | Puede preparar ChatGPT/Codex | Requiere al responsable |
|---|---|---|
| Diagnósticos, pruebas, informes, PR técnicos | Sí; rama separada y CI | Autorizar integración si hay cambios publicados |
| Verificar eventos nuevos y proponer lote | Sí; fuentes identificadas y trazabilidad | Aprobar o rechazar incorporaciones editoriales |
| Revisión documental de términos | Sí; recopilar texto/URLs y proponer consulta | Decidir solicitudes, aceptación de condiciones y asesoría legal |
| Aviso legal y domicilio | Redactar alternativas con cautelas | Decisión de identidad/datos exigibles, sin divulgar dirección por defecto |
| Activar indexación, nuevas fuentes, monetización | Solo plan y pruebas simuladas | **Autorización expresa** |
| Test de Android/lector pantalla real | Preparar guion y procesar resultados | Breve validación del dispositivo si no hay un laboratorio equivalente |

## 7. Criterios para cambiar el dictamen a GO

- [ ] Documento por fuente con autorización/fundamento/restricción y evaluación del uso agregado, revisado por el responsable o asesor competente.
- [ ] Aviso legal, domicilio/datos exigibles y condiciones de contacto revisados y aprobados.
- [ ] Proveedores, transferencias y comportamiento real de cookies verificados y documentados.
- [ ] Pruebas de Android y accesibilidad sin defectos graves pendientes; resultados registrados.
- [ ] Auditoría de los enlaces y fichas prioritarias, cancelaciones, fechas y municipios contrastados.
- [ ] CI verde; última publicación, continuidad, filtros y avisos correctos sin degradación territorial relevante.
- [ ] Documento de lanzamiento preparado y **autorización expresa del responsable** para habilitar indexación. Cambio por PR, despliegue vigilado y posible reversión.

### Próxima decisión propuesta

Mantener `public_launch:false`. Primero completar **P0.1 revisión de derechos y frecuencia efectiva de Runnink** y **P0.2 datos exigibles en aviso legal**; en paralelo, preparar el guion de prueba Android y la revisión visual real. Esta auditoría es una evaluación de preparación, no una solicitud de aprobación automática del lanzamiento.

**Fuentes de referencia internas:** `AGENTS.md`, `docs/ESTADO_PROYECTO.md`, `docs/MANUAL_OPERATIVO.md`, `docs/DECISIONES.md`, `docs/HOJA_DE_RUTA.md`, `docs/auditoria_fuentes_privacidad_2026-11-17.md`, `docs/criterios-fuentes-2026-11-18.md`, `config/derechos_fuentes.json`, `config/site.json`, `scripts/build.py`, `scripts/control_calidad.py`, `scripts/verificar_salida.py`, `assets/app.js`, `assets/styles.css`, `.github/workflows/publicar.yml`, diario `estado-correradar-continuidad` y logs de Actions indicados arriba.
