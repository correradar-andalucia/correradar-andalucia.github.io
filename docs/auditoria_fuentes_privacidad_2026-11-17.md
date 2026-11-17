# CorreRadar Andalucía — auditoría de fuentes y privacidad (17/11/2026)

**Estado: verificación técnica realizada; autorización de reutilización sistemática de las diez fuentes NO acreditada.** Este informe no es un certificado legal.

Una política de privacidad del origen regula datos personales; **no es una licencia para copiar el calendario**. Tampoco una regla robots.txt que permite consultar una página concede derechos de propiedad intelectual ni derechos sobre bases de datos.

## Diez fuentes consultadas automáticamente cada 12 horas

En la ejecución real del 17/11/2026 fueron accesibles las diez fuentes. La programación usa HTTPS, comprueba robots.txt, limita tamaño y frecuencia y extrae solo datos deportivos básicos, sin datos personales de corredores.

| Fuente | Documentación pública comprobada | Valoración actual |
|---|---|---|
| FADME/FADMES | [Aviso legal](https://fadmes.es/aviso-legal/) | **Reserva expresa de derechos**: prohíbe copiar o reproducir contenido sin autorización; evaluar el uso factual puntual y pedir aclaración para extracción sistemática |
| Dorsalchip | [Aviso legal](https://www.dorsalchip.es/avisolegal.aspx) y [condiciones generales](https://www.dorsalchip.es/CondicionesGenerales.aspx) | No consta autorización específica para copiar el catálogo de forma recurrente |
| Cruzando la Meta | [Política de privacidad](https://www.cruzandolameta.es/privacidad/) | Regula datos personales, pero no acredita permiso de reutilización del calendario |
| FAA | [Política de privacidad](https://atletismofaa.es/politica-privacidad/) y reserva de copyright en el pie del portal | No se encontró licencia específica para reutilización recurrente |
| GCC Sport Events | [Aviso legal](https://gccsportevents.es/index.php/component/content/article/aviso-legal?catid=2&format=html&tmpl=component) | No se acreditó autorización de extracción sistemática |
| Runnink | No se localizó una licencia verificable de reutilización del calendario | **Sin permiso comprobado** |
| Gesconchip | [Política de cookies](https://gesconchip.es/politica-cookies/) remite a condiciones de uso y aviso legal | No se verificó permiso específico de extracción |
| Diputación de Granada | [Aviso legal](https://www.dipgra.es/aviso-legal/) | **Reserva expresa sobre textos y bases de datos**; determinadas reproducciones comerciales se restringen. Comprobar la licencia concreta o el régimen de reutilización de datos públicos |
| Diputación de Huelva | [Aviso legal](https://www.diphuelva.es/mas-informacion/aviso-legal-y-politica-de-privacidad/) | Hay referencias a reutilización de la información del portal de transparencia, pero no confirman licencia universal para cualquier sección deportiva |
| Circuito Cordobés | Calendario público de [carreraspopularescordoba.com](https://www.carreraspopularescordoba.com/) | No se pudo verificar licencia específica para extracción recurrente |

**Ninguna de estas diez filas equivale a una autorización plena.** La protección de datos personales de los participantes es una cuestión distinta de los derechos sobre contenidos y bases de datos. Las condiciones pueden cambiar. Se requiere revisión jurídica y aclaración de licencias antes de afirmar conformidad general.

**Global Tempo** sigue fuera de la captación automática: se utilizan únicamente enlaces puntuales y un feed de Google Alerts para detectar páginas indexadas que luego requieren aprobación manual. Sportmaniacs no tiene lector automático. Los directorios externos no son por sí mismos fuentes de permiso.

## Auditoría técnica de privacidad y cookies de visitantes

- El código del sitio tiene HTML, CSS y JavaScript propios, sin analítica, publicidad comportamental, píxeles, vídeos incrustados, iframes ni fuentes externas.
- Los filtros buscan datos en el navegador y no transmiten los términos de búsqueda a CorreRadar ni a las webs de carreras.
- El código no usa document.cookie, localStorage o sessionStorage para seguimiento.
- GitHub Pages registra direcciones IP con fines de seguridad según [su documentación](https://docs.github.com/es/pages/getting-started-with-github-pages/what-is-github-pages). Hace falta revisar las garantías aplicables del proveedor.
- Los correos remitidos voluntariamente al contacto deben tener gestión real de acceso y borrado. Publicar una política no ejecuta esas operaciones.
- Los enlaces a terceros son voluntarios; la web declara la política de referencia no-referrer para evitar transmitir la página de procedencia.
- Sin herramientas de seguimiento no esenciales, no se crea un banner ficticio de cookies. Falta realizar una comprobación de cookies de infraestructura en distintos navegadores y documentarla.
- Los textos legales no deben proclamar una certificación de RGPD/LSSI que no consta.

## Antes del lanzamiento público: pendiente

- [ ] Identificar al responsable y determinar domicilio, NIF y datos del artículo 10 LSSI aplicables.
- [ ] Examinar las condiciones de cada fuente con asesoramiento jurídico; solicitar aclaraciones a FADMES y Diputación de Granada y guardar pruebas de licencias o excepciones aplicables.
- [ ] Comprobar con varios navegadores cookies, almacenamiento y solicitudes de GitHub Pages, y revisar encargos, proveedores y transferencias.
- [ ] Definir protocolo de conservación de correos, eliminación y atención a solicitudes de derechos.
- [ ] Revisar y aprobar expresamente los textos legales.
- [ ] Completar, SOLO tras lo anterior, las variables source_rights_review_complete, hosting_privacy_review_complete, cookie_behavior_review_complete y legal_review_complete en config/site.json. No pasar public_launch a true antes de ello.

## Normativa y documentación

- [LSSI, Ley 34/2002, artículos 10 y 22.2](https://www.boe.es/buscar/act.php?id=BOE-A-2002-13758)
- [Ley 37/2007, reutilización de información del sector público](https://www.boe.es/buscar/act.php?id=BOE-A-2007-19814)
- [Guía de cookies de la AEPD](https://www.aepd.es/guias/guia-cookies.pdf)
- [Derecho de información, AEPD](https://www.aepd.es/derechos-y-deberes/conoce-tus-derechos/derecho-de-informacion)
- [GitHub Pages e IP](https://docs.github.com/es/pages/getting-started-with-github-pages/what-is-github-pages)
