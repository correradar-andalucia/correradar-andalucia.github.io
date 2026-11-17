"""Descubrimiento en el calendario del Circuito Cordobés de Carreras Populares.

Solo datos mínimos de fichas específicas del circuito (no agregadores ni
Global Tempo): nombre, fecha COMPLETA con año, municipio identificado y enlace.
Las fechas sin año explícito o las carreras con municipio ambiguo se descartan.
El acceso de red siempre pasa por fetch_if_permitted (robots, HTTPS y límites).
"""
from __future__ import annotations
from datetime import date, timedelta
import re
import unicodedata
from urllib.parse import urljoin, urlparse
from html.parser import HTMLParser

BASE = "https://www.carreraspopularescordoba.com/"
EVENT_PATH = re.compile(r"^/index\.php/calendario/eventodetalle/\d{1,7}/-/[a-z0-9-]+/?$", re.I)
DATE = re.compile(
    r"\b(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\s*,?\s*"
    r"(\d{1,2})\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
    r"septiembre|octubre|noviembre|diciembre)\s+(20\d\d)\b", re.I)
MONTHS = {name:i+1 for i,name in enumerate(
    ("enero","febrero","marzo","abril","mayo","junio","julio","agosto",
     "septiembre","octubre","noviembre","diciembre"))}
NO_FOOT = re.compile(r"\b(?:triatlon|duatlon|ciclismo|cicloturismo|btt|mtb|"
                     r"natacion|senderismo|marcha senderista|mushing)\b",re.I)
# No adivinar municipio por proximidad ni por año precedente.
CITIES = {
    "palma del rio":"Palma del Río",
    "benameji":"Benamejí",
    "guadalcazar":"Guadalcázar",
    "rute":"Rute",
    "priego de cordoba":"Priego de Córdoba",
    "almodovar del rio":"Almodóvar del Río",
    "villanueva de cordoba":"Villanueva de Córdoba",
    "fuente obejuna":"Fuente Obejuna",
    "encinas reales":"Encinas Reales",
    "villafranca de cordoba":"Villafranca de Córdoba",
    "castro del rio":"Castro del Río",
    "puente genil":"Puente Genil",
    "villa del rio":"Villa del Río",
    "la rambla":"La Rambla",
    "la carlota":"La Carlota",
    "pedro abad":"Pedro Abad",
    "el carpio":"El Carpio",
    "pozoblanco":"Pozoblanco",
    "montilla":"Montilla",
    "montoro":"Montoro",
    "lucena":"Lucena",
    "baena":"Baena",
    "cabra":"Cabra",
    "torrecampo":"Torrecampo",
    "cordoba":"Córdoba",
}
SPECIAL_CITIES = {
    "canada real soriana": "Córdoba",
    "san silvestre cordobesa": "Córdoba",
}


def normalize(value):
    text=unicodedata.normalize("NFKD",str(value or "").lower())
    text="".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+"," ",text).split())


class AnchorParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[]
        self.link=None
        self.skip=0

    def handle_starttag(self,tag,attrs):
        if tag in ("script","style"):
            self.skip+=1
        if tag=="a" and not self.skip:
            self.link={"href":dict(attrs).get("href",""),"text":[]}

    def handle_endtag(self,tag):
        if tag in ("script","style") and self.skip:
            self.skip-=1
        if tag=="a" and self.link is not None:
            self.link["text"]=" ".join(self.link["text"]).strip()
            self.links.append(self.link)
            self.link=None

    def handle_data(self,data):
        if self.link is not None and not self.skip and data.strip():
            self.link["text"].append(data.strip())


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.words=[]
        self.skip=0

    def handle_starttag(self,tag,attrs):
        if tag in ("script","style"):
            self.skip+=1

    def handle_endtag(self,tag):
        if tag in ("script","style") and self.skip:
            self.skip-=1

    def handle_data(self,data):
        if not self.skip and data.strip():
            self.words.append(" ".join(data.split()))


def circuito_links(html):
    parser=AnchorParser();parser.feed(html)
    links=[];seen=set()
    for a in parser.links:
        url=urljoin(BASE,a["href"])
        parsed=urlparse(url)
        if (parsed.scheme!="https" or parsed.hostname not in
                ("www.carreraspopularescordoba.com","carreraspopularescordoba.com")
                or not EVENT_PATH.fullmatch(parsed.path)
                or parsed.query or parsed.fragment):
            continue
        title=" ".join(a["text"].split())
        if len(title)<6 or len(title)>170 or url in seen:
            continue
        seen.add(url)
        links.append((url,title))
    return links[:24]


def event_city(title):
    name=normalize(title)
    if NO_FOOT.search(name):
        return ""
    for phrase,city in SPECIAL_CITIES.items():
        if re.search(r"\b"+re.escape(phrase)+r"\b",name):
            return city
    found={city for phrase,city in CITIES.items()
           if re.search(r"\b"+re.escape(phrase)+r"\b",name)}
    # Por ejemplo "Córdoba-Almodóvar" menciona dos municipios y requiere revisión.
    return next(iter(found)) if len(found)==1 else ""


def circuito_detail(html,url,title,today=None):
    today=today or date.today()
    parsed=urlparse(url)
    if parsed.scheme!="https" or not EVENT_PATH.fullmatch(parsed.path):
        return None
    if parsed.hostname not in ("carreraspopularescordoba.com",
                               "www.carreraspopularescordoba.com"):
        return None
    city=event_city(title)
    if not city:
        return None
    parser=VisibleText();parser.feed(html)
    full=" ".join(parser.words)
    # La barra lateral contiene otras carreras; solo se acepta el encabezado
    # y la fecha que preceden al bloque "Próximas Carreras".
    first=full.split("Próximas Carreras",1)[0]
    dates=list(DATE.finditer(first))
    if len(dates)!=1:
        return None
    match=dates[0]
    prior=normalize(first[:match.start()])
    if normalize(title) not in prior:
        return None
    try:
        when=date(int(match[3]),MONTHS[normalize(match[2])],int(match[1]))
    except (ValueError,KeyError):
        return None
    if when<today or when>today+timedelta(days=550):
        return None
    key=normalize(title)
    category=("CROSS" if "cross" in key or "campo a traves" in key else
              "TRAIL" if "trail" in key or "cxm" in key else "RUNNING")
    return {"fecha":when.isoformat(),"nombre":title,"localidad":city,
            "provincia":"Córdoba","modalidad":category,"distancia":"",
            "enlace":url,"fuente":url,"origen":"circuito_cordoba",
            "fuente_directa":True,
            "estado":"Fecha publicada en el calendario oficial del circuito"}
