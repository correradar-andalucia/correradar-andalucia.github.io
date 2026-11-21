# Plan mínimo de migración a CorreRadar Privado

**Decisión funcional del responsable:** abandonar lanzamiento/indexación pública y convertir CorreRadar en herramienta de **uso personal con acceso autenticado**, conservando la automatización actual. **Estado de este documento: propuesta de diseño, NO migración ejecutada.** Fecha: 21/11/2026 (Europe/Madrid). No autoriza automáticamente ampliar lectores ni suprimir revisiones de derechos.

## 1. Situación real y alcance

- Repositorio `correradar-andalucia/correradar-andalucia.github.io`: público. GitHub Pages actual y `/panel/` son públicos aunque tengan `noindex`. La rama pública `estado-correradar-continuidad` almacena un calendario confirmado. **Una contraseña solo en el frontal no lograría privacidad real**.
- Último despliegue de referencia comprobado: GitHub Actions [44882176383](https://github.com/correradar-andalucia/correradar-andalucia.github.io/actions/runs/44882176383), `eafd842`, 181 fichas, 10/10 fuentes, 312 tests, copia confirmada, 0 avisos nuevos. Son métricas fechadas, no promesa futura.
- El generador `scripts/build.py` fija `BASE` a la URL de GitHub Pages y rechaza otra `config/site.json.site_url`; hay enlaces y metadatos derivados de BASE, así como textos de hosting. Debe actualizarse explícitamente.
- Los workflows `publicar.yml` y `aprobar-enlace-globaltempo.yml` crean artefactos nativos de GitHub Pages y usan `scripts/publicacion.py` para confirmar por API de GitHub Pages **y por descarga HTTP anónima del JSON publicado**. Cambiar solo la URL/host rompería o debilitaría continuidad y avisos.
- El PR [#76](https://github.com/correradar-andalucia/correradar-andalucia.github.io/pull/76) describe una beta pública; la estrategia cambió. Mantenerlo sin integrar hasta revisar si su auditoría offline resulta útil, evitando incorporar un plan de difusión incompatible.

## 2. Arquitectura elegida, sin reescribir la web

**GitHub repository privado** (código, Issues, secretos y rama de continuidad) → **GitHub Actions existentes** (lectores autorizables hoy, compilación, calidad, avisos) → **Cloudflare Pages (Direct Upload desde Actions)** → **Cloudflare Access (política de acceso al único usuario)** → móvil/ordenador con sesión autenticada.

- Se puede usar el subdominio generado `<proyecto>.pages.dev`: no requiere comprar dominio. No inventar ni fijar URL definitiva antes de crear el proyecto.
- Configurar Access **por dirección de correo individual**, no por dominio de correo completo ni «cualquier usuario con OTP». Usar código de un solo uso o identidad externa admitida, y sesión razonable. Proteger **producción `<proyecto>.pages.dev` y todos los previews `*.<proyecto>.pages.dev`**, no solamente previews. Si se añade un dominio personalizado después, protegerlo también.
- Cloudflare Zero Trust Free y Cloudflare Pages Free son opciones potencialmente suficientes para un usuario, sujetas a límites/condiciones del proveedor. Las ejecuciones de Actions **de repositorios privados** consumen cuota del plan GitHub: comprobarla tras el cambio; no prometer coste cero.
- No copiar el JSON, el contenido de las carreras, logs, URL privadas RSS ni tokens a un bucket, repositorio, almacenamiento o nueva ruta públicamente legible.

## 3. Pasos de ejecución con control de acceso

### Fase A — Preparación segura, reversible (sin alterar publicación actual)

1. Conservar copia verificable del calendario confirmado y su SHA-256 desde rama de continuidad/artifact, identificando commit/ejecución. No publicar copias de respaldo.
2. Crear cuenta/proyecto Cloudflare Pages **Direct Upload** con un artefacto **de prueba sin carreras**; habilitar Access solo para el usuario, configurar tanto producción como previews siguiendo las instrucciones específicas de Cloudflare.
3. Probar en incógnito/anónimo que se exige login en `/`, `/panel/`, `/data/carreras.json`, una ruta `/carreras/<slug>/` de prueba y una URL de preview; probar desde Android autenticado. Nunca usar como prueba un simple `noindex`.
4. Crear token de API Cloudflare de alcance mínimo (Pages Edit) y, si se decide verificar bytes a través de Access, un **service token** exclusivo para el workflow. Guardarlos solo como GitHub Actions secrets; nunca en PR, scripts, logs ni documentos. El service token debe tener regla **Service Auth** acotada; no usar `Bypass` general.
5. Antes de pasar a repositorio privado, comprobar integración GitHub/ChatGPT/Codex, permisos del bot y cuota de Actions privada. Verificar si cambiar la visibilidad del repositorio puede alterar Pages, OAuth, webhooks y notificaciones.

### Fase B — PR técnico de sustitución *sin ampliar captación*

1. Parametrizar BASE y URL pública del generador a la nueva `site_url` privada, conservando rutas, funcionalidades, filtros, enlaces al organizador, panel, `noindex` y JSON. Adecuar mensajes de hospedaje público y el texto del panel, sin marcar como finalizadas revisiones legales/cookies sin evidencia.
2. Sustituir SOLO los dos despliegues que hoy usan GitHub Pages (`publicar.yml`, `aprobar-enlace-globaltempo.yml`) por **publicación de `_site` precompilado en Cloudflare Pages**. No cambiar cron de consulta ni autorización por fuente, detección editorial ni semántica del contenido.
3. Adaptar `scripts/publicacion.py` y pruebas de continuidad: el calendario previo proviene del diario **privado y confirmado**; el éxito de Cloudflare y la lectura autenticada de `/data/carreras.json` con coincidencia de identidad y SHA-256 confirman la entrega antes de escribir el nuevo `confirmado` y enviar avisos. Si no se confirma o falla la calidad, mantener el calendario previo y bloquear los avisos/publicación posterior. No consultar JSON público de GitHub Pages.
4. Mantener deduplicación, límites de respaldos, bloqueo ante lecturas sospechosas, vetos editoriales, campos desconocidos vacíos, seguridad RSS/GT y avisos GitHub. Actualizar enlaces internos y de notificaciones que apunten a `github.io`.
5. Ejecutar compilación, pruebas Python y JavaScript y generación `CORRERADAR_FETCH=0`, más pruebas de despliegue fallido, Access inaccesible, JSON alterado, SHA distinto, conservación de versión anterior y reintentos de dos flujos.
6. No habilitar nuevos lectores, feeds GT directos, scraping de fuentes pendientes, monitoreo de inscritos, publicación automática de alertas sin revisión, monetización ni indexación.

### Fase C — Corte y comprobación de privacidad, irreversible sin nueva publicación

1. Tras aprobar explícitamente el PR técnico y configurar secretos, comprobar la primera **publicación autenticada**: datos completos, navegación móvil/PC, `/panel/`, calidad, calendario, fuentes, avisos e integridad del diario. Probar como usuario **y como visitante no autorizado**.
2. En GitHub, **despublicar GitHub Pages antiguo** y desactivar cualquier otra ruta a contenido abierto; comprobar que `https://correradar-andalucia.github.io/`, `/panel/` y `/data/carreras.json` ya no sirven el calendario. La publicación nueva no debe depender del viejo dominio.
3. Cambiar el repositorio **y todas las ramas, Issues, Actions y diario** a privado. Revisar repositorios espejo/forks, artefactos, despliegues antiguos y URLs públicas o caches; privatizar no retira copias que terceros hayan guardado previamente. Revisar nuevamente permisos de conectores y Action workflows.
4. Repetir una **segunda ejecución automática** y verificar que recupere el calendario anterior desde la nueva continuidad privada, compile, despliegue, confirme SHA e informe sin crear duplicados. Comprobar en modo incógnito tanto la URL privada Cloudflare (login requerido) como el viejo sitio GitHub (sin contenido).
5. Solo entonces declarar «privacidad operativa confirmada». Cualquier imposibilidad de verificar Access, la continuidad o el cierre del origen viejo **bloquea el corte**. No borrar primero la única copia funcional.

## 4. Funciones y automatización esperada

| Función | Migración |
|---|---|
| 181 fichas y campos conocidos | Mantener último calendario confirmado como referencia, sin inventar actualizaciones |
| Calendario/filtros/fichas/panel | Mantener HTML/JS actual, variando solo URL y protección |
| Diez lectores directos actuales | Mantener límites, derechos, condiciones y robots; ningún permiso se deduce del uso privado |
| Google Alerts, Global Tempo y 4 RSS | Conservar descubrimiento editorial y no seguir URLs sin habilitación |
| Nuevas carreras y modificaciones | Avisar solo tras comparar **datos fiables y permitidos**. No inferir cancelación por ausencia |
| Dos actualizaciones periódicas | Mantener programación existente con control de calidad y continuidad |
| GitHub Issues/avisos | Mantener en repositorio privado, revisar links al nuevo dominio y correo personal |
| Indexación y marketing | No activar; `public_launch=false`, `monetized=false`, `noindex` |
| Textos legales | Revisar hospedaje real y obligaciones aplicables; no rellenar domicilios ni activar flags sin evidencia |

## 5. Pruebas de aceptación y riesgos

**Aceptación funcional:** el mismo calendario puede abrirse y filtrarse tras login desde Android y PC; panel, fichas, enlaces externos y JSON se sirven en sesión autorizada.

**Aceptación de seguridad:** accesos anónimos a producción, previews, panel, JSON y ficha **no devuelven datos**; GitHub antiguo y ramas de catálogo dejan de estar accesibles sin credenciales; ningún token se imprime. Revisar un navegador sin sesión y una petición HTTP sin cookies.

**Aceptación de continuidad:** dos ejecuciones consecutivas de Actions completan build, deploy y avisos, validan la huella exacta del calendario autenticado; una avería deja la copia anterior y no notifica falsos positivos. Es fundamental no eliminar el mecanismo de continuidad para simplificar.

**Aceptación de derechos:** no se cambia ningún lector ni su profundidad, límites, robots/condiciones o estado de permiso sin autorización diferenciada y evidencia suficiente. La titularidad personal de una herramienta no equivale a licencia para reutilizar bases ajenas.

**Riesgos no eliminados por la migración:** obligaciones que puedan aplicarse a tratamiento de datos y plataformas; posibles copias que ya estuvieran públicamente accesibles; disponibilidad y cambios de servicio Cloudflare; consumo de cuota GitHub privada; pérdida de acceso de integraciones al hacer privado.

## 6. Decisiones necesarias del responsable

1. Crear y conectar personalmente una cuenta Cloudflare/Zero Trust (o autorizar un proveedor equivalente), elegir **el correo exacto permitido** y configurar MFA/OTP; no compartir códigos o credenciales en chat.
2. Autorizar el **cambio de visibilidad a privado** y la **despublicación de GitHub Pages** solo cuando nueva web autenticada, continuidades y backups estén probados. Son acciones de corte con impacto de acceso.
3. Autorizar por separado la integración del PR técnico de migración después de CI. **Este PR documental no contiene código de corte ni lo autoriza automáticamente.**

## Referencias oficiales consultadas (21/11/2026)

- [Cloudflare Pages: Direct Upload desde CI](https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/)
- [Cloudflare Pages: proteger producción y previews con Access](https://developers.cloudflare.com/pages/platform/known-issues/#enable-access-on-your-pagesdev-domain)
- [Cloudflare Access: autenticación por correo OTP](https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/one-time-pin/)
- [GitHub Pages: el repositorio privado no equivale a Pages privado](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [GitHub Pages privado reservado a planes de organización Enterprise Cloud](https://docs.github.com/en/enterprise-cloud@latest/pages/getting-started-with-github-pages/about-privately-published-github-pages-sites)
- [GitHub Actions: coste en repositorios privados según plan](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
