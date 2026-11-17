#!/usr/bin/env python3
"""Empaquetar la web privada como módulo del Worker, sin Assets Binding.

No generar ni subir este archivo a un Pages público, ni añadirlo a Git.
Cloudflare Access autentica ANTES de que se sirva un solo archivo.
"""
from __future__ import annotations
import base64
import json
import mimetypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
DEST = ROOT / "private" / "generated.mjs"
MIMES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".xml": "application/xml; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".webmanifest": "application/manifest+json",
}
MAX_RAW_BYTES = 8 * 1024 * 1024


def prepare(site=SITE, dest=DEST):
    site = Path(site).resolve()
    dest = Path(dest)
    if not (site / "data" / "carreras.json").is_file():
        raise ValueError("Falta el calendario verificado: generar primero con scripts/build.py")
    result = {}
    size = 0
    for item in sorted(site.rglob("*")):
        if not item.is_file() or item.suffix.lower() not in MIMES:
            continue
        if item.is_symlink() or not item.resolve().is_relative_to(site):
            raise ValueError("Se rechaza enlace simbólico en paquete privado")
        data = item.read_bytes()
        size += len(data)
        if size > MAX_RAW_BYTES:
            raise ValueError("Calendario supera límite seguro del Worker")
        url = "/" + item.relative_to(site).as_posix()
        result[url] = [
            base64.b64encode(data).decode("ascii"), MIMES[item.suffix.lower()]
        ]
    if "/index.html" not in result:
        raise ValueError("Falta portada de calendario privado")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        "/* ARCHIVO GENERADO. NO SUBIR AL REPOSITORIO. */\n"
        + "export const FILES = Object.freeze("
        + json.dumps(result, ensure_ascii=True, separators=(",", ":"))
        + ");\n",
        encoding="utf-8",
    )
    return {"archivos": len(result), "bytes": size}


if __name__ == "__main__":
    print("Worker privado empaquetado:", prepare())
