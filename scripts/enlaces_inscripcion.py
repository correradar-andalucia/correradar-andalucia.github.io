"""Enlazar inscripciones de Global Tempo SIN consultarlo ni usarlo para descubrir fechas.

El catálogo de enlaces fue cotejado puntualmente. Solo se asocia una URL de
inscripción cuando una fuente institucional, federativa u organizadora distinta
identifica la MISMA carrera, fecha, municipio y modalidad. Nunca crea carreras.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse
from deduplicacion import same_event

FILE = Path(__file__).resolve().parents[1]/"data"/"fichas_globaltempo_2026-11-17.json"
INDEPENDENT = frozenset({
    "fadmes","faa","dipgra","diphuelva","circuito_cordoba","gcc",
    "cruzandolameta","runnink","gesconchip","dorsalchip",
})
GT_HOSTS = {"www.global-tempo.com","global-tempo.com",
            "gateway.global-tempo.com"}


def gt_url(link):
    if not isinstance(link,str):
        return False
    p=urlparse(link)
    return bool(p.scheme=="https" and p.hostname in GT_HOSTS
                and p.path=="/carreras.php"
                and len(p.query.split("&"))==1
                and p.query.startswith("id=")
                and p.query[3:].isdigit())


def match_registrations(races, independently_verified, catalog=None):
    """Añade URL de inscripción SOLO donde otra fuente prueba la edición.

    El cotejo manual es un directorio de ENLACES, no una entrada de carreras.
    Ni el nombre ni la fecha de ese directorio pueden originar una nueva ficha.
    """
    if catalog is None:
        catalog=json.loads(FILE.read_text(encoding="utf-8"))
    links=catalog.get("carreras",[])
    verified=[item for item in independently_verified
              if item.get("origen") in INDEPENDENT
              and not str(item.get("fuente","")).startswith(
                  ("https://www.global-tempo.com","https://gateway.global-tempo.com"))]
    stats={"enlaces_disponibles":len(links),
           "asociados_con_fuente_independiente":0,
           "sin_confirmacion_independiente":0,
           "ambiguedades":0}
    for link in links:
        url=link.get("fuente")
        if not gt_url(url):
            continue
        matching=[r for r in races if same_event(r,link)]
        independent=[r for r in verified if same_event(r,link)]
        if len(matching)!=1 or len(independent)!=1:
            if len(matching)>1 or len(independent)>1:
                stats["ambiguedades"]+=1
            else:
                stats["sin_confirmacion_independiente"]+=1
            continue
        race=matching[0]
        source=independent[0]
        # No avalar una carrera solo porque su nombre figura en GT:
        # la fecha y provincia las debe confirmar la segunda fuente.
        if (race.get("fecha")!=source.get("fecha")
                or race.get("provincia")!=source.get("provincia")):
            stats["ambiguedades"]+=1
            continue
        race["inscripcion_enlace"]=url
        race["inscripcion_cotejada"]=catalog["revision"]
        # Si el registro original era un antiguo cotejo de GT, trasladamos
        # la atribución a la fuente que realmente confirma esa edición.
        if urlparse(str(race.get("fuente",""))).hostname in GT_HOSTS:
            race["fuente"]=source["fuente"]
            race.pop("fuente_nombre",None)
        # El enlace principal debe ser una ficha/inscripción específica.
        # Solo reemplazar la portada del calendario general, no otra
        # inscripción concreta que ya esté funcionando.
        original=str(race.get("enlace",""))
        p=urlparse(original)
        generic=(p.path in ("","/","/index.php","/calendario-fam/",
                            "/carreraspopulares/","/inscripciones/",
                            "/servicios/areas/deportes/deporte-competicion/circuito-provincial-campo-a-traves/"))
        if generic or p.hostname in GT_HOSTS:
            race["enlace"]=url
        stats["asociados_con_fuente_independiente"]+=1
    return stats
