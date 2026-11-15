"""Control editorial de duplicados antes de generar la web.

Un evento con varias distancias/modalidades puede tener fichas diferentes.
No deduplicar solo por nombre ni por URL de una cronometradora.
"""
from __future__ import annotations
from collections import Counter
from datetime import date
from difflib import SequenceMatcher
import hashlib
import re
import unicodedata

STOPWORDS = {"de","del","la","las","el","los","y","en","a","al","por","para",
             "carrera","popular","municipal","circuito","provincial","prueba"}
EDITION = re.compile(r"^(?:[ivxlcdm]{1,8}|[0-9]{1,3}[ªº]?)\s+(?=[a-záéíóúñ])",re.I)
DIST = re.compile(r"(?<!\d)(\d{1,3}(?:[.,]\d{1,3})?)\s*(?:km|kms|k\b)",re.I)

def norm(s):
    s=unicodedata.normalize("NFKD",str(s or "").casefold())
    s="".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s)).strip()

def canonical_name(name):
    value=norm(name)
    value=EDITION.sub("",value)
    return value

def tokens(name):
    return {t for t in canonical_name(name).split()
            if t not in STOPWORDS and len(t)>1}

def distance_set(r):
    raw=str(r.get("distancia") or "")
    result=set()
    for value in DIST.findall(raw):
        try:result.add(round(float(value.replace(",",".")),2))
        except ValueError:pass
    if not result:
        km=r.get("km")
        try:
            n=float(km)
            if n>0:result.add(round(n,2))
        except (ValueError,TypeError):pass
    return result

def similarity(a,b):
    x,y=canonical_name(a),canonical_name(b)
    if not x or not y:return False
    if x==y:return True
    if SequenceMatcher(None,x,y).ratio()>=.87:return True
    ta,tb=tokens(a),tokens(b)
    if len(ta)<2 or len(tb)<2:return False
    score=len(ta&tb)/len(ta|tb)
    coverage=len(ta&tb)/min(len(ta),len(tb))
    return score>=.77 and coverage>=.82

def same_place(a,b):
    return (norm(a.get("provincia"))==norm(b.get("provincia"))
            and norm(a.get("localidad"))==norm(b.get("localidad"))
            and bool(norm(a.get("localidad"))))

def same_event(a,b):
    if a.get("fecha")!=b.get("fecha") or not same_place(a,b):return False
    ma,mb=a.get("modalidad"),b.get("modalidad")
    if ma and mb and ma!=mb:return False
    if not similarity(a.get("nombre"),b.get("nombre")):return False
    da,db=distance_set(a),distance_set(b)
    # Carreras de 5 km y media maratón son dos modalidades, aunque compartan título.
    if da and db and not da.intersection(db):return False
    return True

def conflicting_date(a,b):
    if not same_place(a,b) or not similarity(a.get("nombre"),b.get("nombre")):return False
    try:
        da=date.fromisoformat(str(a["fecha"]));db=date.fromisoformat(str(b["fecha"]))
    except (KeyError,ValueError):return False
    if not 0<abs((da-db).days)<=45:return False
    ma,mb=a.get("modalidad"),b.get("modalidad")
    if ma and mb and ma!=mb:return False
    x,y=distance_set(a),distance_set(b)
    return not x or not y or bool(x&y)

def origins(item):
    result=item.get("fuentes_origen") or []
    if not isinstance(result,list):result=[]
    o=item.get("origen")
    return list(dict.fromkeys([x for x in [*result,o] if isinstance(x,str) and x]))

def record_sources(target,item):
    target["fuentes_origen"]=list(dict.fromkeys([*origins(target),*origins(item)]))
    links=target.get("enlaces_fuente") or []
    for url in [item.get("fuente"), item.get("enlace")]:
        if isinstance(url,str) and url.startswith("https://") and url not in links:
            links.append(url)
    target["enlaces_fuente"]=links[:12]

def unique_slug(item,slugify,seen):
    core=slugify(f"{item['nombre']}-{item['localidad']}-{item['fecha']}")
    if core not in seen:return core
    # Distancias distintas del mismo día necesitan URLs estables separadas.
    marker=f"{item.get('modalidad','')}-{item.get('distancia','')}"
    alt=slugify(f"{core}-{marker}")
    if alt not in seen:return alt
    suffix=hashlib.sha1((marker+"|"+str(item.get("fuente",""))).encode()).hexdigest()[:8]
    alt=f"{core[:74]}-{suffix}"
    if alt not in seen:return alt
    raise ValueError("Colisión no recuperable de URL: "+core)

def verify_unique(races):
    slugs=[r.get("slug") for r in races]
    if any(not s for s in slugs) or len(slugs)!=len(set(slugs)):
        raise ValueError("PUBLICACIÓN BLOQUEADA: URLs de fichas duplicadas")
    for i,a in enumerate(races):
        for b in races[i+1:]:
            if same_event(a,b):
                raise ValueError("PUBLICACIÓN BLOQUEADA: misma carrera/fecha/localidad/distancia: "
                                 +a.get("nombre","")+" / "+b.get("nombre",""))
    return True

def combine(approved,candidates,slugify,km_parse,with_audit=False):
    """Combina: prioridad a aprobadas; directas antes que fotografías antiguas.

    Devuelve también auditoría opcional de duplicados realmente descartados.
    """
    # Mantener el orden de aprobadas tal como las ordenó la publicación.
    # Entre candidatas, las lecturas directas prevalecen sobre datos puntuales.
    candidates=sorted(candidates,key=lambda r:
        (1 if "Cotejada" in str(r.get("estado","")) else 0, str(r.get("fecha",""))))
    rows=[(True,r) for r in approved]+[(False,r) for r in candidates]
    results=[];locks=[];seen=set()
    audit={"entradas_aprobadas":len(approved),"candidatas_entrantes":len(candidates),
           "duplicados_fusionados":0,"fechas_en_conflicto":0,
           "ejemplos_duplicados":[],"ejemplos_conflictos":[]}
    for is_approved,item in rows:
        r=dict(item)
        r.setdefault("distancia","")
        r.setdefault("desnivel","")
        r.setdefault("precio","")
        r.setdefault("bolsa","")
        r.setdefault("track","")
        r.setdefault("verificado",date.today().isoformat())
        r.setdefault("estado","Por confirmar · fuente directa")
        r["km"]=km_parse(r.get("distancia",""))
        r["fuentes_origen"]=origins(r)
        matches=next((old for old in results if same_event(old,r)),None)
        if matches is not None:
            audit["duplicados_fusionados"]+=1
            if len(audit["ejemplos_duplicados"])<30:
                audit["ejemplos_duplicados"].append({"fecha":r["fecha"],
                    "municipio":r.get("localidad"),"descartada":r.get("nombre"),
                    "conservada":matches.get("nombre"),"origen":r.get("origen")})
            record_sources(matches,r)
            if not matches.get("distancia") and not is_approved and r.get("distancia"):
                matches["distancia"]=r["distancia"]
                matches["km"]=km_parse(r["distancia"])
            continue
        different=next((old for old in results if conflicting_date(old,r)),None)
        if different is not None and not is_approved:
            # No publicar dos fechas contradictorias de un evento como si fueran pruebas distintas.
            audit["fechas_en_conflicto"]+=1
            if len(audit["ejemplos_conflictos"])<30:
                audit["ejemplos_conflictos"].append({"nombre":r.get("nombre"),
                    "municipio":r.get("localidad"),"fecha_desestimada":r.get("fecha"),
                    "fecha_conservada":different.get("fecha"),"fuente":r.get("fuente")})
            record_sources(different,r)
            continue
        if r.get("slug") not in seen:
            slug=r.get("slug") or unique_slug(r,slugify,seen)
        else:
            slug=unique_slug(r,slugify,seen)
        r["slug"]=slug
        seen.add(slug)
        results.append(r)
    verify_unique(results)
    audit["fichas_finales"]=len(results)
    audit["fichas_aprobadas_conservadas"]=sum(1 for r in results if r.get("origen") is None and
                                             "confirmar" not in norm(r.get("estado")))
    audit["urls_unicas"]=True
    return (results,audit) if with_audit else results
