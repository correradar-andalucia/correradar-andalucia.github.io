# CorreRadar — avisos de carreras nuevas desde GitHub a Gmail

Este método **no utiliza SMTP, contraseñas de aplicación de Gmail ni secretos de correo**. Después de que GitHub Pages se publique correctamente, la tarea `avisos` compara las carreras con la rama `estado-correradar-avisos` y, si aparecen nuevas, crea **una incidencia (Issue)** con nombre, fecha, localidad/provincia, kilómetros disponibles, enlace a la fuente y ficha.

Si entran cinco carreras a la vez, se crea una incidencia con las cinco. Si no hay carreras nuevas, no se crea incidencia. Tampoco se crean incidencias por cambios en distancia, formato, hora o despliegues idénticos. La referencia de las carreras ya conocidas se conserva desde la instalación SMTP anterior: no se pierde el histórico ni se vuelven a notificar carreras antiguas.

## Activar el correo desde GitHub (configuración personal)

1. Inicia sesión en la **cuenta personal de GitHub** cuyo correo deseas que reciba las notificaciones.
2. Abre [CorreRadar en GitHub](https://github.com/correradar-andalucia/correradar-andalucia.github.io) y pulsa **Watch → Custom → Issues**. Evita *All Activity* si solo quieres las incidencias y no toda la actividad del repositorio. Esto puede avisarte también de otras incidencias del proyecto, no exclusivamente de las creadas por CorreRadar.
3. En [GitHub → Settings → Notifications](https://github.com/settings/notifications), habilita **Email** para *Watching* (y *Participating* si te interesa). Revisa en [Emails](https://github.com/settings/emails) que la dirección de Gmail deseada esté verificada y seleccionada como destinataria de notificaciones de GitHub.
4. Revisa en Gmail que los mensajes de `notifications@github.com` no terminen en spam. Puedes crear un filtro por el asunto `CorreRadar:` si deseas distinguirlos de otras notificaciones.
5. Las próximas novedades se crearán como incidencias en [Issues del repositorio](https://github.com/correradar-andalucia/correradar-andalucia.github.io/issues). El workflow se ejecuta aproximadamente cada 12 horas.

**Importante:** GitHub envía el correo de notificación según la configuración de tu cuenta, no el propio código de CorreRadar. No puedo activar la opción Watch ni verificar el correo por ti: requiere tu sesión de GitHub. Crear una incidencia no garantiza que llegue un correo si has desactivado el email, tienes filtros de Gmail o tu organización limita las direcciones receptoras.

## Implementación

- `.github/workflows/publicar.yml`: el trabajo `avisos` se ejecuta **solo tras completar build y deploy**; tiene permisos mínimos `issues:write` y `contents:write` para crear incidencias y actualizar el histórico.
- `scripts/notificar_carreras.py`: calcula el conjunto de carreras nuevas, prepara título/cuerpo de la incidencia y un identificador de lote estable. No accede al correo ni contiene claves.
- La tarea verifica si ya existe una incidencia con ese identificador entre las últimas 1000 incidencias, abiertas o cerradas, para evitar duplicados en reintentos.
- `estado-correradar-avisos`: rama separada, guardada únicamente después de crear o localizar la incidencia. Si falla GitHub al publicar, no marca carreras como avisadas.
- No se interfiere con las diez fuentes ni con el sistema de Google Alerts de Global Tempo. **Los avisos se refieren a carreras efectivamente incorporadas al calendario**, no a entradas pendientes de revisión de Global Tempo.

Las incidencias son visibles porque el repositorio de CorreRadar es público y solo contienen hechos deportivos y URLs ya disponibles en la web. GitHub puede agrupar, retrasar o filtrar algunos correos según sus preferencias; para una comprobación completa, conviene probar con una carrera nueva real.

Documentación oficial: [notificaciones GitHub](https://docs.github.com/en/subscriptions-and-notifications/get-started/configuring-notifications), [crear incidencias desde Actions](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token).
