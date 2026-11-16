"""Fichas cotejadas en organizadores/administraciones; no inventar ediciones.

Son datos fechados, no una lectura en vivo de terceros.
No se marca ninguna como aprobación editorial ("confirmada").
"""
from __future__ import annotations
from datetime import date, timedelta
import json
from pathlib import Path
import re
from urllib.parse import urlparse

FILE = Path(__file__).resolve().parents[1] / "data" / "fichas_oficiales_2026-11-16.json"
MAX_AGE = 30
PROVINCES = {"Almería", "Cádiz", "Córdoba", "Granada",
             "Huelva", "Jaén", "Málaga", "Sevilla"}
MODALITIES = {"RUNNING", "TRAIL", "CROSS", "ULTRA", "OCR",
              "HIBRIDA", "RESISTENCIA", "ESPECIAL", "MIXTA"}
TIME = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
DISTANCE = re.compile(r"\d+(?:[.,]\d+)?\s*(?:km|m)\b", re.I)
FIELDS = ("fecha", "nombre", "localidad", "provincia", "modalidad",
          "distancia", "hora", "fuente", "fuente_nombre", "tipo_fuente")


def official_races(today=None, catalog=None):
    today = today or date.today()
    if catalog is None:
        catalog = json.loads(FILE.read_text(encoding="utf-8"))
    reviewed = date.fromisoformat(catalog["revision"])
    if reviewed > today:
        raise ValueError("Catálogo oficial con fecha de cotejo futura")
    if reviewed < date(2026, 1, 1):
        raise ValueError("Catálogo oficial sin año de revisión fiable")
    stale = today > reviewed + timedelta(days=MAX_AGE)
    results, seen = [], set()
    for index, record in enumerate(catalog["carreras"], 1):
        if not all(key in record for key in FIELDS):
            raise ValueError("Ficha oficial incompleta: " + str(index))
        event_date = date.fromisoformat(record["fecha"])
        if event_date < today:
            continue
        key = (record["fecha"], record["nombre"].casefold().strip(),
               record["localidad"].casefold().strip())
        if key in seen:
            raise ValueError("Ficha oficial duplicada: " + str(key))
        seen.add(key)
        if not record["nombre"].strip() or len(record["nombre"]) > 170:
            raise ValueError("Nombre inválido en ficha oficial")
        if not record["localidad"].strip() or len(record["localidad"]) > 90:
            raise ValueError("Municipio inválido en ficha oficial")
        if record["provincia"] not in PROVINCES or record["modalidad"] not in MODALITIES:
            raise ValueError("Provincia o modalidad inválida")
        if record["hora"] and not TIME.fullmatch(record["hora"]):
            raise ValueError("Hora de salida inválida")
        if record["distancia"] and not DISTANCE.search(record["distancia"]):
            raise ValueError("Distancia sin unidades reconocibles")
        if record["tipo_fuente"] not in ("organizador", "administracion", "cronometraje"):
            raise ValueError("Procedencia sin identificar")
        url = urlparse(record["fuente"])
        if url.scheme != "https" or not url.hostname or url.username or url.password:
            raise ValueError("Ficha con enlace de fuente inválido")
        race = {field: record[field] for field in FIELDS}
        race.update({"enlace":record["fuente"],
                     "origen":"oficial", "fuente_directa":not stale,
                     "cotejada":reviewed.isoformat(), "verificado":reviewed.isoformat(),
                     "estado":("Cotejada · reconfirmar en la fuente" if stale
                               else "Fuente oficial revisada · comprobar cambios"),
                     "desnivel":"", "precio":"", "bolsa":"", "track":""})
        results.append(race)
    return results
