"""Extracción restrictiva de distancias explícitas en títulos o campos de una ficha.

Nunca inferir kilómetros por el tipo de carrera (media maratón, 10 millas, etc.).
No recorrer toda la página para evitar traer distancias de otras carreras.
"""
from __future__ import annotations
import re
import unicodedata

NUMBER = r"(\d{1,3}(?:[.,]\d{1,3})?)"
UNIT = re.compile(rf"(?<![\d]){NUMBER}\s*(km|kms|kil[oó]metros?|m|metros?|k)\b", re.I)
LABEL = re.compile(r"^\s*(?:distancias?|recorridos?)\s*(?::|[-–]|\s|$)", re.I)
MAX_DISTANCES = 4


def _one(raw, unit):
    value = float(raw.replace(",", "."))
    unit = unit.lower()
    if unit in ("m", "metro", "metros"):
        # Un «m» muy pequeño suele indicar desnivel o un punto kilométrico.
        if not 200 <= value <= 10000:
            return ""
        return f"{raw} m"
    if not 0.2 <= value <= 250:
        return ""
    return f"{raw} km"


def _values(text):
    found = []
    for match in UNIT.finditer(str(text or "")):
        value = _one(match.group(1), match.group(2))
        if value and value not in found:
            found.append(value)
    if len(found) > MAX_DISTANCES:
        return []
    return found


def extract_distance(title="", fragments=()):
    """Distancia textual, solo si la unidad es explícita.

    title: nombre exacto de la prueba, p.ej. «Carrera 10K».
    fragments: nodos de texto de ESA ficha, no de un calendario de varios eventos.
    Solo lee nodos etiquetados como Distancia/Distancias/Recorrido/Recorridos.
    """
    title_values = _values(title)
    detail_values = []
    parts = list(fragments)
    for i, part in enumerate(parts[:180]):
        label = str(part or "").strip()
        if not LABEL.match(label):
            continue
        if len(label) > 95:
            continue
        # Un campo cercano, nunca párrafos posteriores de publicidad u otros eventos.
        short = " ".join(str(p) for p in parts[i:i+3])[:105]
        values = _values(short)
        if values:
            detail_values = values
            break
    if title_values and detail_values and set(title_values) != set(detail_values):
        return ""  # Inconsistencia en la propia ficha: no adivinar
    values = detail_values or title_values
    return " · ".join(values)
