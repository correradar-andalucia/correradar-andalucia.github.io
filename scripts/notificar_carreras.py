#!/usr/bin/env python3
"""Una incidencia GitHub por publicación con carreras nuevas; histórico Git separado.

- Primera ejecución: toma la web existente como referencia y no envía 162 avisos.
- No envía correo si solo cambia el HTML, hora, distancia o datos de una ficha.
- GitHub crea una incidencia por lote; sus notificaciones de email dependen de Watch.
- La rama de estado registra únicamente hechos de carreras ya publicados, nunca claves.
"""
from __future__ import annotations

import argparse
import hashlib
from datetime import date
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import quote, urlparse

SITE_URL = "https://correradar-andalucia.github.io"
VERSION = 1


def normalize(text):
    value = unicodedata.normalize("NFKD", str(text or "").casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value)).strip()


def event_record(row):
    """Solo campos necesarios para identificar la carrera, sin participantes."""
    required = ("fecha", "nombre", "localidad", "provincia")
    if not isinstance(row, dict) or any(not str(row.get(k, "")).strip() for k in required):
        raise ValueError("Ficha sin datos mínimos para detectar carreras nuevas")
    stamp = str(row["fecha"])
    if date.fromisoformat(stamp).isoformat() != stamp:
        raise ValueError("Fecha inválida en el calendario")
    result = {key: str(row[key]).strip() for key in required}
    for key in ("slug", "distancia", "enlace", "fuente"):
        result[key] = str(row.get(key) or "").strip()
    return result


def is_same_event(a, b):
    if (a["fecha"], normalize(a["provincia"]), normalize(a["localidad"])) != (
        b["fecha"], normalize(b["provincia"]), normalize(b["localidad"])
    ):
        return False
    an = normalize(a["nombre"])
    bn = normalize(b["nombre"])
    if an == bn:
        return True
    # Pequeñas rectificaciones de nombre no son carreras añadidas.
    return SequenceMatcher(None, an, bn).ratio() >= 0.88


def unique_events(rows):
    result = []
    for raw in rows:
        item = event_record(raw)
        if not any(is_same_event(item, previous) for previous in result):
            result.append(item)
    return result


def load_calendar(path):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or not isinstance(doc.get("carreras"), list):
        raise ValueError("Calendario de carreras inválido")
    if not doc["carreras"]:
        raise ValueError("Se rechaza calendario vacío para evitar perder estado")
    return unique_events(doc["carreras"])


def load_state(path):
    path = Path(path)
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != VERSION:
        raise ValueError("Estado anterior de avisos incompatible")
    rows = data.get("eventos")
    if not isinstance(rows, list):
        raise ValueError("Estado anterior incompleto")
    return unique_events(rows)


def plan(current, previous):
    if previous is None:
        # El calendario preexistente no debe considerarse nuevo el día de alta.
        return [], list(current), True
    fresh = []
    seen = list(previous)
    for row in current:
        if any(is_same_event(row, old) for old in seen):
            continue
        fresh.append(row)
        seen.append(row)
    # Registrar alias/renombres de eventos ya conocidos, sin disparar nuevos avisos.
    for row in current:
        if not any(row == old for old in seen):
            seen.append(row)
    return fresh, seen, False


def source_url(row):
    for raw in (row.get("enlace"), row.get("fuente")):
        try:
            parsed = urlparse(str(raw))
            if parsed.scheme == "https" and parsed.netloc and not parsed.username:
                return parsed.geturl()
        except ValueError:
            continue
    return SITE_URL


def safe_markdown(text):
    # No crear menciones de usuarios a partir de nombres leídos de terceros.
    value = re.sub(r"[\x00-\x1f\x7f]+", " ", str(text or ""))[:240].strip()
    value = value.replace("@", "＠")
    return re.sub(r"([\\*_{}\[\]<>()#+.!|~-])", r"\\\1", value)


def fingerprint(events):
    identities = sorted([
        row["fecha"], normalize(row["provincia"]),
        normalize(row["localidad"]), normalize(row["nombre"])
    ] for row in events)
    return hashlib.sha256(json.dumps(identities, ensure_ascii=False).encode()).hexdigest()[:24]


def make_issue(events):
    if not events:
        raise ValueError("No hay carreras nuevas para notificar")
    count = len(events)
    label = "carrera nueva" if count == 1 else "carreras nuevas"
    title = f"CorreRadar: {count} {label} publicadas"
    marker = f"<!-- correradar-avisos:{fingerprint(events)} -->"
    body = [
        marker, f"## {count} {label.capitalize()}",
        "Actualización del calendario tras una publicación correcta en GitHub Pages.",
        ""
    ]
    for row in sorted(events, key=lambda r: (r["fecha"], r["nombre"]))[:60]:
        name = safe_markdown(row["nombre"])
        city = safe_markdown(row["localidad"])
        prov = safe_markdown(row["provincia"])
        body += [f"- **{name}** — {row['fecha']} — {city} ({prov})"]
        if row.get("distancia"):
            body += [f"  - Distancia: {safe_markdown(row['distancia'])}"]
        body += [f"  - Fuente: <{source_url(row)}>"]
        if row.get("slug"):
            body += [f"  - Ficha: {SITE_URL}/carreras/{quote(row['slug'], safe='')}/"]
    if count > 60:
        body += ["", f"Y {count - 60} carreras adicionales en {SITE_URL}."]
    body += ["", f"Calendario completo: {SITE_URL}", "",
             "Aviso creado automáticamente; confirma los datos en cada fuente original.",
             "Recíbelo por correo con Watch > Custom > Issues y las notificaciones email de GitHub."]
    return title, "\n".join(body) + "\n", marker


def process(calendar_path, state_path, next_path, title_path, body_path):
    current = load_calendar(calendar_path)
    previous = load_state(state_path)
    new, seen, first_run = plan(current, previous)
    if first_run:
        print(f"Referencia inicial de {len(current)} carreras; sin incidencia.")
    elif new:
        title, body, marker = make_issue(new)
        Path(title_path).write_text(title + "\n", encoding="utf-8")
        Path(body_path).write_text(body, encoding="utf-8")
        print(f"Incidencia preparada para {len(new)} carreras: {marker}.")
    else:
        print("Sin carreras nuevas; no se crea incidencia.")
    # Solo después de crear/confirmar incidencia el workflow guardará este estado.
    Path(next_path).write_text(json.dumps({"version": VERSION, "eventos": seen},
                                         ensure_ascii=False, separators=(",", ":")) + "\n",
                               encoding="utf-8")
    return {"baseline": first_run, "new": len(new), "committed": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--calendario", required=True)
    parser.add_argument("--estado-anterior", required=True)
    parser.add_argument("--estado-siguiente", required=True)
    parser.add_argument("--aviso-titulo", required=True)
    parser.add_argument("--aviso-cuerpo", required=True)
    args = parser.parse_args()
    process(args.calendario, args.estado_anterior, args.estado_siguiente,
            args.aviso_titulo, args.aviso_cuerpo)


if __name__ == "__main__":
    main()
