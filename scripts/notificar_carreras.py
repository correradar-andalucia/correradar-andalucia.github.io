#!/usr/bin/env python3
"""Un email por publicación con carreras nuevas; estado en rama Git separada.

- Primera ejecución: toma la web existente como referencia y no envía 162 avisos.
- No envía correo si solo cambia el HTML, hora, distancia o datos de una ficha.
- Si el correo no está configurado o falla, NO marca las novedades como enviadas.
- La rama de estado registra únicamente hechos de carreras ya publicados, nunca claves.
"""
from __future__ import annotations

import argparse
from datetime import date
from difflib import SequenceMatcher
from email.message import EmailMessage
import json
import os
from pathlib import Path
import re
import smtplib
import ssl
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


def make_message(events, recipient, sender):
    if not events:
        raise ValueError("No hay nuevas carreras para notificar")
    if "\n" in recipient or "\r" in recipient or "@" not in recipient:
        raise ValueError("Destinatario inválido")
    count = len(events)
    msg = EmailMessage()
    msg["Subject"] = f"CorreRadar: {count} carrera{'s' if count != 1 else ''} nueva{'s' if count != 1 else ''}"
    msg["From"] = sender
    msg["To"] = recipient
    lines = [
        f"Se han publicado {count} carrera{'s' if count != 1 else ''} nueva{'s' if count != 1 else ''} en CorreRadar Andalucía.",
        "", "Novedades:"
    ]
    for event in sorted(events, key=lambda r: (r["fecha"], r["nombre"]))[:60]:
        label = f"- {event['nombre']} — {event['fecha']} — {event['localidad']} ({event['provincia']})"
        if event.get("distancia"):
            label += f" — {event['distancia']}"
        lines.extend([label, f"  Fuente: {source_url(event)}"])
        if event.get("slug"):
            lines.append(f"  Ficha: {SITE_URL}/carreras/{quote(event['slug'], safe='')}/")
        lines.append("")
    if count > 60:
        lines.extend([f"Y {count - 60} novedades más. Consulta el calendario completo:", SITE_URL])
    lines.extend(["", f"Calendario: {SITE_URL}", "",
                  "Aviso automático generado tras un despliegue correcto.",
                  "Si la fuente cambia una fecha, comprueba siempre sus datos originales."])
    msg.set_content("\n".join(lines))
    return msg


def send_email(events, sender, password, recipient, *, smtp_factory=smtplib.SMTP_SSL):
    msg = make_message(events, recipient, sender)
    # Contraseñas de aplicación únicamente desde GitHub Actions Secrets.
    with smtp_factory("smtp.gmail.com", 465, context=ssl.create_default_context(),
                      timeout=30) as server:
        server.login(sender, password)
        server.send_message(msg)


def process(calendar_path, state_path, next_path, *, sender, password, recipient):
    current = load_calendar(calendar_path)
    previous = load_state(state_path)
    new, seen, first_run = plan(current, previous)
    if first_run:
        print(f"Primer despliegue monitorizado: referencia inicial de {len(current)} eventos; sin correo.")
    elif new:
        if not (sender and password and recipient):
            print(f"SMTP no configurado: {len(new)} novedades pendientes, SIN marcar como avisadas.")
            return {"baseline": False, "new": len(new), "committed": False}
        send_email(new, sender, password, recipient)
        print(f"Correo enviado: {len(new)} carreras nuevas.")
    else:
        print("Sin carreras nuevas: no se envía correo.")

    # No adelantar el estado si el SMTP falla: GitHub reintentará en el siguiente
    # despliegue, sin falsas afirmaciones de aviso entregado.
    state = {"version": VERSION, "eventos": seen}
    Path(next_path).write_text(json.dumps(state, ensure_ascii=False, separators=(",", ":")) + "\n",
                               encoding="utf-8")
    return {"baseline": first_run, "new": len(new), "committed": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--calendario", required=True)
    parser.add_argument("--estado-anterior", required=True)
    parser.add_argument("--estado-siguiente", required=True)
    args = parser.parse_args()
    default_email = json.loads((Path(__file__).resolve().parents[1] / "config"
                                / "site.json").read_text(encoding="utf-8")).get("contact_email", "")
    process(args.calendario, args.estado_anterior, args.estado_siguiente,
            sender=os.environ.get("CARRERAS_SMTP_USER", "").strip() or default_email,
            password=os.environ.get("CARRERAS_SMTP_APP_PASSWORD", "").replace(" ", ""),
            recipient=os.environ.get("CARRERAS_ALERT_EMAIL", "").strip() or default_email)


if __name__ == "__main__":
    main()
