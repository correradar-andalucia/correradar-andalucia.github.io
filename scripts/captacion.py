"""Captación prudente de fechas de calendarios públicos (sin datos de personas).
Los resultados siempre quedan en estado 'Por confirmar'; NO se aprueban solos.
No se eluden bloqueos, robots ni controles de acceso.
"""
from __future__ import annotations
from datetime import date, datetime
from html.parser import HTMLParser
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

def fetch_if_permitted(url):
    parsed=urlparse(url)
    if parsed.scheme!="https" or parsed.hostname not in ("fadmes.es","dorsalchip.es"):
        raise ValueError("URL no autorizada para este lector")
    root=f"{parsed.scheme}://{parsed.hostname}"
    robots_url=root+"/robots.txt"
    robot=RobotFileParser();robot.set_url(robots_url)
    try:
        with urlopen(Request(robots_url,headers={"User-Agent":USER_AGENT}),timeout=12) as response:
            if response.getcode()!=200:raise RuntimeError("robots.txt no verificable")
            lines=response.read(250_001)
            if len(lines)>250_000:raise RuntimeError("robots.txt demasiado grande")
        robot.parse(lines.decode("utf-8","replace").splitlines())
    except HTTPError as ex:
        # 404 significa que no existe robots.txt; 401/403 deniegan y 5xx bloquean por precaución.
        if ex.code!=404:raise RuntimeError(f"robots.txt HTTP {ex.code}") from ex
        robot.parse([])
    except Exception as ex:
        raise RuntimeError("No fue posible consultar robots.txt: "+type(ex).__name__) from ex
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
            rows=parse_fadmes(page,today) if name=="fadmes" else parse_dorsalchip(page,today)
            events.extend(rows)
            report["fuentes"][name]={"estado":"leida","candidatas":len(rows),"url":url}
        except Exception as exc:
            report["fuentes"][name]={"estado":"no disponible","motivo":str(exc)[:170],"url":url}
    report["fuentes"]["globaltempo"]={"estado":"sin consulta automática",
        "motivo":"Condiciones de reutilización pendientes; solo fichas cotejadas manualmente"}
    return events,report
