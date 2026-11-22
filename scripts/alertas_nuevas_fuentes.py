"""Bandeja de novedades de cuatro fuentes por Google Alerts, sin scraping.

Lee exclusivamente RSS de Google y crea incidencias de revisión en GitHub.
Ni la fecha del aviso ni el título indexado acreditan una edición deportiva.
No abre fichas originales, no modifica el calendario, no guarda extractos.
"""
from datetime import date, timedelta
from hashlib import sha256
from html import unescape
import os
import re
import sys
import unicodedata
from urllib.parse import parse_qs, urlparse
import xml.etree.ElementTree as ET

from alertas_globaltempo import (ROOT, MAX_BYTES, MAX_ENTRIES, read_feed,
                                 parse_timestamp, gh_request, ensure_label)
from notificar_carreras import safe_markdown
from oficiales import official_races

SOURCES={
    "deportime":("DeporTime","DEPORTIME_ALERT_RSS_URL","deportime.es",r"/events/[a-z0-9-]+/?"),
    "croniussport":("CroniusSport","CRONIUSSPORT_ALERT_RSS_URL","inscripciones.croniussport.es",r"/inscripcion/[a-z0-9-]+/?"),
    "cronofinisher":("Cronofinisher","CRONOFINISHER_ALERT_RSS_URL","cronofinisher.com",r"/evento/[a-z0-9-]+/?"),
    "patronato_jaen":("Patronato de Jaén","PATRONATO_JAEN_ALERT_RSS_URL","patronatodeportesjaen.es",r"/(?:events/)?[a-z0-9-]+/?"),
}
LABEL="rss-pendiente"
MARKER="CORRERADAR-RSS-CANDIDATO"
MAX_AGE=30
MAX_NEW=5
RACE=re.compile(r"\b(?:carreras?|trail|cross|cxm|maraton(?:es)?|san silvestre|legua|running|ultra|10k|5k|ocr|canicross)\b")
EXCLUDE=re.compile(r"\b(?:ciclismo|cicloturista|mtb|btt|triatlon|duatlon|natacion|clasificaciones?|resultados?|inscritos|participantes inscritos|victorias?|ganadores?|vencedores?|zona privada|diplomas?|fotografias|galeria)\b")
JAEN_NEWS=re.compile(r"\b(?:inscripcion(?:es)?|dorsales?|presenta(?:n|da|cion)?|anuncia(?:n|do)?|convoca(?:toria)?|celebrara|disputara|reglamento|apertura|plazas)\b")

def norm(value):
    value=unicodedata.normalize("NFKD",str(value or "").casefold())
    return "".join(c for c in value if not unicodedata.combining(c))

def checked_url(url,source):
    """URL profunda, sin fragmentos, credenciales, fichas privadas ni parámetros personales."""
    if not isinstance(url,str) or len(url)>1800 or any(c.isspace() for c in url):
        return ""
    _,_,host,pattern=SOURCES[source]
    try:
        p=urlparse(url)
        if p.scheme!="https" or p.hostname not in (host,"www."+host) or p.port not in (None,443) or p.username or p.password or p.fragment:
            return ""
        if not re.fullmatch(pattern,p.path):
            return ""
        query=parse_qs(p.query,keep_blank_values=True)
        # Solo parámetros conocidos de seguimiento/idioma; los demás pueden
        # seleccionar resultados, formularios, personas o recursos privados.
        if any(k not in ("lang","gclid","fbclid") and not re.fullmatch(r"utm_[a-z_]+",k) for k in query):
            return ""
        slug=p.path.strip("/").split("/")[-1]
        if EXCLUDE.search(norm(slug.replace("-"," "))):
            return ""
        if source=="patronato_jaen" and (not RACE.search(norm(slug.replace("-"," "))) or slug in ("carreras","maraton","cross","trail")):
            return ""
        sem_host="www.cronofinisher.com" if source=="cronofinisher" else host
        return "https://"+sem_host+p.path.rstrip("/")+"/"
    except ValueError:
        return ""

def source_link(url,source):
    canonical=checked_url(url,source)
    if canonical:
        return canonical
    try:
        p=urlparse(url)
        if p.scheme!="https" or p.hostname not in ("google.com","www.google.com") or p.path!="/url" or p.username or p.password or p.port not in (None,443):
            return ""
        query=parse_qs(p.query)
        links=[query[k][0] for k in ("url","q") if len(query.get(k,[]))==1]
        valid={checked_url(x,source) for x in links}
        return next(iter(valid)) if len(valid)==1 and "" not in valid else ""
    except (ValueError,TypeError):
        return ""

def candidate_id(source,url):
    return sha256((source+"|"+url).encode()).hexdigest()[:24]

def parse_feed(xml,source,today=None):
    today=today or date.today()
    if len(xml)>MAX_BYTES or b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
        raise ValueError("Feed no permitido")
    # UTF-16 permitiría ocultar declaraciones de entidades a la comprobación
    # anterior. El RSS de Google usa UTF-8.
    root=ET.fromstring(xml.decode("utf-8-sig"))
    atom="{http://www.w3.org/2005/Atom}"
    if root.tag==atom+"feed":
        entries=root.findall(atom+"entry")
        records=[("".join(x.find(atom+"title").itertext()) if x.find(atom+"title") is not None else "",
                  [a.get("href","") for a in x.findall(atom+"link") if a.get("rel","alternate") in ("alternate","")],
                  x.findtext(atom+"updated") or x.findtext(atom+"published")) for x in entries]
    elif root.tag=="rss":
        entries=root.findall("./channel/item")
        records=[(x.findtext("title",""),[x.findtext("link","")],x.findtext("pubDate")) for x in entries]
    else:
        raise ValueError("Formato RSS/Atom no reconocido")
    if len(entries)>MAX_ENTRIES:
        raise ValueError("Demasiadas entradas")
    found={}
    for raw,links,updated in records:
        title=" ".join(unescape(re.sub(r"<[^>]*>"," ",raw or "")).split())
        plain=norm(title)
        if not 6<=len(title)<=240 or "://" in title or EXCLUDE.search(plain) or not RACE.search(plain):
            continue
        stamp=parse_timestamp(updated)
        if not stamp or stamp>today or (today-stamp).days>MAX_AGE:
            continue
        urls={source_link(x,source) for x in links}
        urls.discard("")
        if len(urls)!=1:
            continue
        url=next(iter(urls))
        # El Patronato publica convocatorias bajo /events/<slug>/ sin verbos
        # de noticia. Solo estas fichas de carreras eluden el filtro JAEN_NEWS.
        # No se sigue la ficha ni se incorpora al calendario sin revisión.
        if source=="patronato_jaen" and not JAEN_NEWS.search(plain) and not urlparse(url).path.startswith("/events/"):
            continue
        key=candidate_id(source,url)
        found[key]={"id":key,"titulo":title[:160],"url":url,"fecha_aviso":stamp.isoformat(),"fuente":source}
    return sorted(found.values(),key=lambda x:(x["fecha_aviso"],x["id"]),reverse=True)

def existing_candidates():
    ids=set()
    for page in range(1,11):
        issues=gh_request("GET",f"/issues?state=all&labels={LABEL}&per_page=100&page={page}")
        if not isinstance(issues,list):
            raise ValueError("Historial de avisos inválido")
        for issue in issues:
            if "pull_request" in issue:
                continue
            for key in re.findall(r"<!-- "+MARKER+r":([0-9a-f]{24}) -->",issue.get("body") or ""):
                ids.add(key)
        if len(issues)<100:
            return ids
    raise ValueError("Historial incompleto; no crear duplicados")

def known_official(source):
    known=set()
    for row in official_races():
        url=checked_url(row.get("fuente"),source)
        if url:
            known.add(candidate_id(source,url))
    return known

def issue_body(c):
    label=SOURCES[c["fuente"]][0]
    return (f"<!-- {MARKER}:{c['id']} -->\n"
            f"**Fuente:** {label}\n\n"
            f"**Título indexado:** {safe_markdown(c['titulo'])}\n\n"
            f"**Enlace para revisión:** <{c['url']}>\n\n"
            f"**Fecha del aviso Google:** {c['fecha_aviso']} (NO es la fecha de la carrera).\n\n"
            "### Comprobaciones antes de incorporar al calendario\n"
            "- [ ] Existe una edición futura y su fecha está acreditada.\n"
            "- [ ] Es una carrera a pie en Andalucía; municipio y provincia comprobados.\n"
            "- [ ] No es una prueba ya registrada, cancelada, ni un resultado antiguo.\n"
            "- [ ] Kilómetros y horario solo si constan para esa edición.\n\n"
            "Este aviso no publica nada automáticamente. Tras revisar, incorporar únicamente "
            "los hechos deportivos y el enlace en el catálogo editorial mediante una revisión "
            "del repositorio, o cerrar si no procede. Mantener la etiqueta rss-pendiente para "
            "evitar avisos repetidos. No añadir datos de participantes.\n")

def detect():
    known=existing_candidates()
    errors=0
    for source,(label,env,_,_) in SOURCES.items():
        try:
            rss=os.environ.get(env,"").strip()
            if not rss:
                print(f"{label}: secreto no configurado ({env})")
                errors+=1
                continue
            xml=read_feed(rss)
            rows=parse_feed(xml,source)
            previous=known|known_official(source)
            created=0
            for c in rows:
                if c["id"] in previous:
                    continue
                if created>=MAX_NEW:
                    break
                gh_request("POST","/issues",{
                    "title":f"Revisar carrera RSS · {label}: "+c["titulo"].replace("@","＠")[:100],
                    "body":issue_body(c),"labels":[LABEL]})
                known.add(c["id"])
                previous.add(c["id"])
                created+=1
            print(f"{label}: RSS leído; {len(rows)} resultados candidatos, {created} avisos nuevos, 0 publicaciones automáticas")
        except Exception:
            # La URL RSS puede ser privada: no imprimir trazas ni valores.
            print(f"{label}: error al procesar RSS o avisos; comprobar configuración y acceso en GitHub")
            errors+=1
    return errors

def main():
    try:
        ensure_label(LABEL,"b8a55c","Novedad RSS por verificar; no se publica automáticamente")
        return 1 if detect() else 0
    except Exception:
        print("Error al preparar historial RSS o etiqueta; no se crean avisos sin comprobación",file=sys.stderr)
        return 1

if __name__=="__main__":
    sys.exit(main())
