"""Comprobación final del artefacto estático antes de subirlo a GitHub Pages."""
from __future__ import annotations
import json
from pathlib import Path

from control_calidad import check_launch_ready


def verify_output(root, config):
    root = Path(root)
    check_launch_ready(config)
    errors = []
    for relative in ("index.html", "robots.txt", "sitemap.xml",
                     "assets/app.js", "assets/styles.css",
                     "data/carreras.json", "data/estado_fuentes.json",
                     "data/control_calidad.json"):
        if not (root / relative).is_file():
            errors.append("Falta archivo: " + relative)
    if errors:
        raise ValueError("ARTEFACTO INCOMPLETO: " + "; ".join(errors))
    races = json.loads((root/"data/carreras.json").read_text(encoding="utf-8"))["carreras"]
    quality = json.loads((root/"data/control_calidad.json").read_text(encoding="utf-8"))
    if not quality["apto_para_desplegar"] or quality["total_carreras"] != len(races):
        errors.append("Informe de calidad incompatible con el calendario")
    if len({r["slug"] for r in races}) != len(races):
        errors.append("URLs de carrera duplicadas")
    home = (root/"index.html").read_text(encoding="utf-8")
    pages = [(root/"carreras"/r["slug"]/"index.html") for r in races]
    for page in pages:
        if not page.is_file():
            errors.append("Ficha no generada: " + str(page.relative_to(root)))
    if not config.get("public_launch",False):
        # No bloquear robots.txt: el crawler debe poder leer la etiqueta noindex.
        marker = '<meta name="robots" content="noindex,nofollow">'
        if marker not in home:
            errors.append("Portada de prelanzamiento indexable")
        for page in pages:
            if page.is_file() and marker not in page.read_text(encoding="utf-8"):
                errors.append("Ficha indexable antes del lanzamiento: "+str(page.relative_to(root)))
    if errors:
        raise ValueError("PREPUBLICACIÓN BLOQUEADA: "+"; ".join(errors[:12]))
    return {"fichas_verificadas": len(pages),
            "prelanzamiento_noindex": not config.get("public_launch",False),
            "control_calidad": True}


if __name__ == "__main__":
    base = Path(__file__).resolve().parents[1]
    conf = json.loads((base/"config/site.json").read_text(encoding="utf-8"))
    print("VERIFICACIÓN DE SALIDA:", verify_output(base/"_site",conf))
