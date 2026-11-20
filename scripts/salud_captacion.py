"""Detecta pérdidas silenciosas de lectura sin inferir bajas ni ampliar captación.

Solo compara hechos de la última publicación confirmada y la captación ya
autorizada; no visita fuentes, no guarda HTML y no rehabilita lectores pausados.
"""
from collections import Counter
from datetime import date

MIN_HISTORICO = 3
DIAS_REFERENCIA = 7
MIN_ENLACES_SIN_RESULTADO = 3


def _referencia_viva(previous, allowed, today):
    """Contar solo pruebas futuras con consulta original reciente y no restaurada."""
    counts = Counter()
    for row in previous:
        if row.get("confirmada") or row.get("respaldo_temporal") or row.get("fecha_origen") != "fuente":
            continue
        try:
            day = date.fromisoformat(row["fecha"])
            consulted = date.fromisoformat(row["consultado"])
        except (KeyError, TypeError, ValueError):
            continue
        if day < today or not 0 <= (today - consulted).days <= DIAS_REFERENCIA:
            continue
        # Una fusión puede tener más de un lector comprobado en el mismo ciclo.
        sources = row.get("fuentes_origen")
        if not isinstance(sources, list):
            sources = []
        origins = {src for src in [row.get("origen"), *sources] if isinstance(src, str)}
        for src in origins & allowed:
            counts[src] += 1
    return counts


def verificar_lecturas(candidates, previous, report, today=None):
    """Marcar lecturas con 0 resultados frente a >=3 eventos recientes confirmados.

    La ausencia de antecedentes suficientes, la pausa deliberada y el modo
    offline nunca son una evidencia de error. Las caídas parciales y fichas
    enlazadas sin resultados se anotan para revisión, sin bloquear por sí solas.
    """
    today = today or date.today()
    if report.get("modo") == "Prueba local sin conexión":
        return {"sospechosas": {}, "avisos": {}, "revision_historico_dias": DIAS_REFERENCIA}
    sources = report.get("fuentes") or {}
    names = report.get("nombres_fuentes_habilitadas") or []
    allowed = set(names)
    counts = _referencia_viva(previous, allowed, today)
    actual = Counter(row.get("origen") for row in candidates)
    suspect, warnings = {}, {}
    for name in sorted(allowed):
        info = sources.get(name)
        if (not isinstance(info, dict) or info.get("estado") != "leida"
                or info.get("acceso_restringido") or info.get("detalle_restringido")):
            continue
        before, now = counts[name], actual[name]
        # La comparación se hace sobre salidas reales, no solo sobre el estado
        # "leida" que devuelve collect() tras un HTTP 200.
        declared = info.get("candidatas")
        if type(declared) is int and declared != now:
            suspect[name] = {"motivo": "recuento_inconsistente",
                             "futuras_previas": before, "obtenidas": now}
        elif before >= MIN_HISTORICO and now == 0:
            suspect[name] = {"motivo": "cero_tras_historico",
                             "futuras_previas": before, "obtenidas": 0}
        elif before >= MIN_HISTORICO and now * 2 < before:
            warnings[name] = {"motivo": "descenso_parcial",
                              "futuras_previas": before, "obtenidas": now}
        elif (before < MIN_HISTORICO and now == 0
              and (info.get("enlaces_detectados") or 0) >= MIN_ENLACES_SIN_RESULTADO):
            warnings[name] = {"motivo": "enlaces_sin_carreras",
                              "enlaces_detectados": info["enlaces_detectados"], "obtenidas": 0}
    for name, detail in suspect.items():
        info = sources[name]
        info["estado"] = "lectura_sospechosa"
        info["motivo"] = ("Resultados no fiables: "
                         f"{detail['obtenidas']} fichas extraídas frente a "
                         f"{detail['futuras_previas']} futuras de la última publicación"
                         if detail["motivo"] == "cero_tras_historico"
                         else "Resultados no fiables: el recuento del lector no coincide con sus fichas")
        info["lectura_sospechosa"] = True
        info["futuras_previas"] = detail["futuras_previas"]
        info["obtenidas_actualmente"] = detail["obtenidas"]
    report["salud_captacion"] = {
        "sospechosas": suspect, "avisos": warnings,
        "revision_historico_dias": DIAS_REFERENCIA,
    }
    return report["salud_captacion"]
