"""Vetos editoriales explícitos para la misma edición: nunca inferir cancelaciones.

Una fila del CSV con Estado=cancelada/anulada/retirada, fecha y evidencia
verificable excluye esa edición de TODOS los caminos automáticos, incluso
si la fila no está marcada para publicar. Las ediciones de otra fecha
no se vetan automáticamente: deben revisarse si hay una reprogramación.
"""
from control_calidad import PROVINCES, valid_source
from deduplicacion import distance_set, same_place, similarity, valid_locality

VETO_STATES = frozenset({
    "cancelada", "cancelado", "anulada", "anulado", "retirada", "retirado",
})


def extract_vetoes(rows, date_parse, modes, normalize):
    """Solo decisiones expresas y verificadas; un registro incompleto bloquea el build."""
    vetoes = []
    for rowno, row in enumerate(rows, 2):
        if normalize(row.get("Estado")) not in VETO_STATES:
            continue
        try:
            name = str(row.get("Nombre") or "").strip()
            city = str(row.get("Localidad") or "").strip()
            province = str(row.get("Provincia") or "").strip()
            mode = modes.get(normalize(row.get("Modalidad")).upper())
            source = str(row.get("Fuente") or "").strip()
            verified = str(row.get("Verificado") or "").strip()
            day = date_parse(row.get("Fecha")).isoformat()
            if (not name or len(name) > 170 or not valid_locality(city)
                    or province not in PROVINCES or not mode
                    or not valid_source(source) or not verified):
                raise ValueError("faltan identidad, modalidad o evidencia HTTPS verificada")
            date_parse(verified)  # La decisión necesita una fecha documental explícita.
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Fila {rowno}: veto editorial inválido ({exc}); "
                "corrige la fila antes de publicar"
            ) from exc
        vetoes.append({
            "fecha": day, "nombre": name, "localidad": city,
            "provincia": province, "modalidad": mode,
            "distancia": str(row.get("Distancia") or "").strip(),
        })
    return vetoes


def is_vetoed(race, vetoes):
    """Misma fecha, provincia/municipio, modalidad y prueba; jamás solo URL o nombre.

    Sin distancia en el veto, se retiran todas las distancias de esa edición.
    Con una distancia específica, otras distancias documentadas se conservan.
    """
    for veto in vetoes:
        if (race.get("fecha") != veto["fecha"]
                or race.get("modalidad") != veto["modalidad"]
                or not same_place(race, veto)
                or not similarity(race.get("nombre"), veto["nombre"])):
            continue
        veto_distances = distance_set(veto)
        race_distances = distance_set(race)
        if veto_distances and race_distances and not (veto_distances & race_distances):
            continue
        return True
    return False


def exclude_vetoed(races, vetoes):
    """Filtra candidatas y respaldos antes de deduplicar o restaurar."""
    accepted = [r for r in races if not is_vetoed(r, vetoes)]
    return accepted, len(races) - len(accepted)
