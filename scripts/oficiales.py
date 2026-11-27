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

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
FILE = DATA_DIR / "fichas_oficiales_2026-11-16.json"
GLOBALTEMPO_FILE = DATA_DIR / "fichas_globaltempo_2026-11-17.json"
FILES = (FILE, DATA_DIR / "fichas_oficiales_2026-11-17.json",
         GLOBALTEMPO_FILE, DATA_DIR / "fichas_oficiales_2026-11-18_jaen_huelva.json",
         DATA_DIR / "fichas_oficiales_2026-11-20.json",
         DATA_DIR / "fichas_oficiales_2026-11-20_vicar.json",
         DATA_DIR / "fichas_oficiales_2026-11-25_guajares.json",
         DATA_DIR / "fichas_oficiales_2026-11-26_media_cordoba.json",
         DATA_DIR / "fichas_oficiales_2026-11-27_subbetica_trail.json")
# Directorio de agregadores del Excel recibido. Son para descubrir carreras,
# no sirven como fuente final de confirmación editorial.
AGGREGATOR_HOSTS = frozenset({
    "andaluciarunning.com", "runnea.com", "corredorespopulares.es",
    "carreraspopulares.com", "clubrunning.es", "runagain.com",
    "hybridracemap.com", "hybridracehub.com", "metahibrida.com",
    "sportplan.es",
})
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
    """Une cotejos fechados, sin renovar implícitamente los cotejos antiguos."""
    today = today or date.today()
    if catalog is not None:
        return _read_catalog(today, catalog)
    result = []
    for path in FILES:
        if path.exists():
            record=json.loads(path.read_text(encoding="utf-8"))
            # En pruebas históricas no introducir información cotejada después.
            if date.fromisoformat(record["revision"]) > today:
                continue
            result.extend(_read_catalog(today, record))
    return result


def _read_catalog(today, catalog):
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
        host = url.hostname.removeprefix("www.")
        # Las revisiones manuales de Global Tempo necesitan una ficha específica
        # de inscripción, no una portada ni un calendario general.
        if record["fuente_nombre"].startswith("Global Tempo") and not (
            host in ("global-tempo.com",)
            and url.path == "/carreras.php"
            and re.fullmatch(r"id=\d{1,7}", url.query)
        ):
            raise ValueError("Global Tempo exige enlace a edición concreta")
        # Corredores Populares también aloja inscripciones REALES de eventos.
        # Única excepción, verificada por inscripción y reglamento de esta edición;
        # no convertir todo su calendario en pruebas confirmadas.
        signup_exception=(
            host=="corredorespopulares.es"
            and url.path=="/inscripciones.php"
            and record["tipo_fuente"]=="cronometraje"
            and record["fecha"]=="2026-12-20"
            and record["nombre"]=="III Carrera Popular de Navidad El Rubio"
        )
        if host in AGGREGATOR_HOSTS and not signup_exception:
            raise ValueError("Una web agregadora no acredita la confirmación: "+host)
        race = {field: record[field] for field in FIELDS}
        race.update({"enlace":record["fuente"],
                     "origen":"oficial", "fuente_directa":not stale,
                     "cotejada":reviewed.isoformat(), "verificado":reviewed.isoformat(),
                     "estado":("Cotejada · reconfirmar en la fuente" if stale
                               else "Fuente oficial revisada · comprobar cambios"),
                     "desnivel":"", "precio":"", "bolsa":"", "track":""})
        results.append(race)
    return results
