"""Control previo a publicar: evita despliegues de calendarios dañados o sin fuentes.

No verifica que los datos externos sean verdaderos; sí su estructura, procedencia,
enlaces seguros y una consulta mínima de fuentes para el despliegue programado.
No descarga páginas, no agrega ni inventa carreras.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from urllib.parse import urlparse

PROVINCES = ("Almería", "Cádiz", "Córdoba", "Granada",
             "Huelva", "Jaén", "Málaga", "Sevilla")
MODES = {"RUNNING", "TRAIL", "CROSS", "ULTRA", "RESISTENCIA",
         "OCR", "HIBRIDA", "ESPECIAL", "MIXTA"}
ORIGINS = {"editorial", "fuente", "catalogo"}


def valid_source(url):
    """Aceptar solo URL HTTPS con host real, sin credenciales o espacios."""
    if not isinstance(url, str) or any(c.isspace() for c in url):
        return False
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme == "https" and parsed.hostname
                    and "." in parsed.hostname and not parsed.username
                    and not parsed.password and not parsed.fragment.startswith("/"))
    except ValueError:
        return False


def check_launch_ready(config):
    """No permitir que un simple cambio a public_launch habilite indexación."""
    if not config.get("public_launch", False):
        return
    missing = []
    if not (config.get("contact_email") or "").strip():
        missing.append("contact_email")
    if not (config.get("legal_name") or "").strip():
        missing.append("legal_name")
    if config.get("legal_review_complete") is not True:
        missing.append("legal_review_complete=true tras revisión del responsable")
    if missing:
        raise ValueError("LANZAMIENTO BLOQUEADO: falta " + ", ".join(missing))


def inspect_calendar(races, capture_report, today=None):
    today = today or date.today()
    reasons, notices = [], []
    province_counts = Counter()
    origin_counts = Counter()
    totals = {"con_distancia": 0, "con_hora": 0, "con_enlace": 0}
    if not races:
        reasons.append("La web quedaría sin carreras; mantener la última publicación buena")

    for i, race in enumerate(races, 1):
        name = str(race.get("nombre") or "").strip()
        label = name[:65] or f"fila {i}"
        if not name or len(name) > 170:
            reasons.append(f"{label}: nombre inválido")
        try:
            when = date.fromisoformat(str(race["fecha"]))
            if when < today:
                reasons.append(f"{label}: fecha ya pasada")
            if when.year > today.year + 3:
                reasons.append(f"{label}: fecha excesivamente futura")
        except (ValueError, KeyError, TypeError):
            reasons.append(f"{label}: fecha inválida")
        province = race.get("provincia")
        if province not in PROVINCES:
            reasons.append(f"{label}: provincia desconocida")
        else:
            province_counts[province] += 1
        if not str(race.get("localidad") or "").strip():
            reasons.append(f"{label}: falta localidad")
        if race.get("modalidad") not in MODES:
            reasons.append(f"{label}: modalidad desconocida")
        origin = race.get("fecha_origen")
        if origin not in ORIGINS:
            reasons.append(f"{label}: no consta procedencia de la fecha")
        else:
            origin_counts[origin] += 1
        if race.get("distancia"):
            totals["con_distancia"] += 1
            if race.get("distancia_origen") not in ORIGINS:
                reasons.append(f"{label}: distancia sin procedencia")
        if race.get("hora") and race.get("hora_origen"):
            totals["con_hora"] += 1
        links = [race.get("enlace"), race.get("fuente")]
        if not any(valid_source(url) for url in links):
            reasons.append(f"{label}: sin enlace HTTPS a fuente o ficha")
        else:
            totals["con_enlace"] += 1
        # No publicar enlaces con javascript:/http:/credenciales ni en las fichas.
        for key in ("enlace", "fuente", "distancia_fuente", "track"):
            url = race.get(key)
            if url and not valid_source(url):
                reasons.append(f"{label}: enlace inseguro en {key}")
        consulted = str(race.get("consultado") or "").strip()
        if consulted:
            try:
                checked = date.fromisoformat(consulted)
                if checked > today:
                    reasons.append(f"{label}: consulta fechada en el futuro")
                elif origin == "fuente" and (today - checked).days > 30:
                    reasons.append(f"{label}: consulta antigua presentada como reciente")
            except ValueError:
                reasons.append(f"{label}: fecha de consulta inválida")

    capture_report = capture_report or {}
    sources = capture_report.get("fuentes") or {}
    live = sorted(key for key, record in sources.items()
                  if isinstance(record, dict) and record.get("estado") == "leida")
    offline = capture_report.get("modo") == "Prueba local sin conexión"
    if not offline and len(live) < 2:
        reasons.append("Menos de dos fuentes automáticas consultadas; conservar la última web")

    if len(province_counts) < 8:
        notices.append("No hay carreras próximas en las ocho provincias")
    if races and totals["con_distancia"] / len(races) < .5:
        notices.append("Menos de la mitad de las carreras tienen distancia")
    if sources and not live and offline:
        notices.append("Compilación sin red: no representa la salud de las fuentes")

    return {
        "fecha_revision": today.isoformat(),
        "apto_para_desplegar": not reasons,
        "bloqueos": reasons,
        "avisos": notices,
        "total_carreras": len(races),
        **totals,
        "provincias": {p: province_counts[p] for p in PROVINCES},
        "origen_fecha": {p: origin_counts[p] for p in ("editorial", "fuente", "catalogo")},
        "fuentes_automaticas_leidas": live,
        "fuentes_automaticas_leidas_total": len(live),
        "compilacion_sin_red": offline
    }
