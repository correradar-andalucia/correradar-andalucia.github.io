"""Estados de inscripción extraídos SOLO de listados/fichas ya consultados.

No sigue enlaces de inscripción, no accede a formularios, no almacena cupos ni
participantes. Una fecha límite anunciada no garantiza que queden plazas.
"""
from datetime import date, datetime, timedelta
import re
import unicodedata
from collections import Counter
from control_calidad import valid_source

STATES={"abierta","cerrada","agotada","proximamente","desconocida"}
LABELS={"abierta":"Abiertas según fuente","cerrada":"Cerradas según fuente",
        "agotada":"Agotadas según fuente","proximamente":"Próximamente",
        "desconocida":"Sin información actual"}
MAX_AGE_DAYS=1
MONTHS={n:i+1 for i,n in enumerate(
    ["enero","febrero","marzo","abril","mayo","junio","julio","agosto",
     "septiembre","octubre","noviembre","diciembre"])}

def norm(s):
    s=unicodedata.normalize("NFKD",str(s or "").casefold())
    return re.sub(r"\s+"," ","".join(c for c in s if not unicodedata.combining(c))).strip()

def title_key(name):
    return re.sub(r"\s*\((?:dorsales agotados|inscripciones agotadas|inscripciones cerradas)\)\s*$","",norm(name))

def identity(row):
    return (row.get("fecha"),title_key(row.get("nombre")),norm(row.get("localidad")),
            norm(row.get("provincia")),row.get("modalidad"))

def observation(state,source,today,**extra):
    return dict(inscripcion_estado=state,inscripcion_fuente=source,
                inscripcion_consultada=today.isoformat(),**extra)

def runnink_label(text,source,event_day,today):
    """Solo CTA de la misma URL de evento en el listado público."""
    label=norm(text).strip(" ›»→")
    states={"inscripciones":"abierta","inscripciones abiertas":"abierta",
            "inscripciones cerradas":"cerrada","dorsales agotados":"agotada",
            "inscripciones agotadas":"agotada","plazas agotadas":"agotada",
            "agotadas":"agotada","proximamente":"proximamente"}
    if label in states:
        return observation(states[label],source,today)
    match=re.fullmatch(r"apertura el (\d{1,2}) de ([a-z]+)(?: de (20\d\d))?",label)
    if not match:
        return {}
    month=MONTHS.get(match[2])
    if not month:
        return {}
    valid=[]
    for year in range(today.year,event_day.year+1):
        if match[3] and int(match[3])!=year:
            continue
        try: day=date(year,month,int(match[1]))
        except ValueError:continue
        if today<=day<=event_day:
            valid.append(day)
    if len(valid)==1:
        return observation("proximamente",source,today,inscripcion_apertura=valid[0].isoformat())
    # La etiqueta sigue siendo informativa, pero no inventar año ni apertura pasada.
    return observation("proximamente",source,today) if len(valid)>1 else {}

def faa_label(title,source,today):
    if re.search(r"\((?:dorsales|inscripciones|plazas) agotad[oa]s\)\s*$",norm(title)):
        return observation("agotada",source,today)
    if norm(title).endswith("(inscripciones cerradas)"):
        return observation("cerrada",source,today)
    return {}

def gcc_fields(parts,source,event_day,today):
    """Leer campos exactos del bloque de información, no precios ni texto promocional."""
    chunks=[" ".join(str(x).split()) for x in parts]
    start=next((i for i,c in enumerate(chunks) if norm(c)=="fecha inicio"),None)
    if start is None:
        return {}
    block=chunks[start:start+35]
    def field(label):
        values=[block[i+1] for i,c in enumerate(block[:-1]) if norm(c)==label]
        return values[0] if len(values)==1 else ""
    raw=field("cierre inscripcion")
    end=None
    try:
        end=datetime.strptime(raw,"%d-%m-%Y %H:%M")
    except ValueError:
        pass
    extra={}
    if end and end.date()<=event_day:
        extra=dict(inscripcion_limite=end.date().isoformat(),inscripcion_hora_limite=end.strftime("%H:%M"))
    states={norm(c) for c in chunks[start:start+65]}
    if "inscripciones cerradas" in states:
        state="cerrada"
    elif states & {"dorsales agotados","inscripciones agotadas","plazas agotadas"}:
        state="agotada"
    elif (("inscripcion (individual)" in states or "inscripcion (grupo)" in states)
          and field("plazas disponibles").isdigit() and int(field("plazas disponibles"))>0
          and extra and end.date()>=today):
        state="abierta"
    else:
        state="desconocida"
    if state=="desconocida" and not extra:
        return {}
    return observation(state,source,today,**extra)

FIELDS=("inscripcion_estado","inscripcion_fuente","inscripcion_consultada",
        "inscripcion_apertura","inscripcion_limite","inscripcion_hora_limite")

def valid_observation(row,today):
    if row.get("inscripcion_estado") not in STATES or not valid_source(row.get("inscripcion_fuente")):
        return False
    try:
        stamp=date.fromisoformat(row["inscripcion_consultada"])
        event=date.fromisoformat(row["fecha"])
        start=date.fromisoformat(row["inscripcion_apertura"]) if row.get("inscripcion_apertura") else None
        end=date.fromisoformat(row["inscripcion_limite"]) if row.get("inscripcion_limite") else None
    except (ValueError,TypeError,KeyError):
        return False
    if not 0<=(today-stamp).days<=MAX_AGE_DAYS or event<today:
        return False
    if (start and start>event) or (end and end>event) or (start and end and start>end):
        return False
    hour=row.get("inscripcion_hora_limite")
    return not hour or bool(end and re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",str(hour)))

def apply_current_registrations(races, live, today=None):
    """No recuperar estados del catálogo previo. Coincidencia inequívoca o desconocido."""
    today=today or date.today()
    by_key={}
    for row in live:
        if valid_observation(row,today):
            by_key.setdefault(identity(row),[]).append(row)
    keys=Counter(identity(r) for r in races)
    conflicts=0
    for race in races:
        for field in FIELDS:
            race.pop(field,None)
        key=identity(race)
        evidence=by_key.get(key,[]) if keys[key]==1 and not race.get("respaldo_temporal") else []
        if evidence:
            states={r["inscripcion_estado"] for r in evidence if r["inscripcion_estado"]!="desconocida"}
            deadlines={(r.get("inscripcion_limite"),r.get("inscripcion_hora_limite"))
                       for r in evidence if r.get("inscripcion_limite")}
            openings={r["inscripcion_apertura"] for r in evidence if r.get("inscripcion_apertura")}
            if len(states)>1 or len(deadlines)>1 or len(openings)>1:
                conflicts+=1
            else:
                # Mantener procedencia única; no atribuir plazos de otra fuente.
                chosen=max(evidence,key=lambda r:(r["inscripcion_estado"]!="desconocida",
                                                 bool(r.get("inscripcion_limite")),
                                                 bool(r.get("inscripcion_apertura")),
                                                 r["inscripcion_consultada"]))
                race.update({field:chosen[field] for field in FIELDS if field in chosen})
        race.setdefault("inscripcion_estado","desconocida")
    counts=Counter(r["inscripcion_estado"] for r in races)
    return {"por_estado":{s:counts[s] for s in sorted(STATES)},
            "con_plazo":sum(bool(r.get("inscripcion_limite")) for r in races),
            "conflictos":conflicts}
