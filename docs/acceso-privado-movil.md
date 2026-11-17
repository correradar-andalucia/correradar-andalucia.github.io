# CorreRadar privado en el móvil — instalación segura

**Estado:** código y actualización automatizada preparados, **alojamiento privado todavía NO activado**. Es imprescindible conectar una cuenta Cloudflare y configurar quién puede entrar. No compartir aquí claves, contraseñas, tokens ni correos de terceros.

## Por qué no usar GitHub Pages como web privada

En el alojamiento actual, GitHub Pages publica el calendario en internet incluso con `noindex`, y un repositorio privado no garantiza que Pages también sea privado. La opción de Pages publicada de forma privada requiere GitHub Enterprise Cloud. Por eso se prepara un **Cloudflare Worker protegido por Cloudflare Access**, que permite la consulta autenticada desde Safari o Chrome en el móvil.

El código `private/worker.mjs` exige **dos verificaciones independientes**: una identidad realmente autenticada por Cloudflare Access y el mismo correo que se configura en el secreto `CORRERADAR_PRIVATE_EMAIL`. Si falta cualquiera, responde 403/503 a **toda página y JSON**. La web generada se incorpora como módulo `private/generated.mjs` (no subido a Git); deliberadamente **no** utiliza `assets.directory`, ya que el router de Assets no traslada `ctx.access` al Worker.

## Activación única (requiere tu intervención en tus propias cuentas)

1. **Cuenta Cloudflare.** Crea/inicia sesión en Cloudflare y prepara el Worker con nombre `correradar-consulta-privada`. Nunca pegues los tokens en mensajes ni en archivos del repositorio.
2. **Primer despliegue cerrado.** Desde una copia local del repositorio con Python y Node disponibles, ejecuta `python scripts/build.py`, `python scripts/verificar_salida.py`, `python scripts/pack_private_worker.py`, y `npx wrangler@4 deploy` tras iniciar sesión con `npx wrangler@4 login`. **Antes de configurar el secreto, el Worker responde 503 y no publica las carreras.** Alternativamente, puedes añadir el token y Account ID en los secretos de GitHub y activar el workflow cuando Access esté listo.
3. **Identidad permitida.** En Cloudflare, añade el secreto del Worker `CORRERADAR_PRIVATE_EMAIL` con **tu correo exacto** (sin publicarlo en Git). Se puede configurar con `npx wrangler@4 secret put CORRERADAR_PRIVATE_EMAIL` desde tu equipo.
4. **Proteger todo el Worker.** En Cloudflare: **Workers & Pages → correradar-consulta-privada → Access → Protect this Worker behind Access → All traffic**. Crea una política **Allow para un solo correo**, nunca *Everyone* ni un dominio general. Si utilizas inicio de sesión por código, activa One-time PIN en **Zero Trust → Integrations → Identity providers**. El Worker seguirá rechazando identidades que no coincidan con el secreto.
5. **Comprobar privacidad.** En una sesión privada del navegador, intentar abrir `/data/carreras.json` debe redirigir al acceso de Cloudflare o responder 403. Tras autenticarte con tu correo, deben funcionar portada, filtros y fichas. Prueba una identidad no autorizada: **no** debe recibir contenido.
6. **Actualizar automáticamente cada 12 horas.** En GitHub → repositorio → Settings → Secrets and variables → Actions, añade los secretos `CLOUDFLARE_API_TOKEN` y `CLOUDFLARE_ACCOUNT_ID` (con permiso mínimo para desplegar Workers). Tras validar Access, crea la variable `PRIVATE_DEPLOY_ENABLED=true`. El workflow `publicar-privado.yml` actualiza el calendario; el workflow original de GitHub Pages se detiene al activar esa variable.
7. **Cerrar la antigua publicación.** En GitHub → Settings → Pages, **unpublish** la web anterior y comprueba que `https://correradar-andalucia.github.io/` ya no sirve carreras. Si quieres privacidad también para el **repositorio y sus datos históricos**, muévelo a un repositorio privado nuevo (el historial público anterior puede seguir accesible por copias o archivos); ni Cloudflare Access ni `noindex` borran publicaciones previas de internet.

## Consultar desde el móvil

Abre la dirección `https://correradar-consulta-privada.<tu-subdominio>.workers.dev/`, inicia sesión con tu correo y código, y usa búsqueda, provincia, mes, modalidad y **distancias múltiples**. En iPhone, Safari → Compartir → Añadir a pantalla de inicio; en Android, Chrome → menú → Añadir a pantalla de inicio. No es necesaria una aplicación descargada ni mantener tu ordenador encendido.

## Fuentes y límites

La versión privada hereda de momento **ocho fuentes automáticas de consulta mínima**. FADMES y Diputación de Granada continúan pendientes de revisar; Global Tempo directo sigue sin conexión hasta contar con acceso adecuado. Que el calendario sea de uso particular **no elimina automáticamente** los derechos sobre bases de datos ni las condiciones de acceso de cada proveedor. No activar todas indiscriminadamente; se pueden ampliar tras revisar fuente por fuente.

## Consideraciones

- No publicar `private/generated.mjs`, `_site/`, tokens, ni secretos. Este archivo generado contiene datos de carreras: se despliega **dentro del Worker**, no como ruta estática.
- Una captura local o sesión iniciada en el móvil puede quedar visible a quien controle el dispositivo: protege el móvil con contraseña/biometría.
- No activar este acceso sin verificar que las peticiones anónimas fallan y el antiguo GitHub Pages está retirado.
- Hasta completar los pasos externos anteriores, **la web privada no está operativa** y la web antigua sigue siendo pública.

Documentación oficial: [Cloudflare Worker Access](https://developers.cloudflare.com/workers/configuration/cloudflare-access/), [código de inicio de sesión](https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/one-time-pin/), [GitHub Pages privado](https://docs.github.com/en/enterprise-cloud@latest/pages/getting-started-with-github-pages/about-privately-published-github-pages-sites).
