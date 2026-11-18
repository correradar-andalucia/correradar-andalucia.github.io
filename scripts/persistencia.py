"""Respaldo limitado de la propia última publicación y lista de distancias pendientes."""
from datetime import date
import json
from pathlib import Path
from urllib.parse import urlparse

from control_calidad import valid_source, MODES, PROVINCES
from deduplicacion import same_event, conflicting_date, valid_locality

MAX_AGE=7

def read_previous(path):
    if not path:
        return []
    try:
        p=Path(path)
        if p.stat().st_size>3_000_000:
            return []
        doc=json.loads(p.read_text(encoding="utf-8"))
        rows=doc.get("carreras")
        return [r for r in rows if isinstance(r,dict)] if isinstance(rows,list) else []
    except (OSError,ValueError,TypeError,AttributeError):
        return []

def restore_missing(races, previous, report, slugify, km_parse, today=None):
    """Solo ante fallo temporal acreditado, nunca ante ausencia en lectura correcta.

    No recupera eventos de una fuente pausada ni reintroduce fechas contradichas.
    El dato conserva la fecha de consulta anterior: no se renueva al reutilizarlo.
    """
    from captacion import SOURCES
    today=today or date.today()
    statuses=report.get("fuentes") or {}
    allowed=set(report.get("nombres_fuentes_habilitadas") or []) & set(SOURCES)
    failed={s for s in allowed if statuses.get(s,{}).get("estado")=="no disponible"
            and statuses[s].get("fallo_temporal") is True}
    restored=[]
    for old in previous:
        origin=old.get("origen")
        if origin not in failed or old.get("confirmada"):
            continue
        if not isinstance(old.get("nombre"),str) or not old["nombre"] or len(old["nombre"])>170 or not valid_locality(old.get("localidad")):
            continue
        if old.get("provincia") not in PROVINCES or old.get("modalidad") not in MODES:
            continue
        try:
            day=date.fromisoformat(old["fecha"])
            stamp=date.fromisoformat(old["consultado"])
        except (KeyError,TypeError,ValueError):
            continue
        if day<today or day.year>today.year+2 or not 0<=(today-stamp).days<=MAX_AGE:
            continue
        source=old.get("fuente")
        link=old.get("enlace")
        if not valid_source(source) or not valid_source(link):
            continue
        host=urlparse(SOURCES[origin]).hostname
        def host_key(url):
            return (urlparse(url).hostname or "").removeprefix("www.")
        if host_key(source)!=host.removeprefix("www.") or host_key(link)!=host.removeprefix("www."):
            continue
        # No recuperar un evento si otra fuente ya lo ha leído o cambiado de fecha.
        if any(same_event(old,r) or conflicting_date(old,r) for r in races+restored):
            continue
        slug=old.get("slug")
        if not isinstance(slug,str) or slugify(slug)!=slug or any(r.get("slug")==slug for r in races+restored):
            continue
        row={k:old.get(k,"") for k in ("fecha","nombre","localidad","provincia","modalidad","enlace","fuente","slug","origen")}
        row.update(confirmada=False,fecha_origen="catalogo",consultado=stamp.isoformat(),
                   estado="Cotejada · fuente temporalmente no disponible",respaldo_temporal=True,
                   distancia="",distancia_origen="",hora="",hora_origen="",km=0,
                   desnivel="",precio="",bolsa="",track="",verificado="",
                   fuentes_origen=[origin],enlaces_fuente=[source])
        # Solo datos de distancia explícitos de la propia fuente, con fecha original.
        from distancias import extract_distance
        dist=old.get("distancia")
        dist_source=old.get("distancia_fuente")
        try:
            checked=date.fromisoformat(old.get("distancia_cotejada"))
        except (TypeError,ValueError):
            checked=None
        if (isinstance(dist,str) and dist and extract_distance(dist)==dist
            and dist_source in (source,link) and checked and 0<=(today-checked).days<=30):
            row.update(distancia=dist,distancia_origen="catalogo",distancia_fuente=dist_source,
                       distancia_cotejada=checked.isoformat(),km=km_parse(dist))
            if old.get("distancia_aproximada") is True:
                row["distancia_aproximada"]=True
        restored.append(row)
    races.extend(restored)
    races.sort(key=lambda r:(r["fecha"],r["nombre"].casefold()))
    return {"recuperadas":len(restored),"fuentes_con_fallo_temporal":sorted(failed),
            "caducidad_dias":MAX_AGE}

def distance_backlog(races,today=None):
    """Inventario exacto por edición: no contiene datos personales ni estimaciones como km."""
    today=today or date.today()
    rows=[]
    for race in races:
        if race.get("distancia"):
            continue
        try: days=(date.fromisoformat(race["fecha"])-today).days
        except (KeyError,ValueError,TypeError):continue
        if days<0:continue
        rows.append({k:race.get(k,"") for k in ("fecha","nombre","localidad","provincia","modalidad","origen","fuente","enlace","slug")}
                    | {"dias_hasta_carrera":days,
                       "estado":"orientativa" if race.get("distancia_orientativa") else "pendiente",
                       "prioridad":"alta" if days<=30 else "media" if days<=90 else "baja"})
    rows.sort(key=lambda r:(r["fecha"],r["provincia"],r["nombre"]))
    return {"fecha_revision":today.isoformat(),"total":len(rows),
            "orientativas":sum(r["estado"]=="orientativa" for r in rows),
            "pendientes":rows}
