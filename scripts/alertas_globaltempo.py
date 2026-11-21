"""Bandeja editorial Global Tempo: descubrir por Google Alerts RSS, aprobar con GitHub.

No hace NINGUNA petición a Global Tempo. No copia su calendario ni publica
automáticamente candidatos. Solo consume enlaces que un buscador ya indexó;
la aprobación explícita de un responsable permite publicarlos como enlaces
SIN fecha en una sección separada del calendario.

CLI:
  python scripts/alertas_globaltempo.py detectar
  python scripts/alertas_globaltempo.py aprobar
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from html import unescape
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "data" / "globaltempo_enlaces_aprobados.json"
PENDING = "gt-pendiente"
APPROVE = "gt-aprobar"
PUBLISHED = "gt-publicada"
MARKER = "CORRERADAR-GT-CANDIDATO"
MAX_BYTES = 1_000_000
MAX_ENTRIES = 100
MAX_AGE = 45


def event_id(url):
    """Aceptar exclusivamente fichas profundas Global Tempo, no sus listados."""
    if not isinstance(url, str) or any(x.isspace() for x in url):
        return ""
    try:
        p = urlparse(url)
        if (p.scheme != "https" or p.hostname not in
                ("www.global-tempo.com", "global-tempo.com",
                 "gateway.global-tempo.com")
                or p.port not in (None, 443) or p.username or p.password
                or p.fragment or p.path != "/carreras.php"):
            return ""
        query = parse_qs(p.query, keep_blank_values=True, strict_parsing=True)
        if set(query) != {"id"} or len(query["id"]) != 1:
            return ""
        number = query["id"][0]
        return number if re.fullmatch(r"[1-9][0-9]{0,7}", number) else ""
    except ValueError:
        return ""


def source_link(url):
    """Desenvolver solo enlaces Google /url?url= hacia la ficha de inscripción."""
    if not isinstance(url, str):
        return ""
    if event_id(url):
        return url
    try:
        p = urlparse(url)
        if p.scheme != "https" or p.hostname not in ("google.com", "www.google.com"):
            return ""
        if p.path != "/url":
            return ""
        query = parse_qs(p.query)
        for key in ("url", "q"):
            values = query.get(key) or []
            if len(values) == 1 and event_id(values[0]):
                return values[0]
    except ValueError:
        pass
    return ""


def clean_title(value):
    title = unescape(re.sub(r"<[^>]*>", " ", str(value or "")))
    title = " ".join(title.split())
    # No confiar en texto HTML del buscador.
    if (not 6 <= len(title) <= 160 or "://" in title
            or any(ord(ch) < 32 for ch in title)):
        return ""
    title = re.sub(r"\s+[-|·]\s+Global[ -]Tempo\b.*$", "", title, flags=re.I).strip()
    if re.fullmatch(r"Global[ -]Tempo(?:[. :\-]*Cronometraje Profesional)?",title,re.I):
        return ""
    return title if len(title) >= 6 else ""


def alert_feed_url(value):
    """El propio usuario proporciona su URL RSS de Google Alerts."""
    try:
        p = urlparse(str(value or ""))
        if (p.scheme != "https" or p.hostname not in ("www.google.com","google.com")
                or not p.path.startswith("/alerts/feeds/")
                or p.username or p.password or p.fragment or p.port not in (None,443)
                or len(p.geturl()) > 1500):
            raise ValueError("Solo se admite una URL RSS de Google Alerts")
        return p.geturl()
    except ValueError as exc:
        raise ValueError("URL de alerta no válida") from exc


def parse_timestamp(raw):
    raw = str(raw or "").strip()
    if not raw:
        return None
    try:
        from email.utils import parsedate_to_datetime
        when = (parsedate_to_datetime(raw) if "," in raw else
                datetime.fromisoformat(raw.replace("Z","+00:00")))
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return when.date()
    except (ValueError, TypeError, IndexError):
        return None


def parse_feed(xml, today=None, metrics=None):
    """Extraer candidatos de RSS/Atom y, opcionalmente, contar descartes sin datos privados.

    metrics contiene exclusivamente contadores agregados: nunca títulos, URLs,
    tokens del feed ni identificadores de carreras. No realiza más peticiones.
    """
    today = today or date.today()
    if len(xml) > MAX_BYTES or b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
        raise ValueError("Feed demasiado grande o con entidades no permitidas")
    root = ET.fromstring(xml)
    atom = "{http://www.w3.org/2005/Atom}"
    if root.tag == atom+"feed":
        entries = root.findall(atom+"entry")
        if len(entries) > MAX_ENTRIES:
            raise ValueError("Demasiadas entradas en el feed")
        records = []
        for entry in entries:
            title = "".join(entry.find(atom+"title").itertext()) if entry.find(atom+"title") is not None else ""
            link = ""
            for a in entry.findall(atom+"link"):
                if a.get("rel", "alternate") in ("alternate", ""):
                    link = a.get("href", "")
                    if source_link(link):
                        break
            updated = entry.findtext(atom+"updated") or entry.findtext(atom+"published")
            records.append((title, link, updated))
    elif root.tag == "rss":
        entries = root.findall("./channel/item")
        if len(entries) > MAX_ENTRIES:
            raise ValueError("Demasiadas entradas en el feed")
        records = [(entry.findtext("title",""),
                    entry.findtext("link",""),
                    entry.findtext("pubDate","")) for entry in entries]
    else:
        raise ValueError("Formato RSS/Atom no reconocido")
    # Las categorías son mutuamente excluyentes para que las sumas cuadren.
    # El orden de validación solo sirve para clasificar el primer descarte.
    counts = {
        "entradas_rss": len(records),
        "titulo_invalido": 0,
        "enlace_no_admitido": 0,
        "fecha_no_valida": 0,
        "fecha_futura": 0,
        "fecha_antigua": 0,
        "duplicado_en_rss": 0,
        "candidatos_validos": 0,
    }
    found, seen = [], set()
    for title, link, updated in records:
        name = clean_title(title)
        if not name:
            counts["titulo_invalido"] += 1
            continue
        canonical = source_link(link)
        if not canonical:
            counts["enlace_no_admitido"] += 1
            continue
        stamp = parse_timestamp(updated)
        if not stamp:
            counts["fecha_no_valida"] += 1
            continue
        if stamp > today:
            counts["fecha_futura"] += 1
            continue
        if today-stamp > timedelta(days=MAX_AGE):
            counts["fecha_antigua"] += 1
            continue
        key = event_id(canonical)
        if key in seen:
            counts["duplicado_en_rss"] += 1
            continue
        seen.add(key)
        found.append({"id":key,"nombre":name,"url":canonical,
                      "fecha_aviso":stamp.isoformat()})
    counts["candidatos_validos"] = len(found)
    if metrics is not None:
        metrics.update(counts)
    return found


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def read_feed(url):
    address = alert_feed_url(url)
    opener = build_opener(NoRedirect)
    with opener.open(Request(address, headers={
        "User-Agent":"CorreRadarAndalucia/2.0 (+mailto:correradarandalucia@gmail.com)",
        "Accept":"application/atom+xml, application/rss+xml, application/xml, text/xml",
    }), timeout=15) as reply:
        data = reply.read(MAX_BYTES+1)
    if len(data) > MAX_BYTES:
        raise ValueError("Alerta RSS demasiado grande")
    return data


def approved_items(path=FILE):
    if not Path(path).exists():
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("enlaces"), list):
        raise ValueError("Catálogo de enlaces aprobados inválido")
    return data["enlaces"]


def publication_candidates(items):
    """Validación independiente: no mostrar entradas sin URL profunda/identificador único."""
    output, seen = [], set()
    for item in items:
        name = clean_title(item.get("nombre",""))
        url = item.get("url","")
        key = event_id(url)
        if not name or not key:
            raise ValueError("Enlace aprobado inválido: nombre o URL")
        if key in seen:
            raise ValueError("Enlace de inscripción aprobado duplicado: "+key)
        seen.add(key)
        output.append({"nombre":name,"url":url})
    return output


def issue_body(candidate):
    return (f"<!-- {MARKER}:{candidate['id']} -->\n"
            f"**Nombre:** {candidate['nombre']}\n\n"
            f"**Inscripción:** {candidate['url']}\n\n"
            f"**Detectado por:** resultado indexado en Google Alerts, "
            f"aviso del {candidate['fecha_aviso']} (NO es la fecha de la carrera).\n\n"
            "### Revisión editorial obligatoria\n"
            "- [ ] He abierto la ficha y comprobado que la prueba existe y pertenece a una edición actual.\n"
            "- [ ] No hay error evidente, cancelación, duplicado ni actividad ajena a las carreras.\n"
            "- [ ] Entiendo que se mostrará **solo nombre + enlace**, en una sección "
            "separada y **sin fecha confirmada**.\n\n"
            f"**Para aprobar:** marca las comprobaciones y añade la etiqueta "
            f"`{APPROVE}`. La aprobación publicará el enlace sin fecha.\n"
            "**Para descartar:** cierra esta incidencia sin añadir la etiqueta.\n")


def extract_issue(issue):
    """Solo incidencias generadas por el bot; nunca aceptar eventos arbitrarios."""
    if not isinstance(issue, dict) or issue.get("state") != "open":
        raise ValueError("La incidencia no está abierta")
    creator = (issue.get("user") or {}).get("login")
    if creator != "github-actions[bot]":
        raise ValueError("La incidencia no fue creada por el detector")
    labels = {x.get("name") for x in issue.get("labels", []) if isinstance(x,dict)}
    if not {PENDING, APPROVE} <= labels:
        raise ValueError("Faltan las etiquetas de revisión")
    body = issue.get("body") or ""
    marker = re.search(r"<!-- "+MARKER+r":(\d{1,8}) -->", body)
    name = re.search(r"^\*\*Nombre:\*\*\s*(.+)$",body,re.M)
    link = re.search(r"^\*\*Inscripción:\*\*\s*(\S+)$",body,re.M)
    if not marker or not name or not link:
        raise ValueError("Incidencia sin los campos esperados")
    url = link.group(1).strip()
    if event_id(url) != marker.group(1):
        raise ValueError("La URL ya no coincide con el candidato inicial")
    # Al menos las tres comprobaciones de revisión deben estar marcadas.
    if len(re.findall(r"^- \[[xX]\] ",body,re.M)) < 3:
        raise ValueError("Debes marcar las tres comprobaciones antes de aprobar")
    name = clean_title(name.group(1))
    if not name:
        raise ValueError("Nombre inválido")
    return {"nombre":name,"url":url,
            "revision":date.today().isoformat(),
            "issue":issue.get("number")}


def repository():
    raw = os.environ.get("GITHUB_REPOSITORY","")
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+",raw):
        raise ValueError("Repositorio GitHub no indicado")
    return raw


def gh_request(method, path, data=None):
    token = os.environ.get("GH_TOKEN","")
    if not token:
        raise ValueError("Falta GH_TOKEN de GitHub Actions")
    address="https://api.github.com/repos/"+repository()+path
    body=json.dumps(data,ensure_ascii=False).encode("utf-8") if data is not None else None
    req=Request(address,data=body,method=method,headers={
        "Authorization":"Bearer "+token,
        "Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28",
        "User-Agent":"CorreRadar-GT-Editorial/1.0",
        **({"Content-Type":"application/json"} if body is not None else {}),
    })
    with urlopen(req, timeout=15) as reply:
        data=reply.read(1_000_001)
    if len(data)>1_000_000:
        raise ValueError("Respuesta GitHub demasiado grande")
    return json.loads(data) if data else {}


def ensure_label(name, color, description):
    try:
        gh_request("POST","/labels",
                   {"name":name,"color":color,"description":description})
    except HTTPError as exc:
        if exc.code != 422:
            raise


def existing_candidates():
    ids=set()
    for page in range(1,11):
        issues=gh_request("GET",f"/issues?state=all&labels={PENDING}&per_page=100&page={page}")
        if not isinstance(issues,list):
            raise ValueError("Respuesta de incidencias inválida")
        for issue in issues:
            marker=re.search(r"<!-- "+MARKER+r":(\d{1,8}) -->", issue.get("body") or "")
            if marker:
                ids.add(marker.group(1))
        if len(issues)<100:
            return ids
    raise ValueError("Demasiadas incidencias sin paginar completamente")


def detect():
    # Crear las etiquetas de revisión aunque todavía no haya RSS ni candidatos.
    # Así el enlace de GitHub Issues no devuelve "Invalid value for label".
    ensure_label(PENDING,"b8a55c","Candidato encontrado en buscador; requiere revisión")
    ensure_label(APPROVE,"20864c","Revisión manual realizada; publicar solo nombre y enlace")
    ensure_label(PUBLISHED,"196eae","Enlace revisado y publicado")
    rss=os.environ.get("GT_ALERT_RSS_URL","").strip()
    if not rss:
        print("Global Tempo: detector preparado, pendiente configurar Google Alerts RSS")
        return
    try:
        alert=read_feed(rss)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        # La URL de Google Alerts puede incluir un token en su ruta:
        # NUNCA escribirla en los logs, ni siquiera al fallar HTTP.
        raise ValueError("No se pudo obtener el RSS de Google Alerts; "
                         "comprobar la URL secreta en GitHub") from None
    # Solo métricas numéricas: los registros de Actions son públicos en este repo.
    metrics={}
    candidates=parse_feed(alert,metrics=metrics)
    known=existing_candidates()
    known.update(event_id(row.get("url","")) for row in approved_items())
    # Enlaces ya cotejados anteriormente: no crear incidencias repetidas.
    historic=ROOT/"data"/"fichas_globaltempo_2026-11-17.json"
    if historic.exists():
        data=json.loads(historic.read_text(encoding="utf-8"))
        known.update(event_id(row.get("fuente","")) for row in data.get("carreras",[]))
    created=0
    already_known=0
    limit_skipped=0
    for c in candidates:
        if c["id"] in known:
            already_known+=1
            continue
        if created >= 20:
            limit_skipped+=1
            continue
        gh_request("POST","/issues",{
            "title":"Revisar inscripción GT: "+c["nombre"][:110],
            "body":issue_body(c),
            "labels":[PENDING]})
        known.add(c["id"])
        created+=1
    metrics.update({
        "ya_conocidos": already_known,
        "aplazados_por_limite": limit_skipped,
        "incidencias_nuevas": created,
        "publicaciones_automaticas": 0,
    })
    # Nunca incluir RSS, títulos, URLs, IDs o respuestas del buscador en logs.
    print("Global Tempo: diagnóstico RSS "+json.dumps(
        metrics,ensure_ascii=False,sort_keys=True))
    print(f"Global Tempo: {len(candidates)} resultados RSS relevantes, "
          f"{created} incidencias nuevas, 0 publicaciones automáticas")


def approve():
    event_path=os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        raise ValueError("Falta evento de aprobación GitHub")
    event=json.loads(Path(event_path).read_text(encoding="utf-8"))
    if event.get("action")!="labeled" or (event.get("label") or {}).get("name")!=APPROVE:
        raise ValueError("Este evento no es una aprobación")
    record=extract_issue(event.get("issue"))
    items=approved_items()
    publication_candidates(items)
    if any(event_id(x["url"])==event_id(record["url"]) for x in items):
        print("Enlace ya publicado; no duplicar")
        return
    items.append(record)
    publication_candidates(items)
    FILE.write_text(json.dumps({"enlaces":items},ensure_ascii=False,indent=2)+"\n",
                    encoding="utf-8")
    print(f"Aprobado manualmente: enlace #{event_id(record['url'])}; "
          "pendiente de publicar con el despliegue de Pages")


def main():
    command=sys.argv[1] if len(sys.argv)>1 else ""
    if command=="detectar":
        detect()
    elif command=="aprobar":
        approve()
    else:
        raise ValueError("Uso: alertas_globaltempo.py detectar|aprobar")


if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR de revisión Global Tempo: {exc}",file=sys.stderr)
        sys.exit(1)
