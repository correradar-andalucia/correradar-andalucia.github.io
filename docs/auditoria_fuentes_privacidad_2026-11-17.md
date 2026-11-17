# CorreRadar Andalucía — revisión técnica de privacidad y condiciones de fuentes

**Revisión documental: 17/11/2026. Responsable del proyecto: Iván Amador Dueñas, persona física.**

**Resultado:** el contenido de privacidad se ha ajustado al código y se ha identificado al responsable. **No se puede certificar cumplimiento jurídico general ni autorización de reutilización de calendarios ajenos.** El lanzamiento público sigue bloqueado, aunque el sitio GitHub Pages de preparación sea accesible mediante su URL.

La **política de privacidad de CorreRadar** se refiere al tratamiento de datos personales de sus visitantes, corresponsales y responsables editoriales. Las **políticas de privacidad de las webs de carreras** explican cómo esas organizaciones tratan los datos de sus propios usuarios y participantes; **no conceden licencias a CorreRadar para copiar sus bases de datos**. `robots.txt` controla una preferencia técnica de rastreo, no derechos de propiedad intelectual. Noindex tampoco proporciona una excepción legal de reutilización.

**Resumen de política aplicada:** la autorización general para reproducir sistemáticamente calendarios completos de las diez fuentes sigue **NO acreditada**; esto no equivale a prohibir el uso mínimo de hechos públicos. El uso recurrente de bases de datos ajenas **no está amparado por licencias generales acreditadas** para estas diez fuentes, pero ello no significa que toda lectura de hechos objetivos y enlaces necesite permiso. Tras la pausa cautelar inicial, `config/derechos_fuentes.json` distingue ocho fuentes en `consulta_minima` y dos pausadas (`fadmes` y `dipgra`) por reservas expresas identificadas. Esto es una decisión de gestión del riesgo, **no una certificación jurídica ni una supuesta autorización**. Referencias: [TRLPI, art. 133](https://www.boe.es/buscar/act.php?id=BOE-A-1996-8930), [Directiva 96/9/CE, arts. 7–8](https://eur-lex.europa.eu/eli/dir/1996/9) y [TJUE, Svensson C-466/12](https://curia.europa.eu/site/upload/docs/application/pdf/2014-02/cp140020es.pdf). Abreviaturas: FADME/FADMES (montaña) y FAA (Federación Andaluza de Atletismo).

## Fuentes automáticas de calendario (10)

La tarea programada aproximadamente cada 12 horas consulta únicamente los ocho lectores en modo de uso mínimo. Su finalidad son los datos objetivos de edición, fecha y enlace, además de lugar/modalidad para desambiguar; ciertas páginas individuales se consultan para confirmar esas circunstancias (máximo 24 por fuente/ejecución), pero **no** para completar distancias adicionales salvo activación específica y revisada. Se controla `robots.txt`, tamaño máximo de HTML, URL del dominio esperado y fecha de la edición; nunca se descargan datos personales de participantes ni textos extensos para publicarlos. FADMES y Diputación de Granada no reciben peticiones del captador mientras sigan en `pendiente`. El permiso para reproducción de contenidos de una fuente no debe confundirse con el uso de un dato factual aislado; siguen siendo posibles riesgos por extracción acumulativa o infracción de términos concretos.

| Fuente (lector) | Documentos públicos y constataciones | Estado de reutilización automatizada |
|---|---|---|
| FADMES (`fadmes`) | [Aviso legal](https://fadmes.es/aviso-legal/): prohíbe la copia o reproducción del contenido, total o parcial, sin autorización expresa. Su política de privacidad se refiere a sus propios usuarios. | **Reserva expresa de derechos.** Falta aclarar si el uso concreto de datos factuales y enlaces puede acogerse a una excepción, acuerdo o licencia. |
| Dorsalchip (`dorsalchip`) | [Aviso y privacidad](https://www.dorsalchip.es/avisolegal.aspx) y [condiciones de inscripción](https://www.dorsalchip.es/CondicionesGenerales.aspx). Se centran en servicios, inscripciones y datos personales. | No se verificó licencia para reextraer su catálogo regularmente. |
| Cruzando la Meta (`cruzandolameta`) | [Política de privacidad](https://www.cruzandolameta.es/privacidad/) relativa a inscripciones y a personas usuarias. | La política no acredita derechos de reutilización recurrente del calendario. |
| Federación Andaluza de Atletismo (`faa`) | [Privacidad](https://atletismofaa.es/politica-privacidad/); el portal contiene una reserva de derechos. | No se verificó licencia específica de reutilización automática. |
| GCC Sport Events (`gcc`) | [Aviso legal identificado en revisión anterior](https://gccsportevents.es/index.php/component/content/article/aviso-legal?catid=2&format=html&tmpl=component). El documento no pudo reabrirse en la revisión externa actual. | **Sin validación actual suficiente.** No presumir permiso. |
| Runnink (`runnink`) | Página de [inscripciones](https://www.runnink.com/inscripciones/) y reglamentos individuales. No se localizó licencia explícita y aplicable a todo el calendario. | Licencia para extracción recurrente **no encontrada**. |
| Gesconchip (`gesconchip`) | [Política de cookies](https://gesconchip.es/politica-cookies/), que remite a condiciones, privacidad y aviso legal. | No se verificó permiso de reutilización del calendario. |
| Diputación de Granada (`dipgra`) | [Aviso legal](https://www.dipgra.es/aviso-legal/): reserva sobre textos y bases de datos; restricciones explícitas de reproducción comercial. | **Reserva de derechos.** Es preciso identificar licencia específica del calendario deportivo o régimen de reutilización del sector público. |
| Diputación de Huelva (`diphuelva`) | [Aviso legal y privacidad](https://www.diphuelva.es/mas-informacion/aviso-legal-y-politica-de-privacidad/). Menciona reutilización del portal de transparencia, no una licencia automática universal del calendario deportivo. | Comprobar condiciones específicas de la sección de deportes. |
| Circuito Cordobés (`circuito_cordoba`) | [Portal y fichas del circuito](https://www.carreraspopularescordoba.com/). No se encontró licencia reutilizable en los documentos examinados. | Autorización de lectura y reutilización recurrente **no acreditada**. |

**Decisión editorial pendiente:** revisar las condiciones específicas y el alcance de uso factual de cada lector. Antes de reactivar las dos fuentes con reserva expresa o de ampliar la captación más allá de hechos mínimos y enlaces, documentar licencia, autorización, régimen de reutilización de información pública aplicable o análisis jurídico específico. Antes de activar la indexación o monetizar, completar la revisión por fuente. En ausencia de base suficiente, considerar suspender el lector afectado y sustituirlo por datos oficiales autorizados o revisiones puntuales lícitas. Es una revisión de propiedad intelectual, bases de datos y condiciones de acceso, además del RGPD. La accesibilidad del sitio, los datos mínimos, robots.txt y los enlaces de atribución son medidas prudentes, pero **no garantizan legalidad**.

## Global Tempo — dos procedimientos distintos

**1. Cotejos manuales anteriores.** `data/fichas_globaltempo_2026-11-17.json` contiene carreras individualmente seleccionadas con datos básicos y enlaces profundos obtenidos en una revisión puntual. Pueden seguir visibles como fichas históricamente cotejadas, identificando fecha de revisión y procedencia. **No existe autorización expresa acreditada**; no se deben presentar como datos certificados por la plataforma ni como permiso para ir reconstruyendo su catálogo por adiciones sistemáticas.

**2. Detección externa + aprobación.** El proceso `scripts/alertas_globaltempo.py` (workflow `detectar-alertas-globaltempo.yml`) consulta **únicamente un RSS de Google Alerts** configurado por el titular, que puede no estar configurado o no indexar las novedades. Extrae de ese aviso un **título y enlace profundo HTTPS** a `global-tempo.com/carreras.php?id=...`, junto con **fecha del aviso**, que NO es fecha de carrera. No descarga automáticamente las fichas de Global Tempo ni sigue redirecciones a ellas. Genera una incidencia de GitHub con etiqueta `gt-pendiente`; **no publica automáticamente**. La persona responsable comprueba la edición, marca tres casillas y añade `gt-aprobar`. Solo entonces se publica **nombre y enlace**, sin fecha, localidad ni datos de atletas, en una sección separada. La incidencia editorial puede ser **pública** porque el repositorio es público. Su finalidad es revisión deportiva: no introducir nombres ni información privada sobre inscritos, teléfonos personales, direcciones o datos de salud.

**3. Conector oficial desactivado.** `scripts/globaltempo_feed.py` solo puede activarse tras permiso explícito y entrega de feed autorizado; no existe todavía URL oficial acordada ni permiso. La política de privacidad no sustituye a esas autorizaciones.

[Global Tempo, aviso legal](https://www.global-tempo.com/avisolegal.pdf), especialmente apartado **8, propiedad intelectual**: exige autorización escrita para determinadas formas de reproducción, utilización y distribución de sus contenidos. Aunque la detección mediante Google Alerts evita visitas periódicas directas a Global Tempo, **el intermediario no transforma automáticamente un eventual uso sistemático de la base en autorizado**. Aplicar las limitaciones españolas sobre extracción sustancial y repetida/sistemática (artículo 133 del TRLPI). Evaluar el volumen y la finalidad de enlaces aprobados; si acabara reconstruyéndose parte significativa del catálogo, solicitar permiso o sustituir el procedimiento.

## Protección de datos de los visitantes y remitentes: comprobación contra el código

- **Responsable:** Iván Amador Dueñas, persona física. Correo público: `correradarandalucia@gmail.com`. La marca CorreRadar no es una sociedad. No publicar DNI, teléfono ni dirección particular sin revisar cuáles son legalmente exigibles.
- **Navegación:** la web estática tiene HTML, CSS, JS propios y carga datos del calendario desde GitHub Pages. La búsqueda/filtrado se efectúa en el navegador. No hay formularios de cuenta, analítica propia, píxeles publicitarios ni listas de participantes.
- **Infraestructura:** [GitHub Pages](https://docs.github.com/es/pages/getting-started-with-github-pages/what-is-github-pages) informa de registro de direcciones IP de visitantes con fines de seguridad; por tanto, no se promete navegación anónima absoluta.
- **Comunicaciones:** las personas que escriben al correo aportan datos voluntariamente, procesados mediante Gmail. Se usan para responder consultas y corregir carreras, no para boletines o publicidad. Pendiente establecer operativamente criterios de revisión y borrado de mensajes y copias.
- **Edición:** GitHub Actions y Google Alerts procesan alertas de eventos. GitHub Issues puede hacer visibles nombres y enlaces deportivos; deben excluirse datos personales o confidenciales que acompañen accidentalmente avisos.
- **Destinatarios y transferencias:** GitHub y Google tienen términos propios. Deben examinarse y documentarse los roles de tratamiento, transferencias fuera del EEE y garantías; no se afirma que esas comprobaciones estén realizadas.
- **Cookies:** no hay `document.cookie`, `localStorage`, `sessionStorage`, analítica, anuncios o incrustaciones externas en el código del visitante. No se ha constatado todavía el comportamiento completo de cookies/seguridad de la infraestructura en varios navegadores: **`cookie_behavior_review_complete=false`**. No inventar un banner de consentimiento mientras no existan cookies no esenciales.
- **Enlaces externos:** la web usa política `no-referrer` para limitar exposición del origen; los registros/inscripciones y sus cookies pertenecen a los terceros después de que el visitante pulse el enlace. CorreRadar no recibe por ello datos de pago o inscripción.
- **Contenido informativo:** la política publicada explica fines, criterio jurídico, contacto, destinatarios, conservación, derechos y AEPD, identifica incertidumbres sobre proveedores; no certifica que todas las obligaciones operativas estén implementadas.

## Tareas pendientes antes de dar conformidad jurídica al lanzamiento

- [x] Identificar como titular persona física a **Iván Amador Dueñas** y actualizar aviso legal y privacidad.
- [ ] Examinar deberes de identificación del artículo 10 LSSI (domicilio, NIF y demás datos según actividad). No se facilitan ni publican datos personales no aportados.
- [ ] Documentar y justificar el derecho de reutilización *por cada fuente*, con prioridad FADMES y Diputación de Granada; el acceso en público no lo concede.
- [ ] Examinar contratos, roles, garantías y transferencias de proveedores (GitHub/Gmail/Google Alerts), y definir la gestión real de datos de correo e incidencias editoriales.
- [ ] Comprobar cookies e infraestructura en varios navegadores y registrar resultado.
- [ ] Aprobar expresamente los textos finales y solicitar revisión jurídica antes del lanzamiento indexable.

No cambiar `public_launch`, `legal_review_complete`, `source_rights_review_complete`, `hosting_privacy_review_complete` ni `cookie_behavior_review_complete` a `true` sin cerrar y documentar sus revisiones. **Noindex** es una medida editorial temporal, no una exención legal.

## Referencias jurídicas y de proveedores

- [Artículos 12 y 133 — TRLPI, derechos sobre bases de datos](https://www.boe.es/buscar/act.php?id=BOE-A-1996-8930)
- [Artículo 13, RGPD; derecho de información — AEPD](https://www.aepd.es/derechos-y-deberes/conoce-tus-derechos/derecho-de-informacion)
- [Artículo 10, LSSI — BOE](https://www.boe.es/buscar/act.php?id=BOE-A-2002-13758)
- [Ley de reutilización de información del sector público](https://www.boe.es/buscar/act.php?id=BOE-A-2007-19814)
- [Guía de cookies — AEPD](https://www.aepd.es/guias/guia-cookies.pdf)
- [GitHub Pages e IP](https://docs.github.com/es/pages/getting-started-with-github-pages/what-is-github-pages)
