"""Auditoría offline de procedencia de la última salida de CorreRadar.

Entrada: carreras.json publicado (archivo local) y registro de derechos del repo.
Salida: SOLO recuentos. No consulta fuentes, no publica ni altera ningún archivo.
Una fuente registrada no acredita por sí misma licencia ni verificación editorial.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIORITARIAS = frozenset({"fadmes", "gesconchip", "runnink"})
EXTRAS_CONOCIDOS = frozenset({"oficial", "globaltempo", "rockthesport"})
PROVINCIAS = frozenset({
    "Almería", "Cádiz", "Córdoba", "Granada",
    "Huelva", "Jaén", "Málaga", "Sevilla",
})
REQUERIDOS = ("nombre", "fecha", "localidad", "provincia", "enlace")


def auditar(calendario, registro):
    """Agrupar exclusivamente métricas, sin conservar ni devolver fichas/URLs."""
    if not isinstance(calendario, dict) or not isinstance(calendario.get("carreras"), list):
        raise ValueError("Calendario sin lista de carreras")
    fuentes = registro.get("fuentes") if isinstance(registro, dict) else None
    if not isinstance(fuentes, dict):
        raise ValueError("Registro de derechos sin fuentes")
    riesgos = frozenset(
        codigo for codigo, cfg in fuentes.items()
        if isinstance(cfg, dict)
        and cfg.get("riesgo_aviso_legal") in ("reserva_expresa", "reserva_general")
    )
    nombres = frozenset(fuentes) | EXTRAS_CONOCIDOS
    stats = {
        "total": 0, "sin_fuentes_origen": 0, "fuente_unica": 0,
        "mas_de_una_fuente": 0, "slugs_repetidos": 0,
        "campos_esenciales_incompletos": 0,
        "con_prioritaria": 0, "solo_prioritarias": 0,
        "con_fuente_en_riesgo": 0, "solo_fuentes_en_riesgo": 0,
    }
    por_provincia = Counter()
    por_fuente = Counter()
    fuentes_unicas = Counter()
    origen_fecha = Counter()
    slugs = set()
    for carrera in calendario["carreras"]:
        if not isinstance(carrera, dict):
            raise ValueError("Carrera con formato inválido")
        stats["total"] += 1
        if any(not carrera.get(k) for k in REQUERIDOS):
            stats["campos_esenciales_incompletos"] += 1
        slug = carrera.get("slug")
        if not isinstance(slug, str) or not slug or slug in slugs:
            stats["slugs_repetidos"] += 1
        else:
            slugs.add(slug)
        provincia = carrera.get("provincia")
        por_provincia[provincia if provincia in PROVINCIAS else "otra"] += 1
        fecha_origen = carrera.get("fecha_origen")
        origen_fecha[fecha_origen if fecha_origen in ("fuente", "catalogo", "editorial") else "otro"] += 1
        raw = carrera.get("fuentes_origen", [])
        if not isinstance(raw, list):
            raise ValueError("fuentes_origen debe ser una lista")
        presentes = frozenset(s for s in raw if isinstance(s, str) and s)
        if not presentes:
            stats["sin_fuentes_origen"] += 1
        elif len(presentes) == 1:
            stats["fuente_unica"] += 1
            fuente = next(iter(presentes))
            fuentes_unicas[fuente if fuente in nombres else "otra"] += 1
        else:
            stats["mas_de_una_fuente"] += 1
        for fuente in presentes:
            por_fuente[fuente if fuente in nombres else "otra"] += 1
        if presentes & PRIORITARIAS:
            stats["con_prioritaria"] += 1
            if presentes <= PRIORITARIAS:
                stats["solo_prioritarias"] += 1
        if presentes & riesgos:
            stats["con_fuente_en_riesgo"] += 1
            if presentes <= riesgos:
                stats["solo_fuentes_en_riesgo"] += 1
    return {
        "resumen": stats,
        "provincias": dict(sorted(por_provincia.items())),
        "fuentes_registradas": dict(sorted(por_fuente.items())),
        "fuente_unica_por_codigo": dict(sorted(fuentes_unicas.items())),
        "origen_fecha": dict(sorted(origen_fecha.items())),
        "grupos": {
            "prioritarias_para_consulta": sorted(PRIORITARIAS),
            "con_reservas_documentadas": sorted(riesgos),
        },
        "advertencia": (
            "Agrupaciones de procedencia declarada: no acreditan derechos,"
            " independencia de fuentes ni necesidad automática de retirada"
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("calendario", type=Path, help="carreras.json de un despliegue confirmado")
    parser.add_argument("--derechos", type=Path, default=ROOT / "config/derechos_fuentes.json")
    args = parser.parse_args()
    calendario = json.loads(args.calendario.read_text(encoding="utf-8"))
    derechos = json.loads(args.derechos.read_text(encoding="utf-8"))
    print(json.dumps(auditar(calendario, derechos), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
