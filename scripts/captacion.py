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
from urllib.error import HTTPError
from urllib.robotparser import RobotFileParser
import re
import unicodedata
import os

USER_AGENT = "CorreRadarAndaluciaBot/0.1 (+mailto:correradarandalucia@gmail.com)"
SOURCES = {
    "fadmes": "https://fadmes.es/calendario-fam/",
    "dorsalchip": "https://dorsalchip.es/view/Inicio.aspx",
    "cruzandolameta": "https://www.cruzandolameta.es/pruebas/",
    "faa": "https://atletismofaa.es/carreraspopulares/",
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
                      "modalidad":modality,"distancia":"","fuente":SOURCES["fadmes"],
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
                      "modalidad":modality,"distancia":"","fuente":url,"enlace":url,"origen":"dorsalchip"})
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

def parse_cruzando_detail(page,source_url,today=None):
    today=today or date.today()
    parser=RaceText();parser.feed(page)
    name=compact(" ".join(parser.heading))
    if not name or len(name)>170 or SKIP.search(name):return None
    full=compact(" ".join(parser.words))
    pos=full.find(name)
    primary=full[pos+len(name):] if pos>=0 else full
    primary=re.split(r"También te puede interesar|Más pruebas en",primary,maxsplit=1,flags=re.I)[0]
    if re.search(r"\bcancelad[ao]s?\b|\banulad[ao]s?\b",primary[:600],re.I):return None
    m=re.search(r"\b(\d{1,2})\s+de\s+("+ "|".join(MONTHS.keys())+
                r")\s+de\s+(20\d\d)\b",primary[:650],re.I)
    if m:
        try:d=date(int(m[3]),MONTHS[m[2].lower()],int(m[1]))
        except ValueError:return None
    else:
        d=get_date(primary[:650])
    if not d or d<today or d.year>today.year+2:return None
    key=canon(name)
    category=("HIBRIDA" if re.search(r"HYROX|DEKA",key) else
              "OCR" if re.search(r"\bOCR\b|OBSTACUL",key) else
              "ULTRA" if "ULTRA" in key else
              "TRAIL" if re.search(r"TRAIL|CXM|MONTANA|SILVESTRAIL",key) else
              "CROSS" if "CROSS" in key else "RUNNING")
    if category=="RUNNING" and not re.search(
            r"CARRERA|MARATON|FONDO|SUBIDA|RUNNING|SAN SILVESTRE|RELEVOS",key):
        return None
    located=primary[:1100]
    province=None
    for p in PROVINCES.values():
        if re.search(r"\("+re.escape(p)+r"\)",located,re.I):
            province=p;break
    if province is None:return None
    loc=re.search(r"(.{2,110}?)\s*\("+re.escape(province)+r"\)",located,re.I)
    if not loc:return None
    place=compact(loc.group(1))
    # Preservar el lugar explícito; no convertir un pabellón en municipio inventado.
    for marker in ("Dónde", "Localización", "Lugar", "Salida"):
        if marker in place:place=place.split(marker)[-1].strip(" :·")
    place=place[-100:].strip(" ,;·")
    if not place or len(place)<2:return None
    return {"fecha":d.isoformat(),"nombre":name,"localidad":place,"provincia":province,
            "modalidad":category,"distancia":"","enlace":source_url,
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
        match=re.match(r"^/carrera/(20\d\d)/\d{1,2}/\d{1,2}/[^/]+\.aspx$",u.path,re.I)
        if not match or int(match[1])<today.year:continue
        if url in seen:continue
        seen.add(url);found.append(url)
    # El listado incluye pruebas ya celebradas; el tramo final presenta las más recientes.
    return found[-60:]

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
                "modalidad":mode,"distancia":"","fuente":link,"enlace":link,"origen":"dorsalchip"}
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
        results.append({"fecha":day.isoformat(),"nombre":title,"localidad":city,
                        "provincia":prov,"modalidad":typ,"distancia":"",
                        "enlace":SOURCES["faa"],"fuente":SOURCES["faa"],"origen":"faa"})
    return results


def fetch_if_permitted(url):
    parsed=urlparse(url)
    if parsed.scheme!="https" or parsed.hostname not in (
            "fadmes.es","dorsalchip.es","www.cruzandolameta.es","atletismofaa.es"):
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

def collect(today=None):
    today=today or date.today()
    events=[];report={"consultado":today.isoformat(),"fuentes":{}}
    if os.environ.get('CORRERADAR_FETCH')=='0':
        report['modo']='Prueba local sin conexión'
        return events,report
    for name,url in SOURCES.items():
        try:
            page=fetch_if_permitted(url)
            if name=="fadmes":
                rows=parse_fadmes(page,today)
            elif name=="faa":
                rows=parse_faa(page,today)
            elif name=="dorsalchip":
                rows=[];links=dorsal_links(page,today)
                for detail in links:
                    try:
                        candidate=dorsal_detail(fetch_if_permitted(detail),detail,today)
                        if candidate:rows.append(candidate)
                    except Exception:
                        pass
                    time.sleep(0.2)
            else:
                rows=[];links=cruzando_links(page)
                for detail in links:
                    try:
                        candidate=parse_cruzando_detail(fetch_if_permitted(detail),detail,today)
                        if candidate:rows.append(candidate)
                    except Exception:
                        pass
                    time.sleep(0.3)
            events.extend(rows)
            report["fuentes"][name]={"estado":"leida","candidatas":len(rows),"url":url}
        except Exception as exc:
            report["fuentes"][name]={"estado":"no disponible","motivo":str(exc)[:170],"url":url}
    report["fuentes"]["globaltempo"]={"estado":"sin consulta automática",
        "motivo":"Condiciones de reutilización pendientes; solo fichas cotejadas manualmente"}
    return events,report
