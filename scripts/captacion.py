"""Captación prudente de fechas de calendarios públicos (sin datos de personas).
Los resultados siempre quedan en estado 'Por confirmar'; NO se aprueban solos.
No se eluden bloqueos, robots ni controles de acceso.
"""
from __future__ import annotations
from datetime import date, datetime
from html.parser import HTMLParser
from functools import lru_cache
from html import unescape
import time
from urllib.parse import urlparse, urljoin, unquote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import socket
from urllib.robotparser import RobotFileParser
import re
import unicodedata
import os
import json
from distancias import (extract_distance, extract_races_section,
                       extract_narrative_distance, extract_booking_distance,
                       extract_modalities_distance)

USER_AGENT = "CorreRadarAndaluciaBot/0.1 (+mailto:correradarandalucia@gmail.com)"
MAX_DETALLES_POR_FUENTE = 24
# Lectores con reserva concreta o general documentada. No implica desactivación.
FUENTES_CON_RESERVAS_DOCUMENTADAS = {"fadmes", "dipgra", "faa", "runnink", "gesconchip"}
MAX_ENRIQUECIMIENTO_RUNNINK = 12
SOURCES = {
    "fadmes": "https://fadmes.es/calendario-fam/",
    "dorsalchip": "https://dorsalchip.es/view/Inicio.aspx",
    "cruzandolameta": "https://www.cruzandolameta.es/pruebas/",
    "faa": "https://atletismofaa.es/carreraspopulares/",
    "gcc": "https://gccsportevents.es/index.php",
    "runnink": "https://www.runnink.com/inscripciones/",
    "gesconchip": "https://gesconchip.es/app/proximas-pruebas",
    "dipgra": "https://www.dipgra.es/servicios/areas/deportes/deporte-competicion/circuito-provincial-campo-a-traves/",
    "diphuelva": "https://www.diphuelva.es/deportes/contenidos/Circuitos-Carreras-Atleticas-2026/",
    "circuito_cordoba": "https://www.carreraspopularescordoba.com/",
}
PROVINCES = {"ALMERIA":"Almería","CADIZ":"Cádiz","CORDOBA":"Córdoba",
             "GRANADA":"Granada","HUELVA":"Huelva","JAEN":"Jaén",
             "MALAGA":"Málaga","SEVILLA":"Sevilla"}
SKIP = re.compile(r"\b(?:triatl[oó]n|duatl[oó]n|ciclismo|cicloturismo|btt|mtb|"
                  r"paddle\s*surf|nataci[oó]n|jabalina|lanzamiento|senderismo|"
                  r"escalada|barranquismo|marcha\s+senderista)\b",re.I)

def canon(s):
    s=unicodedata.normalize("NFKD",str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).upper().strip()

def compact(s):
    return re.sub(r"\s+"," ",str(s or "")).strip()

def get_date(s):
    m=re.search(r"\b(\d{1,2})/(\d{1,2})/(20\d\d)\b",str(s))
    if not m:return None
    try:return date(int(m[3]),int(m[2]),int(m[1]))
    except ValueError:return None

class CalendarParser(HTMLParser):
    """Extrae tablas y textos por elemento de ancla sin depender de estilos CSS."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows=[];self.cells=[];self.cell=None
        self.in_row=False;self.in_anchor=False;self.anchor=None;self.anchors=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="tr":
            self.in_row=True;self.cells=[]
        if tag in ("td","th") and self.in_row:
            self.cell=[]
        if tag=="a":
            self.in_anchor=True;self.anchor={"href":a.get("href",""),"parts":[]}
    def handle_endtag(self,tag):
        if tag in ("td","th") and self.cell is not None and self.in_row:
            self.cells.append(compact(" ".join(self.cell)));self.cell=None
        if tag=="tr" and self.in_row:
            if self.cells:self.rows.append(self.cells)
            self.in_row=False;self.cells=[]
        if tag=="a" and self.in_anchor:
            if self.anchor:
                self.anchor["text"]=compact(" ".join(self.anchor["parts"]))
                self.anchors.append(self.anchor)
            self.in_anchor=False;self.anchor=None
    def handle_data(self,data):
        s=compact(data)
        if not s:return
        if self.cell is not None:self.cell.append(s)
        if self.in_anchor and self.anchor is not None:self.anchor["parts"].append(s)

def parse_fadmes(html,today=None):
    today=today or date.today()
    p=CalendarParser();p.feed(html)
    found=[]
    for c in p.rows:
        if len(c)<7:continue
        d=get_date(c[0]);kind=canon(c[2]);name=c[3];city=c[5];province=PROVINCES.get(canon(c[6]))
        if not d or not today<=d or d.year>today.year+2:continue
        if not province or not city or not name or len(name)>170:continue
        if not ("CXM" in kind or "CARRERAS POR MONTANA" in kind):continue
        if SKIP.search(name):continue
        modality="ULTRA" if "ULTRA" in canon(name) else "TRAIL"
        found.append({"fecha":d.isoformat(),"nombre":name,"localidad":city,"provincia":province,
                      "modalidad":modality,"distancia":extract_distance(name),"fuente":SOURCES["fadmes"],
                      "enlace":SOURCES["fadmes"],"origen":"fadmes"})
    return found

def parse_dorsalchip(html,today=None):
    """Acepta únicamente fichas con fecha, nombre y municipio inequívocos."""
    today=today or date.today()
    parser=CalendarParser();parser.feed(html)
    found=[];seen=set()
    for anchor in parser.anchors:
        url=urljoin(SOURCES["dorsalchip"],anchor["href"])
        parsed=urlparse(url)
        if parsed.hostname not in ("dorsalchip.es","www.dorsalchip.es"):continue
        if not re.match(r"^/carrera/20\d\d/\d{1,2}/\d{1,2}/[^/]+\.aspx$",parsed.path,re.I):continue
        parts=[compact(p) for p in anchor["parts"] if compact(p)]
        if not parts:continue
        day=get_date(anchor["text"])
        if not day or day<today or day.year>today.year+2:continue
        loc_index=next((i for i,p in enumerate(parts) if re.fullmatch(
            r".{2,90},\s*(Almería|Cádiz|Córdoba|Granada|Huelva|Jaén|Málaga|Sevilla)",p,re.I)),None)
        name="";city="";province=""
        if loc_index is not None and loc_index>0:
            loc=parts[loc_index]
            city,prov=loc.rsplit(",",1)
            province=PROVINCES.get(canon(prov),"")
            name=re.sub(r"^\d{1,2}/\d{1,2}/20\d\d\s*","",compact(" ".join(parts[:loc_index])))
        if not name:
            # Muchos enlaces incluyen nombre y localidad en un mismo nodo HTML.
            # La ruta de la propia ficha permite separar con confianza el título.
            stem=unquote(parsed.path.rsplit("/",1)[-1][:-5])
            slug_words=[re.sub(r"[^A-Z0-9]","",canon(w)) for w in re.split(r"[_\-\s]+",stem)]
            slug_words=[x for x in slug_words if x]
            body=re.sub(r"^\d{1,2}/\d{1,2}/20\d\d\s*","",anchor["text"])
            body=re.sub(r"\bPrueba cronometrada por dorsalChip\b.*$","",body,flags=re.I).strip()
            words=body.split()
            def token(w):return re.sub(r"[^A-Z0-9]","",canon(w))
            if slug_words and len(words)>len(slug_words):
                if [token(w) for w in words[:len(slug_words)]]==slug_words:
                    remaining=compact(" ".join(words[len(slug_words):]))
                    place=re.fullmatch(r"(.{2,90}),\s*(Almería|Cádiz|Córdoba|Granada|Huelva|Jaén|Málaga|Sevilla)",remaining,re.I)
                    if place:
                        name=compact(" ".join(words[:len(slug_words)]))
                        city=compact(place.group(1))
                        province=PROVINCES.get(canon(place.group(2)),"")
        if not name or not city or not province or len(name)>170:continue
        if SKIP.search(name) or re.search(r"\b(?:traves[ií]a\s+a\s+nado|marcha\s+solidaria)\b",name,re.I):continue
        key=canon(name)
        modality=("OCR" if re.search(r"\bOCR\b|OBSTACUL",key) else
                  "ULTRA" if "ULTRA" in key else
                  "TRAIL" if re.search(r"TRAIL|CXM|MONTANA",key) else
                  "CROSS" if "CROSS" in key else "RUNNING")
        identity=(day.isoformat(),canon(name),canon(city))
        if identity in seen:continue
        seen.add(identity)
        found.append({"fecha":day.isoformat(),"nombre":name,"localidad":city,"provincia":province,
                      "modalidad":modality,"distancia":extract_distance(name),"fuente":url,"enlace":url,"origen":"dorsalchip"})
    return found


MONTHS = {s:i+1 for i,s in enumerate(
    ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"])}

class RaceText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.words=[];self.heading=[];self.in_h1=False;self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style"):self.hidden+=1
        if tag=="h1":self.in_h1=True
    def handle_endtag(self,tag):
        if tag in ("script","style") and self.hidden:self.hidden-=1
        if tag=="h1":self.in_h1=False
    def handle_data(self,data):
        if self.hidden:return
        t=compact(data)
        if t:self.words.append(t)
        if t and self.in_h1:self.heading.append(t)

def cruzando_links(page):
    p=CalendarParser();p.feed(page)
    urls=[];seen=set()
    for a in p.anchors:
        target=urljoin(SOURCES["cruzandolameta"],a["href"])
        parsed=urlparse(target)
        if parsed.hostname!="www.cruzandolameta.es":continue
        if not re.fullmatch(r"/pruebas/[a-z0-9-]+/?",parsed.path):continue
        if target not in seen:
            seen.add(target);urls.append(target)
    return urls[:18]

def parse_cruzando_detail(page,source_url,today=None,diagnostico=None):
    """Usar fecha y localidad explícitas de la ficha, sin confundir recintos.

    Las razones de descarte son códigos agregables, no contenido de la fuente.
    """
    today=today or date.today()
    def descartar(motivo):
        if diagnostico is not None:
            diagnostico["motivo"]=motivo
        return None

    parser=RaceText();parser.feed(page)
    name=compact(" ".join(parser.heading))
    if not name or len(name)>170:
        return descartar("titulo_invalido")
    if SKIP.search(name):
        return descartar("deporte_excluido")
    full=compact(" ".join(parser.words))
    pos=full.find(name)
    primary=full[pos+len(name):] if pos>=0 else full
    primary=re.split(r"También te puede interesar|Más pruebas en",primary,maxsplit=1,flags=re.I)[0]
    if re.search(r"\bcancelad[ao]s?\b|\banulad[ao]s?\b",primary[:600],re.I):
        return descartar("cancelada")
    m=re.search(r"\b(\d{1,2})\s+de\s+("+ "|".join(MONTHS.keys())+
                r")\s+de\s+(20\d\d)\b",primary[:650],re.I)
    if m:
        try:d=date(int(m[3]),MONTHS[m[2].lower()],int(m[1]))
        except ValueError:return descartar("fecha_no_verificable")
    else:
        d=get_date(primary[:650])
    if not d or d<today or d.year>today.year+2:
        return descartar("fecha_no_verificable")

    key=canon(name)
    category=("HIBRIDA" if re.search(r"HYROX|DEKA",key) else
              "OCR" if re.search(r"\bOCR\b|OBSTACUL",key) else
              "ULTRA" if "ULTRA" in key else
              "TRAIL" if re.search(r"TRAIL|CXM|MONTANA|SILVESTRAIL",key) else
              "CROSS" if "CROSS" in key else "RUNNING")
    if category=="RUNNING" and not re.search(
            r"CARRERA|MARATON|FONDO|SUBIDA|RUNNING|SAN SILVESTRE|RELEVOS",key):
        return descartar("modalidad_no_verificable")

    # En las fichas actuales, la primera línea contiene fecha, hora y recinto
    # juntos. Ese texto NO es una localidad: leer el campo "Dónde" aislado.
    # En fichas históricas sintéticas sin tal sección, aceptar únicamente un
    # nodo de texto independiente que termine en "(Provincia)".
    province_expr="|".join(re.escape(p) for p in PROVINCES.values())
    location_pattern=re.compile(r"^(.{2,140}?)\s*\(("+province_expr+r")\)\s*$",re.I)
    place_field=None
    for idx,word in enumerate(parser.words):
        if canon(word).strip(" :¡!¿?")=="DONDE":
            place_field=parser.words[idx+1] if idx+1<len(parser.words) else ""
            break
    if place_field is None:
        for word in parser.words:
            # No usar municipios de fichas sugeridas o menús del pie.
            if re.search(r"También te puede interesar|Más pruebas en|Ver calendario",word,re.I):
                break
            if re.search(r"\b\d{1,2}:\d{2}\b",word):
                continue
            if location_pattern.fullmatch(word):
                place_field=word
                break
    match=location_pattern.fullmatch(compact(place_field))
    if not match:
        return descartar("ubicacion_sin_provincia_verificable")
    venue,province=compact(match.group(1)),next(
        p for p in PROVINCES.values() if canon(p)==canon(match.group(2)))
    # "La Alquería (Adra) (Almería)" menciona explícitamente el municipio.
    explicit=re.search(r"\(([^()]{2,70})\)\s*$",venue)
    place=compact(explicit.group(1)) if explicit else venue
    if not explicit:
        # Pabellón de Atarfe + la misma localidad en el nombre: única
        # excepción acotada; no inferir municipios desde plazas o estadios.
        match_pavilion=re.fullmatch(
            r"Pabell[oó]n (?:Cubierto )?de ([^,\d]{2,65})",place,re.I)
        if match_pavilion and canon(match_pavilion.group(1)) in key:
            place=compact(match_pavilion.group(1))
        elif re.match(
            r"(?i)^(?:pabell[oó]n|palacio(?:\\s+de\\s+deportes)?|plaza|parque|calle|avenida|avda|paseo|"
            r"aparcamiento|parking|estadio|polideportivo|instituto|"
            r"centro|complejo|carretera|explanada)\b",place):
            return descartar("recinto_sin_municipio_verificable")
    if (not 2<=len(place)<=90 or re.search(r"\b\d{1,2}:\d{2}\b",place)
            or re.search(r"\b(?:inscripciones|salida a las|sábado|domingo)\b",place,re.I)
            or re.search(r"[<>]",place)):
        return descartar("municipio_no_verificable")
    return {"fecha":d.isoformat(),"nombre":name,"localidad":place,"provincia":province,
            "modalidad":category,"distancia":extract_distance(name),"enlace":source_url,
            "fuente":source_url,"origen":"cruzandolameta"}

@lru_cache(maxsize=8)
def get_robots(host):
    """Robots por dominio, nunca saltar un fallo de consulta salvo HTTP 404."""
    robot=RobotFileParser()
    robots_url="https://"+host+"/robots.txt"
    try:
        with urlopen(Request(robots_url,headers={"User-Agent":USER_AGENT}),timeout=12) as response:
            if response.getcode()!=200:raise RuntimeError("robots.txt no verificable")
            lines=response.read(250_001)
            if len(lines)>250_000:raise RuntimeError("robots.txt demasiado grande")
        robot.parse(lines.decode("utf-8","replace").splitlines())
    except HTTPError as ex:
        if ex.code!=404:raise RuntimeError(f"robots.txt HTTP {ex.code}") from ex
        robot.parse([])
    except Exception as ex:
        raise RuntimeError("No fue posible consultar robots.txt: "+type(ex).__name__) from ex
    return robot


def dorsal_links(page,today=None):
    today=today or date.today()
    p=CalendarParser();p.feed(page)
    found=[];seen=set()
    for a in p.anchors:
        url=urljoin(SOURCES["dorsalchip"],a["href"])
        u=urlparse(url)
        if u.hostname not in ("dorsalchip.es","www.dorsalchip.es"):continue
        match=re.fullmatch(r"/carrera/(20\d\d)/(\d{1,2})/(\d{1,2})/[^/]+\.aspx",u.path,re.I)
        if not match:continue
        try: day=date(*map(int,match.groups()))
        except ValueError:continue
        if day<today or day.year>today.year+2 or url in seen:continue
        seen.add(url);found.append((day,url))
    # No gastar el presupuesto de fichas en ediciones pasadas.
    return [url for _,url in sorted(found)[:MAX_DETALLES_POR_FUENTE]]

def dorsal_detail(page,link,today=None):
    today=today or date.today()
    p=RaceText();p.feed(page)
    texts=p.words
    for i,t in enumerate(texts[:100]):
        if not re.fullmatch(r"\d{1,2}/\d{1,2}/20\d\d",t):continue
        d=get_date(t)
        if not d or d<today or d.year>today.year+2:continue
        if i<1 or i+2>=len(texts):continue
        name=compact(texts[i-1]);city=compact(texts[i+1]);province=PROVINCES.get(canon(texts[i+2]))
        if not name or not city or not province or len(name)>170 or len(city)>100:continue
        if SKIP.search(name):continue
        if re.search(r"\b(?:marcha\s+solidaria|traves[ií]a\s+a\s+nado|preinscripci[oó]n)\b",name,re.I):continue
        key=canon(name)
        if not re.search(r"CARRERA|TRAIL|CXM|RUN|CROSS|ULTRA|MARATON|SAN SILVESTRE|OBSTACUL|OCR|DEKA|HYROX|FONDO|VERTICAL|RESISTENCIA|SUBIDA",key):
            continue
        mode=("HIBRIDA" if "HYROX" in key or "DEKA" in key else
              "OCR" if "OBSTACUL" in key or "OCR" in key else
              "ULTRA" if "ULTRA" in key else
              "TRAIL" if re.search(r"TRAIL|CXM|MONTANA",key) else
              "CROSS" if "CROSS" in key else "RUNNING")
        if re.search(r"\b(?:CANCELADA|CANCELADO|ANULADA|APLAZADA)\b",canon(" ".join(texts[i-2:i+6]))):
            continue
        return {"fecha":d.isoformat(),"nombre":name,"localidad":city,"provincia":province,
                "modalidad":mode,"distancia":(extract_distance(name,texts[i+2:])
                or extract_modalities_distance(texts[i+2:])),"fuente":link,"enlace":link,"origen":"dorsalchip"}
    return None



# Municipio y provincia explícitamente identificados, sin extrapolar fechas.
FAA_PLACES = {
    "VALLE DE ABDALAJIS":("Valle de Abdalajís","Málaga"),
    "VILLANUEVA DEL TRABUCO":("Villanueva del Trabuco","Málaga"),
    "AGUILARENSE":("Aguilar de la Frontera","Córdoba"),
    "TORRE DEL MAR":("Torre del Mar","Málaga"),
    "CROSS ALGARROBO":("Algarrobo","Málaga"),
    "ESTEPONA":("Estepona","Málaga"),
    "CARTAYA":("Cartaya","Huelva"),
    "ARCHIDONA":("Archidona","Málaga"),
    "ANTEQUERA":("Antequera","Málaga"),
    "BENAMEJI":("Benamejí","Córdoba"),
    "ARDALES":("Ardales","Málaga"),
    "AYAMONTE":("Ayamonte","Huelva"),
    "CARTAMA":("Cártama","Málaga"),
    "ALORA":("Álora","Málaga"),
    "PURULLENA":("Purullena","Granada"),
    "TORROX":("Torrox","Málaga"),
    "COMPETA":("Cómpeta","Málaga"),
    "RUTE":("Rute","Córdoba"),
    "VELEZ":("Vélez-Málaga","Málaga"),
    "ESPERA":("Espera","Cádiz"),
}
FAA_MONTHS = {canon(m):n for n,m in enumerate(
  ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO",
   "AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"],1)}
FAA_DATE=re.compile(r"^(\d{1,2})(?:\s*[-/]\s*\d{1,2})?\s+([A-ZÁÉÍÓÚÑ]+)\s+(20\d\d)$",re.I)

def parse_faa(page,today=None):
    today=today or date.today()
    parser=RaceText();parser.feed(page)
    chunks=[compact(x) for x in parser.words if compact(x)]
    start=next((i for i,t in enumerate(chunks) if "PROXIMAS CARRERAS" in canon(t)),None)
    if start is None:return []
    results=[];seen=set()
    for i in range(start+1,min(len(chunks)-1,start+180)):
        m=FAA_DATE.fullmatch(chunks[i])
        if not m:continue
        month=FAA_MONTHS.get(canon(m[2]))
        if not month:continue
        try:day=date(int(m[3]),month,int(m[1]))
        except ValueError:continue
        if day<today or day.year>today.year+2:continue
        title=chunks[i+1]
        if not title or len(title)>125 or FAA_DATE.fullmatch(title):continue
        if canon(title) in {"RESULTADOS","INSCRIPCIONES","CARRERAS POPULARES"}:continue
        if SKIP.search(title):continue
        upper=canon(title)
        matches=[]
        for term,place in FAA_PLACES.items():
            if re.search(r"(?<![A-Z])"+re.escape(term)+r"(?![A-Z])",upper):
                matches.append((len(term),place))
        if not matches:continue
        _,(city,prov)=max(matches,key=lambda x:x[0])
        identity=(day.isoformat(),upper)
        if identity in seen:continue
        seen.add(identity)
        typ=("ULTRA" if "ULTRA" in upper else
             "TRAIL" if re.search("TRAIL|CXM|MONTANA",upper) else
             "CROSS" if "CROSS" in upper else "RUNNING")
        from estado_inscripciones import faa_label
        results.append({"fecha":day.isoformat(),"nombre":title,"localidad":city,
                        "provincia":prov,"modalidad":typ,"distancia":extract_distance(title),
                        "enlace":SOURCES["faa"],"fuente":SOURCES["faa"],"origen":"faa",
                        **faa_label(title,SOURCES["faa"],today)})
    return results



GCC_CITY_MAP = {
    "LAS PALOMAS":("Zahara de la Sierra","Cádiz"),
    "ILITURGITANA":("Andújar","Jaén"),
    "CORDOBESA":("Córdoba","Córdoba"),
    "EPORA TRAIL":("Montoro","Córdoba"),
}
GCC_KNOWN_CITIES = {
    "CORDOBA":("Córdoba","Córdoba"),
    "MONTORO":("Montoro","Córdoba"),
    "ANDUJAR":("Andújar","Jaén"),
    "ZAHARA DE LA SIERRA":("Zahara de la Sierra","Cádiz"),
    "PEDRO ABAD":("Pedro Abad","Córdoba"),
    "JAEN":("Jaén","Jaén"),
    "TARIFA":("Tarifa","Cádiz"),
}

def gcc_links(page):
    p=CalendarParser();p.feed(page)
    seen=set();result=[]
    for a in p.anchors:
        href=urljoin(SOURCES["gcc"],a["href"])
        parts=urlparse(href)
        if parts.scheme!="https" or parts.hostname not in ("gccsportevents.es","www.gccsportevents.es",
            "www.runnink.com","runnink.com","gesconchip.es","www.gesconchip.es",
            "www.dipgra.es","dipgra.es","www.diphuelva.es","diphuelva.es"):
            continue
        if not re.fullmatch(r"/index\.php/(trail-cxm|atletismo-ruta-cross)/[a-z0-9-]+",parts.path,re.I):
            continue
        if href not in seen:
            seen.add(href);result.append(href)
    return result[:18]

def parse_gcc_detail(page,url,today=None):
    today=today or date.today()
    p=RaceText();p.feed(page)
    if not p.heading:return None
    title=compact(" ".join(p.heading))
    if len(title)>170 or len(title)<7 or SKIP.search(title):return None
    upper=canon(title)
    if not re.search(r"TRAIL|CXM|CROSS|CARRERA|SILVESTRE|RUNNING|ULTRA|MARATON|OBSTACUL|OCR",upper):
        return None
    full=compact(" ".join(p.words))
    m=re.search(r"Fecha inicio\s+(\d{1,2}-\d{1,2}-20\d\d)",full,re.I)
    if not m:return None
    try:day=datetime.strptime(m.group(1),"%d-%m-%Y").date()
    except ValueError:return None
    if day<today or day.year>today.year+2:return None
    city=None;province=None
    loc=re.search(r"\bLugar\s+(.{2,80}?)(?=\s+(?:Fecha|Cierre|Cuota|Apertura|Plazas|Inscripci[oó]n|Guardar|Capacidad|Registrado)\b|$)",full,re.I)
    if loc:
        raw=canon(loc.group(1))
        for tag,value in GCC_KNOWN_CITIES.items():
            if tag in raw:
                city,province=value
                break
    if not city:
        for marker,value in GCC_CITY_MAP.items():
            if marker in upper:
                city,province=value
                break
    if not city or not province:return None
    modality=("OCR" if "OBSTACUL" in upper or "OCR" in upper else
              "ULTRA" if "ULTRA" in upper else
              "TRAIL" if re.search(r"TRAIL|CXM|MONTANA",upper) else
              "CROSS" if "CROSS" in upper else "RUNNING")
    from estado_inscripciones import gcc_fields
    return {"fecha":day.isoformat(),"nombre":title,"localidad":city,
            "provincia":province,"modalidad":modality,"distancia":(extract_distance(title,p.words)
                or extract_modalities_distance(p.words)),
            "enlace":url,"fuente":url,"origen":"gcc",
            **gcc_fields(p.words,url,day,today)}


ALLOWED_HOSTS = frozenset((
    "fadmes.es", "dorsalchip.es", "www.cruzandolameta.es",
    "atletismofaa.es", "gccsportevents.es", "www.gccsportevents.es",
    "www.runnink.com", "runnink.com",
    "gesconchip.es", "www.gesconchip.es",
    "www.dipgra.es", "dipgra.es",
    "www.diphuelva.es", "diphuelva.es",
    "www.carreraspopularescordoba.com", "carreraspopularescordoba.com",
))
def is_allowed_url(url):
    parsed=urlparse(url)
    return parsed.scheme=="https" and parsed.hostname in ALLOWED_HOSTS

def fetch_if_permitted(url):
    parsed=urlparse(url)
    if not is_allowed_url(url):
        raise ValueError("URL no autorizada para este lector")
    robot=get_robots(parsed.hostname)
    if not robot.can_fetch(USER_AGENT,url):
        raise RuntimeError("robots.txt prohíbe la consulta")
    with urlopen(Request(url,headers={"User-Agent":USER_AGENT,"Accept":"text/html"}),timeout=18) as response:
        final=urlparse(response.geturl())
        if final.hostname!=parsed.hostname:raise RuntimeError("Redirección fuera del dominio")
        raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise RuntimeError("Página demasiado grande")
        ctype=response.headers.get("Content-Type","")
        if "html" not in ctype.lower():raise RuntimeError("Formato inesperado")
        return raw.decode("utf-8","replace")

def enrich_distance_from_detail(row, page, provider):
    """Lee solo la página vinculada con ESTA carrera y verifica el título.

    No sustituye fechas, nombres o ciudades ya seleccionados por el captador.
    Si la página no identifica el evento, mantiene la distancia original.
    """
    from difflib import SequenceMatcher
    p=RaceText();p.feed(page)
    # Varios portales usan h2/h3, no h1, para el título de la ficha.
    # Solo aceptar coincidencia clara con un nodo cercano al inicio, nunca
    # una mención dentro de una tarjeta de «otras carreras» al final.
    expected=canon(row.get("nombre",""))
    # Algunos portales tienen un h1 genérico y el título real en h2/h3.
    headings=[*p.heading[:6],*p.words[:85]]
    match=any(SequenceMatcher(None,canon(piece),expected).ratio()>=0.88
              for piece in headings if 5<=len(piece)<=180)
    if not match:
        return False
    if provider == "runnink" and row.get("fecha"):
        # Validar la edición antes de leer kilómetros de una ficha reutilizada.
        day=date.fromisoformat(row["fecha"])
        month=next(k for k,v in MONTHS.items() if v==day.month)
        expected_date=r"(?<!\d)0?"+str(day.day)+r"\s+de\s+"+month+r"\s+de\s+"+str(day.year)+r"(?!\d)"
        primary=" ".join(p.words[:85])
        primary=re.split(r"¿?Quieres participar|Te recomendamos|Otras carreras",primary,maxsplit=1,flags=re.I)[0]
        if not re.search(expected_date,primary,re.I):
            return False
    distance=(extract_races_section(p.words) if provider=="gesconchip"
              else extract_distance(row.get("nombre",""),p.words)
                   or extract_modalities_distance(p.words)
                   or extract_narrative_distance(p.words))
    if not distance:
        return False
    if row.get("distancia") and row["distancia"]!=distance:
        # Dos medidas distintas: no reemplazarlas sin revisión.
        return False
    if not row.get("distancia"):
        row["distancia"]=distance
        row["distancia_fuente"]=row.get("enlace","")
        return True
    return False


def enrich_booking_distance(row,page,booking_url):
    """Tarjetas de modalidades de Runnink; validar nombre antes de extraer."""
    from difflib import SequenceMatcher
    p=RaceText();p.feed(page)
    if not any(SequenceMatcher(None,canon(row.get("nombre")),canon(x)).ratio()>=.77
               for x in p.heading[:5]):
        return False
    distance=extract_booking_distance(p.words)
    if not distance or row.get("distancia"):
        return False
    row["distancia"]=distance
    row["distancia_fuente"]=booking_url
    return True


def fuentes_habilitadas():
    """Consulta prudente de hechos básicos sin confundir uso mínimo con licencia.

    'consulta_minima' NO significa autorización del titular; el uso de hechos
    objetivos y enlaces se limita técnicamente y sigue sujeto a revisión.
    Las reservas expresas siguen documentadas y se reportan como riesgo:
    consulta_minima no permite reproducir bases completas ni eludir restricciones.
    """
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "config" / "derechos_fuentes.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    records = config.get("fuentes")
    if config.get("version") != 1 or not isinstance(records, dict) or set(records) != set(SOURCES):
        raise ValueError("Registro de derechos de fuentes incompleto o inválido")
    enabled = set()
    for name, record in records.items():
        if not isinstance(record, dict) or record.get("estado") not in ("pendiente", "consulta_minima", "autorizado"):
            raise ValueError("Estado de derechos inválido: " + name)
        if record["estado"] == "autorizado":
            reference = str(record.get("referencia_evidencia") or "").strip()
            review_date = str(record.get("fecha_revision") or "")
            try:
                date.fromisoformat(review_date)
            except ValueError as exc:
                raise ValueError("Fecha de autorización inválida: " + name) from exc
            if len(reference) < 12:
                raise ValueError("Falta referencia de evidencia de derechos: " + name)
        if record["estado"] != "pendiente":
            enabled.add(name)
    return enabled


def is_access_restriction(exc):
    """Un veto de acceso no debe clasificarse como una caída recuperable."""
    for _ in range(8):
        if isinstance(exc,HTTPError) and exc.code in (401,403,451):
            return True
        if any(marker in str(exc).lower() for marker in (
                "robots.txt prohíbe", "url no autorizada", "redirección fuera del dominio")):
            return True
        exc=exc.reason if isinstance(exc,URLError) else getattr(exc,"__cause__",None)
        if exc is None:
            break
    return False


def is_transient_failure(exc):
    """Solo identificar fallos de red; nunca confundir vetos con indisponibilidad."""
    for _ in range(5):
        if isinstance(exc,HTTPError):
            return exc.code in (408, 429, 500, 502, 503, 504)
        if isinstance(exc,(TimeoutError, ConnectionError, socket.gaierror)):
            return True
        if isinstance(exc,URLError):
            exc=exc.reason
        else:
            exc=getattr(exc,"__cause__",None)
        if exc is None:
            return False
    return False


def collect(today=None):
    today=today or date.today()
    events=[];report={"consultado":today.isoformat(),"fuentes":{}}
    if os.environ.get('CORRERADAR_FETCH')=='0':
        report['modo']='Prueba local sin conexión'
        return events,report
    permitted = fuentes_habilitadas()
    report["fuentes_con_consulta_habilitada"] = len(permitted)
    report["nombres_fuentes_habilitadas"] = sorted(permitted)
    report["fuentes_con_reservas_documentadas"] = sorted(permitted & FUENTES_CON_RESERVAS_DOCUMENTADAS)
    if not permitted:
        report["modo"] = "Fuentes con consulta automática pausada"
    for name,url in SOURCES.items():
        if name not in permitted:
            report["fuentes"][name] = {
                "estado": "sin consulta automática",
                "motivo": "Consulta pausada: reserva expresa o revisión pendiente",
                "url": url}
            continue
        try:
            page=fetch_if_permitted(url)
            detail_errors=0;detail_restricted=False;enlaces_detectados=None
            if name=="dipgra":
                from captacion_extra import diputacion_granada
                rows=diputacion_granada(page,today)
            elif name=="diphuelva":
                from captacion_extra import diputacion_huelva
                rows=diputacion_huelva(page,today)
            elif name=="circuito_cordoba":
                from circuito_cordoba import circuito_links, circuito_detail
                rows=[]
                links=circuito_links(page)
                enlaces_detectados=len(links)
                detail_errors=0
                for link,title in links[:MAX_DETALLES_POR_FUENTE]:
                    try:
                        candidate=circuito_detail(fetch_if_permitted(link),link,title,today)
                        if candidate:rows.append(candidate)
                    except Exception as exc:
                        detail_errors+=1
                        detail_restricted |= is_access_restriction(exc)
                    time.sleep(0.2)
                report["fuentes"]["circuito_cordoba_detalle"]={
                    "consultadas":min(len(links),MAX_DETALLES_POR_FUENTE),"carreras_documentadas":len(rows),
                    "incidencias":detail_errors}
            elif name=="runnink":
                from captacion_extra import runnink
                rows=runnink(page,today)
                detail_success=0;detail_errors=0;attempted=0;fetched=0
                # Solo fichas públicas ya enlazadas en el listado, sin /book/,
                # formularios, inscritos ni resultados. Un máximo de 12 intentos.
                missing=sorted((r for r in rows if not r.get("distancia")),
                               key=lambda r:(r["fecha"],r["nombre"]))
                enabled=os.environ.get("CORRERADAR_DISTANCE_ENRICHMENT")=="yes"
                for row in (missing[:MAX_ENRIQUECIMIENTO_RUNNINK] if enabled else []):
                    if not re.fullmatch(r"/evento/[^/]+/\d+/?",urlparse(row["enlace"]).path):
                        continue
                    attempted+=1
                    try:
                        detail=fetch_if_permitted(row["enlace"]);fetched+=1
                        if enrich_distance_from_detail(row,detail,"runnink"):
                            row["distancia_cotejada"]=today.isoformat()
                            detail_success+=1
                    except Exception as exc:
                        detail_errors+=1
                        detail_restricted |= is_access_restriction(exc)
                    finally:
                        time.sleep(0.5)
                report["fuentes"]["runnink_detalle"]={
                    "estado":"consulta_factica_limitada" if enabled else "desactivado",
                    "intentos":attempted,"consultadas":fetched,
                    "distancias_recuperadas":detail_success,"incidencias":detail_errors,
                    "pendientes":sum(not r.get("distancia") for r in rows)}
            elif name=="gesconchip":
                from captacion_extra import gesconchip
                rows=gesconchip(page,today)
                # El aviso legal revisado reserva el uso privado y exige
                # autorización expresa de reproducción: no ampliar la captación.
                report["fuentes"]["gesconchip_detalle"]={
                    "estado":"pausado por revisión de derechos","consultadas":0,
                    "distancias_recuperadas":0,"incidencias":0,
                    "pendientes":sum(not r.get("distancia") for r in rows)}
            elif name=="fadmes":
                rows=parse_fadmes(page,today)
            elif name=="faa":
                rows=parse_faa(page,today)
            elif name=="gcc":
                rows=[]
                enlaces=gcc_links(page)
                enlaces_detectados=len(enlaces)
                for detail in enlaces[:MAX_DETALLES_POR_FUENTE]:
                    try:
                        candidate=parse_gcc_detail(fetch_if_permitted(detail),detail,today)
                        if candidate:rows.append(candidate)
                    except Exception as exc:
                        detail_errors+=1
                        detail_restricted |= is_access_restriction(exc)
                    time.sleep(0.3)
            elif name=="dorsalchip":
                rows=[];links=dorsal_links(page,today)
                enlaces_detectados=len(links)
                for detail in links[:MAX_DETALLES_POR_FUENTE]:
                    try:
                        candidate=dorsal_detail(fetch_if_permitted(detail),detail,today)
                        if candidate:rows.append(candidate)
                    except Exception as exc:
                        detail_errors+=1
                        detail_restricted |= is_access_restriction(exc)
                    time.sleep(0.2)
            elif name=="cruzandolameta":
                rows=[];links=cruzando_links(page)
                enlaces_detectados=len(links)
                rechazos={};consultadas=0
                for detail in links[:MAX_DETALLES_POR_FUENTE]:
                    consultadas+=1
                    try:
                        diagnostico={}
                        candidate=parse_cruzando_detail(
                            fetch_if_permitted(detail),detail,today,diagnostico)
                        if candidate:
                            rows.append(candidate)
                        else:
                            motivo=diagnostico.get("motivo","descarte_sin_motivo")
                            rechazos[motivo]=rechazos.get(motivo,0)+1
                    except Exception as exc:
                        detail_errors+=1
                        detail_restricted |= is_access_restriction(exc)
                    time.sleep(0.3)
                # Solo cifras agregadas: no guardar HTML, nombres, URLs de fichas
                # ni datos personales en la telemetría de diagnósticos.
                report["fuentes"]["cruzandolameta_detalle"]={
                    "estado":"diagnostico", "consultadas":consultadas,
                    "aceptadas":len(rows), "descartadas":sum(rechazos.values()),
                    "errores":detail_errors, "motivos":dict(sorted(rechazos.items()))}
            else:
                # Un lector nuevo exige revisión y activación explícitas.
                raise ValueError("No existe un lector para esta fuente")
            for row in rows:
                if row.get("distancia"):
                    row.setdefault("distancia_fuente",row.get("fuente") or row.get("enlace"))
                    row.setdefault("distancia_cotejada",today.isoformat())
            events.extend(rows)
            report["fuentes"][name]={"estado":"leida","candidatas":len(rows),"url":url,
                "con_distancia":sum(bool(r.get("distancia")) for r in rows),
                "incidencias_detalle":detail_errors,"detalle_restringido":detail_restricted}
            if enlaces_detectados is not None:
                report["fuentes"][name]["enlaces_detectados"]=enlaces_detectados
        except Exception as exc:
            report["fuentes"][name]={"estado":"no disponible","motivo":str(exc)[:170],"url":url,
                "fallo_temporal":is_transient_failure(exc) and not is_access_restriction(exc),
                "acceso_restringido":is_access_restriction(exc)}
    report["fuentes"]["sportmaniacs"]={"estado":"sin consulta automática",
        "motivo":"No se ha verificado un calendario estructurado accesible ni método autorizado"}
    report["fuentes"]["dip_almeria"]={"estado":"sin próximas carreras",
        "motivo":"El circuito provincial 2026 finalizó en octubre; no extrapolar fechas de 2027"}
    # Solo feed facilitado por Global Tempo tras autorización; jamás
    # raspado de su web ni importación de listados de participantes.
    from globaltempo_feed import fetch_authorized_feed, authorized
    report["globaltempo_autorizado"]=authorized()
    try:
        gt_events,gt_status=fetch_authorized_feed(today)
        events.extend(gt_events)
        report["fuentes"]["globaltempo"]=gt_status
    except Exception as exc:
        report["fuentes"]["globaltempo"]={"estado":"no disponible",
            "motivo":str(exc)[:170]}
    return events,report
