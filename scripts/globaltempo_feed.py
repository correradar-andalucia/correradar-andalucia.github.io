"""Global Tempo: adaptador de feed JSON autorizado, nunca scraper de su web.

NO hace solicitudes a Global Tempo mientras GLOBALTEMPO_AUTHORIZED no sea
'yes'. Solo admite un endpoint entregado expresamente por el proveedor con
permiso de reutilización, sin seguir redirecciones y sin datos personales.
"""
from __future__ import annotations

from datetime import date, timedelta
import json
import os
import re
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, build_opener, HTTPRedirectHandler

PROVINCES = {"Almería", "Cádiz", "Córdoba", "Granada",
             "Huelva", "Jaén", "Málaga", "Sevilla"}
MODES = {"RUNNING", "TRAIL", "CROSS", "ULTRA", "OCR",
         "HIBRIDA", "RESISTENCIA", "ESPECIAL", "MIXTA"}
NON_RUNNING = re.compile(
    r"(?i)\b(triatl[oó]n|duatl[oó]n|nataci[oó]n|traves[ií]a a nado|"
    r"senderismo|senderista|pasacalles|cicloturismo|ciclista|"
    r"ciclismo|btt|mtb|mushing|marcha n[oó]rdica)\b"
)
DISTANCE = re.compile(r"\d+(?:[.,]\d+)?\s*(?:km|m)\b", re.I)
HOUR = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
MAX_BYTES = 2_000_000
MAX_EVENTS = 700


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def authorized(env=None):
    env = os.environ if env is None else env
    return env.get("GLOBALTEMPO_AUTHORIZED") == "yes"


def feed_host(url, allowed):
    if not isinstance(url, str) or any(c.isspace() for c in url):
        raise ValueError("Feed: URL inválida")
    parsed = urlparse(url)
    if (parsed.scheme != "https" or not parsed.hostname or
            parsed.username or parsed.password or parsed.fragment or
            parsed.port not in (None, 443)):
        raise ValueError("Feed: requiere HTTPS sin credenciales, puertos especiales ni fragmentos")
    expected = str(allowed).strip().lower()
    if not expected or parsed.hostname.lower() != expected:
        raise ValueError("Feed: host diferente del autorizado")
    return parsed.hostname


def event_url(url):
    """La ficha de evento específica, nunca una portada ni una búsqueda."""
    if not isinstance(url, str) or any(c.isspace() for c in url):
        return False
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.hostname not in
            ("global-tempo.com", "www.global-tempo.com") or
            parsed.username or parsed.password or parsed.fragment or
            parsed.port not in (None, 443) or parsed.path != "/carreras.php"):
        return False
    args = parse_qs(parsed.query, strict_parsing=True)
    return set(args) == {"id"} and len(args["id"]) == 1 and bool(
        re.fullmatch(r"[1-9][0-9]{0,7}", args["id"][0]))


def parse_authorized_feed(document, today=None):
    """Datos mínimos factuales publicados por el proveedor mediante permiso escrito.

    Formato contrato v1:
    {"version":1,"actualizado":"AAAA-MM-DD","eventos":[{
       "edicion_confirmada":true,"fecha":"AAAA-MM-DD","nombre":"...",
       "localidad":"...","provincia":"Granada","modalidad":"RUNNING",
       "distancia":"10 km","hora":"09:00",
       "url":"https://www.global-tempo.com/carreras.php?id=1234"}]}
    Las carreras ambiguas y ajenas se excluyen, no se adivinan datos.
    """
    today = today or date.today()
    if not isinstance(document, dict) or document.get("version") != 1:
        raise ValueError("Feed autorizado: esquema JSON v1 desconocido")
    updated = date.fromisoformat(str(document.get("actualizado", "")))
    if updated > today or (today-updated) > timedelta(days=14):
        raise ValueError("Feed autorizado: sin actualización reciente o con fecha futura")
    events = document.get("eventos")
    if not isinstance(events, list) or len(events) > MAX_EVENTS:
        raise ValueError("Feed autorizado: eventos ausentes o demasiado numerosos")
    valid, skipped, seen = [], 0, set()
    for item in events:
        if not isinstance(item, dict):
            skipped += 1
            continue
        name = str(item.get("nombre") or "").strip()
        city = str(item.get("localidad") or "").strip()
        province = str(item.get("provincia") or "").strip()
        mode = str(item.get("modalidad") or "").strip().upper()
        link = item.get("url")
        # Solo ediciones marcadas como confirmadas en el feed proporcionado
        # por Global Tempo; nunca fechas orientativas, circuitos o listados.
        if (item.get("edicion_confirmada") is not True or
                len(name) < 5 or len(name) > 170 or
                len(city) < 2 or len(city) > 90 or
                province not in PROVINCES or mode not in MODES or
                NON_RUNNING.search(name) or not event_url(link)):
            skipped += 1
            continue
        try:
            day = date.fromisoformat(str(item.get("fecha") or ""))
        except ValueError:
            skipped += 1
            continue
        if day < today or day > today + timedelta(days=550):
            skipped += 1
            continue
        # Contradicciones declaradas por el feed => no publicar.
        if item.get("fecha_reglamento") and item["fecha_reglamento"] != day.isoformat():
            skipped += 1
            continue
        distance = str(item.get("distancia") or "").strip()
        hour = str(item.get("hora") or "").strip()
        if len(distance) > 140 or (distance and not DISTANCE.search(distance)):
            skipped += 1
            continue
        if hour and not HOUR.fullmatch(hour):
            skipped += 1
            continue
        identity = (day.isoformat(), link)
        if identity in seen:
            skipped += 1
            continue
        seen.add(identity)
        valid.append({
            "fecha": day.isoformat(), "nombre": name,
            "localidad": city, "provincia": province,
            "modalidad": mode, "distancia": distance, "hora": hour,
            "enlace": link, "fuente": link,
            "fuente_nombre": "Global Tempo",
            "origen": "globaltempo", "fuente_directa": True,
            "cotejada": updated.isoformat(), "estado": "Edición confirmada en feed autorizado",
            "desnivel": "", "precio": "", "bolsa": "", "track": "",
            **({"distancia_fuente": link} if distance else {})
        })
    return valid, skipped


def fetch_authorized_feed(today=None, env=None):
    """Devuelve carreras y estado sin llamar a la red salvo autorización doble."""
    env = os.environ if env is None else env
    today = today or date.today()
    if not authorized(env):
        return [], {"estado": "sin consulta automática",
                    "motivo": "Pendiente permiso escrito y feed autorizado"}
    address = env.get("GLOBALTEMPO_FEED_URL", "").strip()
    hostname = env.get("GLOBALTEMPO_FEED_HOST", "").strip()
    if not address or not hostname:
        raise ValueError("Feed autorizado sin URL o host acordado")
    feed_host(address, hostname)
    request = Request(address, headers={
        "User-Agent": "CorreRadarAndalucia/2.0 (+mailto:correradarandalucia@gmail.com)",
        "Accept": "application/json",
        **({"Authorization":"Bearer "+env["GLOBALTEMPO_FEED_TOKEN"]}
           if env.get("GLOBALTEMPO_FEED_TOKEN") else {})
    })
    opener = build_opener(NoRedirect)
    with opener.open(request, timeout=15) as response:
        if response.status != 200:
            raise ValueError("El feed autorizado no responde HTTP 200")
        raw = response.read(MAX_BYTES+1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Feed autorizado demasiado grande")
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("El feed autorizado no es JSON válido") from exc
    events, rejected = parse_authorized_feed(data, today)
    return events, {"estado": "leida", "candidatas":len(events),
                    "rechazadas":rejected, "actualizado":data["actualizado"],
                    "url": "feed autorizado (URL privada)"}
