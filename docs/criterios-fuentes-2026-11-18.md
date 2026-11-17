# CorreRadar — criterio uniforme de captación y fuentes (18/11/2026)

## Decisión

**No activar el scraping directo de Global Tempo en esta revisión.** Su aviso legal, apartado 8, dice expresamente que la reproducción, utilización, explotación y distribución de contenidos requieren autorización **independientemente de su finalidad**. Esto no convierte automáticamente en protegidos un nombre, fecha o enlace aislado; sí introduce una reserva concreta que hace poco prudente habilitar la descarga sistemática sin aclarar su alcance. Se mantienen **Google Alerts → GitHub Issue → revisión/aceptación editorial → nombre y enlace**, sin recopilar el calendario de la plataforma.

**Mantener las diez consultas mínimas existentes**: ocho proveedores anteriores, FADMES y Diputación de Granada. Ninguna fuente se marca como «autorizada» por el solo hecho de ofrecer hechos públicos, y no se amplían la periodicidad ni los campos. FAA queda desde esta revisión identificada como fuente con reserva de derechos general, que faltaba en el informe operativo.

## Comparación de hechos, riesgos y mecanismos

| Fuente | Qué se comprobó | Diferencia relevante | Tratamiento actual |
|---|---|---|---|
| Global Tempo | [Aviso legal, ap. 8](https://www.global-tempo.com/avisolegal.pdf#page=5): reserva escrita independiente del propósito; plataforma de servicios de inscripción | Reserva muy amplia respecto de reproducción/uso de contenidos; no consta una vía directa negociada ni un feed licenciado | RSS de Google Alerts, enlaces individuales revisados, **no** lector directo |
| Diputación Granada | [Aviso legal, ap. 3](https://www.dipgra.es/aviso-legal/): reserva de textos/bases; prohibición formulada expresamente para reproducción con fines **comerciales** y permiso de copias personales/privadas | Además existe el régimen de reutilización del sector público, [Ley 37/2007](https://www.boe.es/buscar/act.php?id=BOE-A-2007-19814). Ni ser administración ni carecer de monetización concede por sí solo licencia ilimitada al calendario | Lee **una página** de fecha/municipio por actualización, atribuye y enlaza a la sección original |
| FAA — Federación Andaluza Atletismo | [Carreras populares](https://atletismofaa.es/carreraspopulares/): nombres y fechas; pie «todos los derechos reservados». La [política de privacidad](https://atletismofaa.es/politica-privacidad/) no es una licencia | Reserva **general**, no se verificó en la documentación examinada una cláusula específica equivalente a Global Tempo para extraer hechos aislados; no presuponer permiso por esa ausencia | Lee **una página** de datos mínimos y enlaza |
| FADMES | [Aviso legal](https://fadmes.es/aviso-legal/): reserva expresa de reproducción | Similar necesidad de aclaración contractual a Global Tempo para contenido protegido; la lectura de hechos mínimos sigue pendiente de valoración específica | Lee datos factuales mínimos, sin copias de reglamentos, respetando robots |
 
La distinción jurídica clave es **hecho individual vs. contenido de una base de datos protegida y repetición de la consulta**, no empresa vs. institución. [Artículos 133 y 134 TRLPI](https://www.boe.es/buscar/act.php?id=BOE-A-1996-8930): el usuario legítimo puede utilizar determinadas partes no sustanciales, pero la repetición que dañe la explotación normal o los intereses legítimos del fabricante puede estar limitada. Tampoco el valor de `noindex` (CorreRadar es accesible por URL) ni una política de privacidad ajena determinan la licitud de la extracción.

## Controles técnicos que se mantienen

- La captación de las diez fuentes está activa **cada ~12 horas** en modo `consulta_minima`, con `robots.txt`, dominios definidos, límite de HTML, y como máximo 24 fichas de detalle por proveedor y ejecución cuando corresponda. No se activan visitas adicionales de enriquecimiento de distancias por defecto.
- No se importan fotografías, descripciones extensas, reglamentos, listados de inscritos, nombres de atletas, tiempos individuales ni datos personales de corredores. Se publican solo nombre, fecha, localidad, modalidad, distancia/hora cuando consta y enlaces de atribución.
- El registro `config/derechos_fuentes.json` mantiene **10 lectores con estado `consulta_minima`**, sin autorizaciones inventadas; señala la reserva **general** de FAA y las **expresas** de FADMES y Diputación de Granada.
- **Global Tempo** consta como `fuentes_externas.globaltempo`, modo `google_alerts_revision_manual`. El indicador `GLOBALTEMPO_AUTHORIZED=yes` **ya no basta** para conectarse: además se exige en el registro `feed_directo_autorizacion.estado=autorizado`, fecha y referencia documental antes de intentar cualquier conexión. El feed sigue necesitando URL HTTPS/host y, si aplica, token proporcionado por el proveedor. El sistema no certifica jurídicamente esa referencia: hace trazable la decisión humana.
- El proceso de Google Alerts, si tiene su secreto RSS configurado, sigue creando incidencias `gt-pendiente` y exige `gt-aprobar`. No se confunde la fecha del aviso con la fecha de la carrera.

## Pendientes y siguientes decisiones

1. **Global Tempo**: solicitar una aclaración por escrito sobre uso de *solo datos factuales mínimos* (nombre, fecha, municipio, modalidad, distancias y enlace); solicitar si ofrece un feed, API, calendario de organizadores o condiciones de atribución. **No se ha enviado ninguna consulta**. No presupone que el titular pueda prohibir la mera noticia de la celebración de una carrera.
2. **FADMES y FAA**: preguntar, cuando sea útil, por las condiciones de reutilización de fechas y enlaces, distinguiendo textos protegidos y bases de datos.
3. **Diputación de Granada**: localizar licencia de la sección de carreras/campo a través o pedir aclaración sobre aplicación de reutilización del sector público. La autorización general de contenidos comerciales no debe extrapolarse a hechos deportivos públicos ni viceversa.
4. Registrar objeciones, cambios de acceso o impacto sustancial y suspender solo el lector afectado, no las diez fuentes en bloque.
5. Antes de ampliar a un calendario indexado o comercial, revisar con un profesional el derecho de reutilización fuente a fuente.

**Alcance de esta revisión:** evaluación documental y cambios técnicos de gobernanza. No constituye una opinión jurídica vinculante ni una garantía de que la extracción periódica concreta esté exenta de reclamaciones.
