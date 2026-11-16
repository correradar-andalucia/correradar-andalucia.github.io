"""Lectores adicionales: Runnink y Gesconchip. Solo hechos básicos y enlaces.

No se copian descripciones ni fotografías; sin acceso a cuentas ni datos de atletas.
Los eventos no se marcan como aprobados. Sin fuentes verificables: cero resultados.
"""
from __future__ import annotations
from datetime import date
from urllib.parse import urlparse, urljoin
from html.parser import HTMLParser
import re
import unicodedata
from distancias import extract_distance

RUNNINK="https://www.runnink.com/inscripciones/"
GESCONCHIP="https://gesconchip.es/app/proximas-pruebas"
MONTHS={n:i+1 for i,n in enumerate(
    ["enero","febrero","marzo","abril","mayo","junio","julio","agosto",
     "septiembre","octubre","noviembre","diciembre"])}
SHORT={"ene":1,"feb":2,"mar":3,"abr":4,"may":5,"jun":6,"jul":7,"ago":8,
       "sep":9,"sept":9,"oct":10,"nov":11,"dic":12}
PROVINCES={"almeria":"Almería","cadiz":"Cádiz","cordoba":"Córdoba","granada":"Granada",
           "huelva":"Huelva","jaen":"Jaén","malaga":"Málaga","sevilla":"Sevilla"}
NO_FOOT=re.compile(r"triatl[oó]n|duatl[oó]n|ciclismo|btt|mtb|nataci[oó]n|"
                   r"acuatl[oó]n|cicloturista|paddle|senderismo|traves[ií]a nado",re.I)
RUN_RE=re.compile(r"\b(\d{1,2})\s+de\s+("+"|".join(MONTHS)+r")\s+de\s+(20\d\d)\b",re.I)
GES_RE=re.compile(r"^\s*(\d{1,2})\s+([a-záéíóúñ]{3,4})\.?\s+(20\d\d)\s+(.+)$",re.I)

CITIES={
    "almeria":("Almería","Almería"),"jaen":("Jaén","Jaén"),
    "chiclana de la frontera":("Chiclana de la Frontera","Cádiz"),
    "chiclana":("Chiclana de la Frontera","Cádiz"),
    "san roque":("San Roque","Cádiz"),
    "rota":("Rota","Cádiz"),"algeciras":("Algeciras","Cádiz"),
    "san fernando":("San Fernando","Cádiz"),
    "el puerto de santa maria":("El Puerto de Santa María","Cádiz"),
    "jerez de la frontera":("Jerez de la Frontera","Cádiz"),
    "benalup casas viejas":("Benalup-Casas Viejas","Cádiz"),
    "marbella":("Marbella","Málaga"),"malaga":("Málaga","Málaga"),
    "benahavis":("Benahavís","Málaga"),
    "rota-chipiona":("Rota-Chipiona","Cádiz"),
    "sanlucar la mayor":("Sanlúcar la Mayor","Sevilla"),
    "torremolinos":("Torremolinos","Málaga"),
    "valencina de la concepcion":("Valencina de la Concepción","Sevilla"),
    "carrion de los cespedes":("Carrión de los Céspedes","Sevilla"),
    "herrera":("Herrera","Sevilla"),
    "montoro":("Montoro","Córdoba"),"cordoba":("Córdoba","Córdoba"),
    "granada":("Granada","Granada"),"huelva":("Huelva","Huelva"),
}

def clean(s):
    s=unicodedata.normalize("NFKD",str(s or "").lower())
    return re.sub(r"\s+"," ","".join(c for c in s if not unicodedata.combining(c))).strip()

def mode(text):
    key=clean(text)
    if NO_FOOT.search(key):return ""
    if "hybrid" in key or "hibrid" in key or "deka" in key or "hyrox" in key:return "HIBRIDA"
    if "obstacul" in key or re.search(r"\bocr\b",key):return "OCR"
    if "ultra" in key:return "ULTRA"
    if "trail" in key or "cxm" in key or "montana" in key:return "TRAIL"
    if "cross" in key or "campo a traves" in key:return "CROSS"
    return "RUNNING"

class Listing(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.words=[];self.links=[];self.depth=0;self.a=None
    def handle_starttag(self,tag,attrs):
        if tag=="script" or tag=="style":self.depth+=1
        if tag=="a":self.a={"href":dict(attrs).get("href",""),"text":[]}
    def handle_endtag(self,tag):
        if tag in ("script","style") and self.depth:self.depth-=1
        if tag=="a" and self.a is not None:
            self.a["text"]=" ".join(self.a["text"]).strip()
            self.links.append(self.a);self.a=None
    def handle_data(self,data):
        if self.depth:return
        t=re.sub(r"\s+"," ",data).strip()
        if t:
            self.words.append(t)
            if self.a is not None:self.a["text"].append(t)

def runnink(page,today=None):
    """Listado de tarjetas: título de ficha, a continuación ciudad/provincia y fecha."""
    today=today or date.today()
    p=Listing();p.feed(page)
    out=[];seen=set()
    for anchor in p.links:
        raw=anchor["href"]
        url=urljoin(RUNNINK,raw)
        loc=urlparse(url)
        if loc.hostname not in ("www.runnink.com","runnink.com"):continue
        if not re.fullmatch(r"/evento/[^/]+/\d+/?",loc.path,re.I):continue
        title=anchor["text"].strip()
        if not 5<=len(title)<=170 or mode(title)=="" or url in seen:continue
        seen.add(url)
        try:i=next(i for i,w in enumerate(p.words) if w.strip()==title)
        except StopIteration:continue
        fragment=" ".join(p.words[i+1:i+12])
        # Fecha y municipio deben estar cerca del título de esa tarjeta, no de la siguiente.
        m=RUN_RE.search(fragment)
        loc_match=re.search(r"(?:📍\s*)?([^📅\n]{2,100}?)\s*\(\s*(Almería|Cádiz|Córdoba|Granada|Huelva|Jaén|Málaga|Sevilla)\s*\)",
                            fragment[:m.start()] if m else "",re.I)
        if not m or not loc_match:continue
        city=loc_match.group(1).strip(" ·|-")
        city=re.sub(r"^(?:Lugar|Localidad|Ubicación)\s*:\s*","",city,flags=re.I)
        # Rechazar texto de estado de inscripción incrustado en el municipio.
        if not city or len(city)>65 or "Inscripciones" in city:continue
        province=PROVINCES.get(clean(loc_match.group(2)))
        try:d=date(int(m.group(3)),MONTHS[clean(m.group(2))],int(m.group(1)))
        except (ValueError,KeyError):continue
        if d<today or d.year>today.year+2:continue
        context=" ".join(p.words[max(0,i-2):i+1])
        if NO_FOOT.search(context):continue
        kind=mode(context+" "+title)
        if not kind:continue
        out.append({"fecha":d.isoformat(),"nombre":title,"localidad":city,
                    "provincia":province,"modalidad":kind,"distancia":extract_distance(title),
                    "enlace":url,"fuente":url,"origen":"runnink"})
    return out

def gesconchip(page,today=None):
    """Lee únicamente entradas cuyo nombre y municipio están explícitos en el enlace."""
    today=today or date.today()
    p=Listing();p.feed(page)
    out=[];seen=set()
    for a in p.links:
        url=urljoin(GESCONCHIP,a["href"])
        parsed=urlparse(url)
        if parsed.hostname not in ("gesconchip.es","www.gesconchip.es"):continue
        if "/prueba/informacion/" not in parsed.path.lower():continue
        if url in seen:continue
        seen.add(url)
        m=GES_RE.match(a["text"])
        if not m:continue
        month=SHORT.get(clean(m.group(2)))
        if month is None:continue
        try:d=date(int(m.group(3)),month,int(m.group(1)))
        except ValueError:continue
        if d<today or d.year>today.year+2:continue
        main=re.split(r"\s+(?:Cierre|Cambio|Apertura)\s+INSCRIPCIONES\b",m.group(4),
                      maxsplit=1,flags=re.I)[0].strip()
        # Extraer localidad junto a su provincia, comprobando un inventario de municipios.
        province_pattern=re.search(
            r"\s+-\s+(Almería|Cádiz|Córdoba|Granada|Huelva|Jaén|Málaga|Sevilla)(?:\s|$)",main,re.I)
        if not province_pattern:continue
        before=main[:province_pattern.start()].strip()
        province=PROVINCES.get(clean(province_pattern.group(1)))
        choices=[(len(key),place,key) for key,place in CITIES.items()
                 if place[1]==province and clean(before).endswith(key)]
        if not choices:continue
        _,(city,_),key=max(choices,key=lambda x:x[0])
        original_name=before[:len(before)-len(key)].strip(" ·-,")
        if not 7<=len(original_name)<=170:continue
        kind=mode(original_name)
        if not kind:continue
        out.append({"fecha":d.isoformat(),"nombre":original_name,"localidad":city,
                    "provincia":province,"modalidad":kind,"distancia":extract_distance(original_name),
                    "enlace":url,"fuente":url,"origen":"gesconchip"})
    return out


DIPGRA="https://www.dipgra.es/servicios/areas/deportes/deporte-competicion/circuito-provincial-campo-a-traves/"
DIPHUELVA="https://www.diphuelva.es/deportes/contenidos/Circuitos-Carreras-Atleticas-2026/"
GRANADA_CITIES={"cuevas del campo":"Cuevas del Campo","lecrin":"Lecrín","la zubia":"La Zubia",
                "baza":"Baza","freila":"Freila","las gabias":"Las Gabias",
                "quentar":"Quéntar","moraleda de zafayona":"Moraleda de Zafayona",
                "guadix":"Guadix","alhendin":"Alhendín","illora":"Íllora"}
HUELVA_CITIES={
    "villanueva de los castillejos":"Villanueva de los Castillejos",
    "vva. de los castillejos":"Villanueva de los Castillejos",
    "san silvestre de guzman":"San Silvestre de Guzmán",
    "moguer":"Moguer","cartaya":"Cartaya","ayamonte":"Ayamonte",
    "almonte":"Almonte","huelva":"Huelva","bonares":"Bonares",
    "trigueros":"Trigueros","lepe":"Lepe","galaroza":"Galaroza",
    "escacena del campo":"Escacena del Campo","beas":"Beas",
    "puebla de guzman":"Puebla de Guzmán","rociana del condado":"Rociana del Condado",
    "bollullos par del condado":"Bollullos Par del Condado",
    "san juan del puerto":"San Juan del Puerto","isla cristina":"Isla Cristina",
    "punta umbria":"Punta Umbría",
}

def diputacion_granada(page,today=None):
    from captacion import CalendarParser, get_date
    today=today or date.today()
    parser=CalendarParser();parser.feed(page)
    out=[];seen=set()
    for row in parser.rows:
        if len(row)<2:continue
        d=get_date(row[0])
        if not d or d<today or d.year>today.year+2:continue
        city=GRANADA_CITIES.get(clean(row[1]))
        if not city:continue
        key=(d.isoformat(),city)
        if key in seen:continue
        seen.add(key)
        out.append({"fecha":d.isoformat(),
                    "nombre":"XXX Circuito Provincial de Campo a Través — "+city,
                    "localidad":city,"provincia":"Granada",
                    "modalidad":"CROSS","distancia":"",
                    "fuente":DIPGRA,"enlace":DIPGRA,"origen":"dipgra"})
    return out

def diputacion_huelva(page,today=None):
    today=today or date.today()
    parser=Listing();parser.feed(page)
    out=[];seen=set()
    section=""
    for raw in parser.words:
        line=" ".join(raw.split())
        low=clean(line)
        if low in ("carreras populares","campo a traves","gran fondo"):
            section=low
            continue
        if "correo electronico de la delegacion" in low:
            break
        if section not in ("carreras populares","campo a traves","gran fondo"):
            continue
        match=re.search(r"(\d{1,2})/(\d{1,2})/(20\d\d)\s*$",line)
        if not match or len(line)>240:continue
        try:d=date(int(match[3]),int(match[2]),int(match[1]))
        except ValueError:continue
        if d<today or d.year>today.year+2:continue
        title=line[:match.start()].strip(' -·')
        if not title or NO_FOOT.search(title):continue
        candidates=[(len(k),city) for k,city in HUELVA_CITIES.items()
                    if re.search(r"(?<!\w)"+re.escape(k)+r"(?!\w)",clean(title))]
        if not candidates:continue
        city=max(candidates,key=lambda p:p[0])[1]
        kind=("TRAIL" if "trail" in low or "montana" in low else
              "CROSS" if "cross" in low else
              "RUNNING")
        key=(d.isoformat(),clean(title))
        if key in seen:continue
        seen.add(key)
        out.append({"fecha":d.isoformat(),"nombre":title,"localidad":city,
                    "provincia":"Huelva","modalidad":kind,"distancia":extract_distance(title),
                    "fuente":DIPHUELVA,"enlace":DIPHUELVA,"origen":"diphuelva"})
    return out
