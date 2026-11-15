"""Captación prudente de fechas de calendarios públicos (sin datos de personas).
Los resultados siempre quedan en estado 'Por confirmar'; NO se aprueban solos.
No se eluden bloqueos, robots ni controles de acceso.
"""
from __future__ import annotations
from datetime import date, datetime
from html.parser import HTMLParser
from urllib.parse import urlparse, urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.robotparser import RobotFileParser
import re
import unicodedata

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
    today=today or date.today()
    p=CalendarParser();p.feed(html)
    found=[]
    for a in p.anchors:
        href=urljoin(SOURCES["dorsalchip"],a["href"])
        url=urlparse(href)
        if url.hostname not in ("dorsalchip.es","www.dorsalchip.es") or not url.path.lower().endswith(".aspx"):continue
        parts=[compact(s) for s in a["parts"] if compact(s)]
        if not parts:continue
        d=get_date(parts[0]) or get_date(a["text"])
        if not d or d<today or d.year>today.year+2:continue
        # Solo usar fichas con campos separados explícitamente: no deducir un municipio del nombre.
        loc_index=next((i for i,s in enumerate(parts) if re.search(r",\s*(Almería|Cádiz|Córdoba|Granada|Huelva|Jaén|Málaga|Sevilla)\s*$",s,re.I)),None)
        if loc_index is None:continue
        loc=parts[loc_index]
        city,prov=loc.rsplit(",",1);province=PROVINCES.get(canon(prov))
        name_parts=parts[:loc_index]
        name=compact(" ".join(name_parts))
        name=re.sub(r"^\d{1,2}/\d{1,2}/20\d\d\s*","",name)
        name=re.sub(r"\s*Prueba cronometrada por dorsalChip.*$","",name,flags=re.I)
        if not name or not province or not compact(city) or len(name)>170 or SKIP.search(name):continue
        if re.search(r"\b(?:traves[ií]a\s+a\s+nado|marcha\s+solidaria)\b",name,re.I):continue
        key=canon(name)
        modality=("OCR" if re.search(r"\bOCR\b|OBSTACUL",key) else
                  "ULTRA" if "ULTRA" in key else
                  "TRAIL" if re.search(r"TRAIL|CXM|MONTANA",key) else
                  "CROSS" if "CROSS" in key else "RUNNING")
        found.append({"fecha":d.isoformat(),"nombre":name,"localidad":compact(city),
                      "provincia":province,"modalidad":modality,"distancia":"",
                      "fuente":href,"enlace":href,"origen":"dorsalchip"})
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
