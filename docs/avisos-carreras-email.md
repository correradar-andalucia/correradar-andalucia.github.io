# Avisos por correo cuando se publique una carrera nueva

CorreRadar ejecuta su captación y despliegue de GitHub Pages aproximadamente cada 12 horas. Tras **un despliegue exitoso**, el trabajo `avisos` compara las carreras publicadas con el histórico de avisos en la rama `estado-correradar-avisos`.

- **Novedad:** carrera que no aparecía anteriormente (fecha, municipio, provincia y nombre, permitiendo pequeñas rectificaciones).
- **Un solo email por actualización**, con todas las carreras nuevas de esa actualización; no un correo por cada carrera si entran varias simultáneamente.
- **No se avisa** por un simple despliegue, una edición de distancia/hora, un cambio de estilos o un evento que desapareció temporalmente y luego reaparece.
- **Primer despliegue:** crea la referencia inicial con las carreras ya existentes; **no** envía un correo masivo por esas carreras.
- **Si Gmail falla o faltan las credenciales:** no se da por avisada ninguna novedad pendiente. Se vuelve a intentar en el próximo despliegue, lo que puede generar algún reintento duplicado si Gmail envió el mensaje pero GitHub no consiguió guardar el histórico.
- El correo incluye nombre, fecha, municipio, provincia, distancia cuando consta, enlace de origen y enlace a la ficha.
- La captura de fuentes y la alerta de Google Alerts para Global Tempo no cambian. Google Alerts solo crea incidencias editoriales; se avisará de una nueva carrera en el calendario principal **si realmente se incorpora al calendario y se publica**.

## Activar los envíos (una vez)

El destinatario y remitente predeterminados son el correo de contacto configurado en `config/site.json`: `correradarandalucia@gmail.com`.

1. En la cuenta de Gmail que va a enviar los avisos, activa [la verificación en dos pasos](https://support.google.com/accounts/answer/185839) y, si tu cuenta admite esta función, crea una [contraseña de aplicación](https://support.google.com/accounts/answer/185833). **No uses tu contraseña principal ni la compartas por el chat.** Google recomienda OAuth para integraciones modernas y puede no ofrecer contraseñas de aplicación en algunas cuentas.
2. Abre [el repositorio en GitHub](https://github.com/correradar-andalucia/correradar-andalucia.github.io/settings/secrets/actions) → **Settings → Secrets and variables → Actions → Repository secrets → New repository secret**.
3. Añade el secreto **`CARRERAS_SMTP_APP_PASSWORD`** con esa contraseña de aplicación de Gmail. Nunca lo escribas en README, código o incidencias.
4. Si quieres enviar desde otro Gmail distinto al correo público, añade **`CARRERAS_SMTP_USER`** como secreto con su dirección completa, y crea la contraseña de aplicación en esa misma cuenta.
5. Si deseas recibir los avisos en otra dirección, añade **una variable** `CARRERAS_ALERT_EMAIL` con el correo receptor. Si no existe, se usa `correradarandalucia@gmail.com`.
6. Puedes comprobar la siguiente ejecución desde [Actions → Actualizar carreras y publicar web](https://github.com/correradar-andalucia/correradar-andalucia.github.io/actions/workflows/publicar.yml). El trabajo `avisos` se ejecuta **después** de los trabajos `build` y `deploy`.

**No hay que añadir credenciales de Global Tempo.** La lista de carreras notificadas se guarda en una rama separada del repositorio, para evitar que guardar el histórico dispare de nuevo el despliegue de `main`. Las contraseñas no se incluyen en esa rama ni en ningún artefacto.

## Seguridad y límites

La rama de avisos guarda solo nombres, fechas, municipios y enlaces de carreras ya publicados; no datos privados de visitantes ni claves. El trabajo utiliza SMTP cifrado por TLS (puerto 465), con secretos de GitHub Actions. El envío no está activo hasta configurar la contraseña. Si se revoca esa contraseña, los avisos dejan de enviarse sin afectar al calendario.

Este mecanismo envía notificaciones cuando aparecen **nuevas carreras**, no cada vez que cambia un detalle de una ficha existente. Para avisos de modificaciones o cancelaciones habría que ampliar explícitamente las reglas y sus pruebas.
