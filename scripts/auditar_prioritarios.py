"""Auditoría local y de solo lectura de familias de carreras prioritarias.

No consulta webs externas, ni interpreta ausencia como cancelación o como
falta de edición. Solo contrasta un inventario editorial con el calendario
íntegro de la última publicación confirmada y verificada por SHA-256.
"""
from __future__ import annotations

import argparse
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
INVENTARIO = ROOT / "data" / "prioritarios_carreras.json"
PROVINCIAS = {"Almería", "Cádiz", "Córdoba", "Granada",
              "Huelva", "Jaén", "Málaga", "Sevilla"}


def normalizar(valor):
    texto = unicodedata.normalize("NFKD", str(valor or "").casefold())
    texto = "".join(x for x in texto if not unicodedata.combining(x))
    return " ".join(re.findall(r"[a-z0-9]+", texto))


def frase_en(texto, frase):
    return (" " + normalizar(frase) + " ") in (" " + texto + " ")


def validar_url(url):
    p = urlparse(url)
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise ValueError("Enlace de evidencia no HTTPS")


def leer_inventario(ruta=INVENTARIO):
    registro = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if registro.get("esquema") != 1 or not isinstance(registro.get("carreras"), list):
        raise ValueError("Inventario prioritario inválido")
    ids = set()
    for carrera in registro["carreras"]:
        codigo = carrera["id"]
        if codigo in ids or not re.fullmatch(r"[a-z0-9-]+", codigo):
            raise ValueError("Identidad prioritaria duplicada o inválida")
        ids.add(codigo)
        if carrera["provincia"] not in PROVINCIAS or not carrera["municipio"]:
            raise ValueError("Provincia o municipio prioritario inválido")
        if not carrera["alias"] or not all(normalizar(a) for a in carrera["alias"]):
            raise ValueError("Carrera prioritaria sin alias")
        if carrera["participacion_historica"]["cifra_referencia"] <= 500:
            raise ValueError("No se acredita el umbral de vigilancia histórica")
        validar_url(carrera["participacion_historica"]["fuente"])
        objetivo = carrera.get("edicion_anunciada")
        if objetivo:
            if not isinstance(objetivo["anio"], int) or objetivo["anio"] < 2026:
                raise ValueError("Año de edición objetivo inválido")
            validar_url(objetivo["fuente"])
    for fuente in registro["fuentes_federativas"]:
        validar_url(fuente["url"])
    return registro


def leer_calendario_confirmado(ruta):
    """Valida bytes embebidos y huella; main/data/carreras.json NO es publicación."""
    estado = json.loads(Path(ruta).read_text(encoding="utf-8"))
    confirmado = estado.get("confirmado")
    if not isinstance(confirmado, dict) or not isinstance(confirmado.get("calendario"), str):
        raise ValueError("No existe calendario confirmado")
    bruto = confirmado["calendario"].encode("utf-8")
    huella = sha256(bruto).hexdigest()
    if huella != confirmado.get("sha256"):
        raise ValueError("Huella del calendario confirmado inválida")
    calendario = json.loads(bruto)
    if not isinstance(calendario.get("carreras"), list) or not calendario["carreras"]:
        raise ValueError("El calendario confirmado está vacío o corrupto")
    publicacion = confirmado.get("publicacion")
    if not isinstance(publicacion, dict) or not publicacion.get("fecha"):
        raise ValueError("Falta la identidad de publicación confirmada")
    for carrera in calendario["carreras"]:
        if not all(carrera.get(x) for x in ("nombre", "fecha", "localidad", "provincia")):
            raise ValueError("Calendario confirmado con carrera incompleta")
        date.fromisoformat(carrera["fecha"])
    return calendario, {
        "sha256": huella,
        "publicacion": publicacion,
        "pendiente": estado.get("pendiente") is not None,
    }


def coincide(candidata, prioridad):
    if normalizar(candidata["provincia"]) != normalizar(prioridad["provincia"]):
        return False
    if normalizar(candidata["localidad"]) != normalizar(prioridad["municipio"]):
        return False
    titulo = normalizar(candidata["nombre"])
    if any(frase_en(titulo, x) for x in prioridad.get("excluir", [])):
        return False
    return any(frase_en(titulo, x) for x in prioridad["alias"])


def auditar(inventario, calendario, referencia):
    resultados = []
    for prioridad in inventario["carreras"]:
        similares = [r for r in calendario["carreras"] if coincide(r, prioridad)]
        objetivo = prioridad.get("edicion_anunciada")
        if objetivo:
            misma = [r for r in similares if date.fromisoformat(r["fecha"]).year == objetivo["anio"]]
            estado = ("edicion_cubierta" if misma else
                      "otra_edicion_localizada" if similares else "edicion_no_localizada")
            filas = misma or similares
        else:
            estado = "familia_localizada" if similares else "sin_ficha_actual"
            filas = similares
        resultados.append({
            "id": prioridad["id"],
            "nombre": prioridad["nombre"],
            "provincia": prioridad["provincia"],
            "municipio": prioridad["municipio"],
            "edicion_anunciada": objetivo["anio"] if objetivo else None,
            "estado": estado,
            "fichas": [
                {"nombre": r["nombre"], "fecha": r["fecha"],
                 "localidad": r["localidad"], "slug": r.get("slug", "")}
                for r in sorted(filas, key=lambda x: (x["fecha"], x["nombre"]))
            ],
            "fuente_evidencia": prioridad["participacion_historica"]["fuente"],
            "fuente_edicion": objetivo["fuente"] if objetivo else None,
        })
    estados = sorted(set(r["estado"] for r in resultados))
    resumen = {key: sum(x["estado"] == key for x in resultados) for key in estados}
    provincias = {
        p: {key: sum(x["provincia"] == p and x["estado"] == key for x in resultados)
            for key in estados}
        for p in sorted(PROVINCIAS)
    }
    return {
        "esquema": 1,
        "fecha_revision_inventario": inventario["revision"],
        "publicacion": referencia["publicacion"],
        "sha256_calendario_confirmado": referencia["sha256"],
        "intento_pendiente": referencia["pendiente"],
        "total_calendario_confirmado": len(calendario["carreras"]),
        "total_familias_vigiladas": len(resultados),
        "resumen": resumen,
        "por_provincia": provincias,
        "resultados": resultados,
        "fuentes_federativas": inventario["fuentes_federativas"],
        "advertencia": (
            "Una ausencia NO prueba cancelación ni confirma una edición futura; "
            "solo indica que no hay coincidencia por nombre, municipio y provincia "
            "en la copia confirmada. Las cifras de participación son históricas. "
            "Los campeonatos requieren verificación editorial independiente."
        ),
    }


def informe_markdown(reporte):
    fecha = reporte["publicacion"]["fecha"]
    lineas = [
        "# Cobertura de carreras prioritarias — auditoría de solo lectura",
        "",
        "Copia confirmada: " + fecha + " UTC · " +
        str(reporte["total_calendario_confirmado"]) + " carreras",
        "",
        "**Aviso:** " + reporte["advertencia"],
        "",
        "No se publican carreras, no se consultan fuentes externas y no se crean avisos.",
        "",
        "| Provincia | Carrera | Edición anunciada | Resultado | Coincidencia publicada |",
        "|---|---|---|---|---|",
    ]
    for f in reporte["resultados"]:
        coincidencias = "; ".join(
            r["nombre"].replace("|", "/") + " (" + r["fecha"] + ")"
            for r in f["fichas"]
        ) or "—"
        lineas.append("| " + " | ".join([
            f["provincia"], f["nombre"].replace("|", "/"),
            str(f["edicion_anunciada"] or "No acreditada"),
            f["estado"].replace("_", " "), coincidencias,
        ]) + " |")
    lineas.extend([
        "",
        "## Fuentes federativas de referencia (sin nueva captación)",
    ])
    for fuente in reporte["fuentes_federativas"]:
        lineas.append("- " + fuente["sigla"] + ": " + fuente["url"] +
                      " — " + fuente["nota"])
    lineas.extend(["", "Las fichas requieren cotejo de edición y autorización editorial.",
                    ""])
    return "\n".join(lineas)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--estado", required=True,
                        help="estado.json de la rama estado-correradar-continuidad")
    parser.add_argument("--inventario", default=str(INVENTARIO))
    parser.add_argument("--salida-json", required=True)
    parser.add_argument("--salida-md", required=True)
    args = parser.parse_args()
    inventario = leer_inventario(args.inventario)
    calendario, referencia = leer_calendario_confirmado(args.estado)
    resultado = auditar(inventario, calendario, referencia)
    salida_json, salida_md = Path(args.salida_json), Path(args.salida_md)
    salida_json.parent.mkdir(parents=True, exist_ok=True)
    salida_md.parent.mkdir(parents=True, exist_ok=True)
    salida_json.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    salida_md.write_text(informe_markdown(resultado), encoding="utf-8")
    print("Auditoría de solo lectura: " + str(resultado["total_familias_vigiladas"]) +
          " familias; " + json.dumps(resultado["resumen"], ensure_ascii=False))


if __name__ == "__main__":
    main()
