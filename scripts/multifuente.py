"""Semilla de calendario multifuente cotejada el 15-11-2026.

No descarga webs ni equivale a una lectura en vivo. Caduca a los 30 días.
Conserva la prioridad de las carreras aprobadas en Google Sheets.
"""
import csv
import datetime as dt
import difflib
import re
import unicodedata
from pathlib import Path

SEED_DATE = dt.date(2026, 11, 15)
SEED_DAYS = 30
FILE = Path(__file__).resolve().parents[1] / "data" / "semilla_multifuente_2026-11-15.psv"
SOURCE_HOMES = {
    "globaltempo": "https://gateway.global-tempo.com/index.php",
    "dorsalchip": "https://dorsalchip.es/view/Inicio.aspx",
    "fadmes": "https://fadmes.es/calendario-fam/",
    "faa": "https://atletismofaa.es/carreraspopulares/",
    "cruzandolameta": "https://www.cruzandolameta.es/pruebas/",
    "dipgra": "https://www.dipgra.es/servicios/areas/deportes/deporte-competicion/circuito-provincial-campo-a-traves/",
    "gcc": "https://www.gccsportevents.es/",
    "rockthesport": "https://web.rockthesport.com/es",
}
PROVINCES = {"Almería", "Cádiz", "Córdoba", "Granada", "Huelva", "Jaén", "Málaga", "Sevilla"}
MODALITIES = {"RUNNING", "TRAIL", "CROSS", "ULTRA", "OCR", "HIBRIDA", "RESISTENCIA", "ESPECIAL"}

def norm(value):
    chars = unicodedata.normalize("NFKD", str(value or "").casefold())
    return re.sub(r"\s+", " ", "".join(c for c in chars if not unicodedata.combining(c))).strip()

def seed_races(today=None):
    today = today or dt.date.today()
    if not SEED_DATE <= today <= SEED_DATE + dt.timedelta(days=SEED_DAYS):
        return []
    if not FILE.exists():
        return []
    result = []
    with FILE.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter="|"):
            try:
                day = dt.date.fromisoformat(r["date"])
                source = (r.get("origen") or "").lower().strip()
                name = (r.get("nombre") or "").strip()
                city = (r.get("localidad") or "").strip()
                province = (r.get("provincia") or "").strip()
                modality = (r.get("modalidad") or "").strip()
                if day < today or source not in SOURCE_HOMES or not name or not city:
                    continue
                if province not in PROVINCES or modality not in MODALITIES:
                    continue
                source_url = (r.get("url") or "").strip()
                if not source_url.startswith("https://"):
                    source_url = SOURCE_HOMES[source]
                result.append({
                    "fecha": day.isoformat(), "nombre": name, "localidad": city,
                    "provincia": province, "distancia": (r.get("distancia") or "").strip(),
                    "km": 0, "modalidad": modality, "desnivel": "", "precio": "",
                    "bolsa": "", "track": "", "enlace": source_url, "fuente": source_url,
                    "estado": "Cotejada · confirmar en fuente", "verificado": SEED_DATE.isoformat(),
                    "origen": source,
                })
            except (ValueError, KeyError):
                continue
    return result

def combine(approved, candidates, slugify, km_parse):
    """Prioriza las aprobadas; fusiona duplicados muy parecidos por fecha y localidad."""
    result = list(approved)
    seen_slugs = {r.get("slug") for r in result}
    for item in candidates:
        identity = (item["fecha"], norm(item["provincia"]), norm(item["localidad"]))
        name = norm(item["nombre"])
        duplicate = False
        for existing in result:
            other = (existing["fecha"], norm(existing.get("provincia")), norm(existing.get("localidad")))
            if other != identity:
                continue
            a = norm(existing["nombre"])
            if a == name or difflib.SequenceMatcher(None, a, name).ratio() >= 0.82:
                duplicate = True
                break
        if duplicate:
            continue
        race = dict(item)
        for key in ("distancia", "desnivel", "precio", "bolsa", "track"):
            race.setdefault(key, "")
        race.setdefault("estado", "Por confirmar · fuente directa")
        race.setdefault("verificado", dt.date.today().isoformat())
        race["km"] = km_parse(race["distancia"])
        race["slug"] = slugify(f"{race['nombre']}-{race['localidad']}-{race['fecha']}")
        if race["slug"] in seen_slugs:
            continue
        seen_slugs.add(race["slug"])
        result.append(race)
    return sorted(result, key=lambda r: (r["fecha"], norm(r["nombre"])))
