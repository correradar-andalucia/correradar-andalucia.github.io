"""Validación de calendarios de Pages y selección de la referencia de continuidad."""
from datetime import date, datetime
from hashlib import sha256
from http.client import HTTPException
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from uuid import uuid4
from urllib.request import HTTPRedirectHandler, Request, build_opener

from control_calidad import MODES, ORIGINS, PROVINCES, valid_source

MAX_CALENDAR = 3_000_000
SCHEMA = 1
PUBLICATION = "publicacion_continuidad"
PAGES_URL = "https://correradar-andalucia.github.io/data/carreras.json"
COMMIT = re.compile(r"[a-f0-9]{40}")
DIGEST = re.compile(r"[a-f0-9]{64}")
RUN_NUMBER = re.compile(r"[1-9][0-9]*")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
UTC_TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")


class ContinuityError(ValueError):
    """Error que debe detener la publicación y explicarse en Actions."""


class HTTPStatusError(ContinuityError):
    def __init__(self, code):
        super().__init__(f"HTTP {code}")
        self.code = code


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_http(url, *, limit, timeout=20, headers=None, data=None):
    request = Request(url, headers=headers or {}, data=data)
    try:
        with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            if response.status not in (200, 201):
                raise HTTPStatusError(response.status)
            raw = response.read(limit + 1)
    except HTTPError as exc:
        raise HTTPStatusError(exc.code) from None
    except (URLError, OSError, HTTPException) as exc:
        raise ContinuityError(f"Error de conexión ({type(exc).__name__})") from None
    if len(raw) > limit:
        raise ContinuityError("Respuesta demasiado grande")
    return raw


def reject_constant(_value):
    raise ValueError("Constante JSON inválida")


def unique_keys(pairs):
    document = {}
    for key, value in pairs:
        if key in document:
            raise ValueError("Clave JSON duplicada")
        document[key] = value
    return document


def decode_json(raw, description):
    try:
        return json.loads(raw.decode("utf-8"), parse_constant=reject_constant, object_pairs_hook=unique_keys)
    except (ValueError, RecursionError):
        raise ContinuityError(f"{description}: JSON inválido") from None


def valid_iso_day(value):
    try:
        return date.fromisoformat(value).isoformat() == value
    except (TypeError, ValueError):
        return False


def matches(pattern, value):
    return isinstance(value, str) and bool(pattern.fullmatch(value))


def check_publication(record):
    if (not isinstance(record, dict) or record.keys() != {"esquema", "commit", "ejecucion", "intento", "fecha"}
            or type(record["esquema"]) is not int or record["esquema"] != SCHEMA
            or not matches(COMMIT, record.get("commit"))
            or not matches(RUN_NUMBER, record.get("ejecucion"))
            or not matches(RUN_NUMBER, record.get("intento"))):
        raise ContinuityError("Metadatos de publicación o versión de esquema inválidos")
    stamp = record.get("fecha")
    try:
        if not matches(UTC_TIMESTAMP, stamp):
            raise ValueError
        datetime.fromisoformat(stamp)
    except ValueError:
        raise ContinuityError("Fecha UTC de publicación inválida") from None
    return record


def parse_calendar(raw):
    if not raw or len(raw) > MAX_CALENDAR:
        raise ContinuityError("Calendario vacío o demasiado grande")
    doc = decode_json(raw, "Calendario")
    if not isinstance(doc, dict) or not isinstance(doc.get("carreras"), list):
        raise ContinuityError("Esquema de calendario inválido (se esperaba una lista de carreras)")
    if not doc["carreras"]:
        raise ContinuityError("Calendario sin carreras")
    try:
        datetime.strptime(doc.get("actualizado"), "%d/%m/%Y")
    except (TypeError, ValueError):
        raise ContinuityError("Calendario sin fecha de actualización válida") from None
    if PUBLICATION in doc:
        check_publication(doc[PUBLICATION])
    slugs = set()
    for index, row in enumerate(doc["carreras"], 1):
        if not isinstance(row, dict):
            raise ContinuityError(f"Carrera {index}: se esperaba un objeto")
        required = ("nombre", "localidad", "provincia", "modalidad", "fecha_origen")
        if (any(not isinstance(row.get(field), str) or not row[field].strip() for field in required)
                or len(row["nombre"]) > 170 or row["provincia"] not in PROVINCES
                or row["modalidad"] not in MODES or row["fecha_origen"] not in ORIGINS
                or not valid_iso_day(row.get("fecha")) or type(row.get("confirmada")) is not bool):
            raise ContinuityError(f"Carrera {index}: identidad, fecha o procedencia inválida")
        # Las fichas editoriales de la hoja pueden carecer de lector y fecha de consulta.
        editorial = row["confirmada"] and row["fecha_origen"] == "editorial"
        origin = row.get("origen", "" if editorial else None)
        if not isinstance(origin, str) or (not editorial and not origin.strip()):
            raise ContinuityError(f"Carrera {index}: falta la procedencia de captación")
        consulted = row.get("consultado", "" if editorial else None)
        if consulted != "" and not valid_iso_day(consulted):
            raise ContinuityError(f"Carrera {index}: fecha de consulta inválida")
        slug = row.get("slug")
        if not matches(SLUG, slug) or slug in slugs:
            raise ContinuityError(f"Carrera {index}: slug inválido o duplicado")
        slugs.add(slug)
        links = (row.get("fuente"), row.get("enlace"))
        if not any(valid_source(link) for link in links) or any(
                url and not valid_source(url)
                for url in (*links, row.get("distancia_fuente"), row.get("hora_fuente"))):
            raise ContinuityError(f"Carrera {index}: enlace de procedencia inválido")
    return doc


def read_calendar(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_CALENDAR + 1)
    return raw, parse_calendar(raw)


def snapshot(raw, publication):
    check_publication(publication)
    doc = parse_calendar(raw)
    if PUBLICATION in doc and doc[PUBLICATION] != publication:
        raise ContinuityError("El origen de la copia no coincide con el calendario")
    return {"publicacion": publication, "sha256": sha256(raw).hexdigest(),
            "calendario": raw.decode("utf-8")}


def verified_snapshot(record):
    if not isinstance(record, dict) or not isinstance(record.get("calendario"), str):
        raise ContinuityError("Falta el calendario de la copia")
    try:
        raw = record["calendario"].encode("utf-8")
    except UnicodeError:
        raise ContinuityError("Contenido de la copia no codificable en UTF-8") from None
    expected = snapshot(raw, record.get("publicacion"))
    if expected["sha256"] != record.get("sha256"):
        raise ContinuityError("La integridad SHA-256 de la copia no coincide")
    return raw


def page_calendar(run_id, attempt, *, timeout=20):
    url = f"{PAGES_URL}?continuidad={run_id}-{attempt}-{uuid4().hex}"
    return read_http(url, limit=MAX_CALENDAR, timeout=timeout,
                     headers={"Cache-Control": "no-cache, no-store", "Accept": "application/json"})


def select_reference(pages, confirmed, log):
    """La copia confirmada también permite detectar respuestas antiguas de la CDN."""
    try:
        raw = pages()
        parse_calendar(raw)
        if confirmed is not None and (not isinstance(confirmed, dict)
                or sha256(raw).hexdigest() != confirmed.get("sha256")):
            raise ContinuityError("El contenido servido no coincide con el último despliegue confirmado")
        log("Referencia elegida: calendario público de GitHub Pages")
        return raw
    except ContinuityError as exc:
        log(f"GitHub Pages descartado: {exc}")
    try:
        if confirmed is None:
            raise ContinuityError("No existe una copia de un despliegue confirmado")
        raw = verified_snapshot(confirmed)
    except ContinuityError as exc:
        log(f"Copia de continuidad descartada: {exc}")
        raise ContinuityError("No hay una referencia válida. Se conserva la última web publicada") from None
    publication = confirmed["publicacion"]
    log(f"Referencia elegida: copia confirmada de ejecución {publication['ejecucion']}, "
        f"intento {publication['intento']}, commit {publication['commit']}")
    return raw
