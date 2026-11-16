"""Distancias explícitas en fichas de UNA carrera, con controles anti falsos positivos.

No se deduce la distancia de nombres como «media maratón» ni se leen
reglamentos o PDF no asociados inequívocamente a esa ficha.
"""
from __future__ import annotations
import re

NUMBER = r"(\d{1,5}(?:[.,]\d{1,3})?)"
UNIT = re.compile(rf"(?<![\w\d]){NUMBER}\s*(kil[oó]metros?|kms?|metros?|mtrs?|mts?|m|k)\b", re.I)
LABEL = re.compile(r"^\s*(?:distancias?|recorridos?|modalidades?|circuitos?|longitud de (?:la )?(?:carrera|prueba|ruta))\s*(?::|[-–]|\s|$)",re.I)
STOP_SECTION = re.compile(
    r"^(?:normativa|reglamento|organiza(?:n|dores)?|patrocinadores|"
    r"colaboradores|informaci[oó]n|contacto|inscripci[oó]n(?:es)?|"
    r"otras pruebas|m[aá]s pruebas|servicios|resultados)\b", re.I)
MAX_DISTANCES = 12


def _one(raw, unit):
    unit = unit.casefold()
    is_m = unit in ("m", "metro", "metros", "mtr", "mtrs", "mt", "mts")
    if is_m:
        # En español «3.000 m» son tres mil metros, no 3 metros.
        if re.fullmatch(r"\d{1,3}[.,]\d{3}", raw):
            value = int(raw.replace(".", "").replace(",", ""))
        else:
            value = float(raw.replace(",", "."))
        if not 100 <= value <= 10000:
            return ""
        if value >= 1000:
            km = value / 1000
            return f"{('%g' % km).replace('.', ',')} km"
        return f"{int(value)} m"
    value = float(raw.replace(",", "."))
    if not 0.2 <= value <= 250:
        return ""
    return f"{('%g' % value).replace('.', ',')} km"


def _values(text, max_values=MAX_DISTANCES):
    found=[]
    content=str(text or "")
    for match in UNIT.finditer(content):
        # "500m+" es normalmente desnivel positivo, no distancia.
        after=content[match.end():match.end()+3].lstrip()
        before=content[max(0,match.start()-35):match.start()]
        if after.startswith("+") or re.search(r"(?:desnivel|elevaci[oó]n|ascenso|d\+)\s*[:+]?\s*$", before, re.I):
            continue
        value=_one(match.group(1),match.group(2))
        if value and value not in found:
            found.append(value)
    if len(found)>max_values:
        return []
    return found


def extract_distance(title="", fragments=()):
    """Título o campos etiquetados de esa ficha, nunca un listado general."""
    title_values=_values(title)
    parts=[str(p).strip() for p in fragments]
    detail_values=[]
    for i,part in enumerate(parts[:240]):
        if not LABEL.match(part) or len(part)>125:
            continue
        # Recortar antes de otra sección: no llevarse publicidad ni recorridos ajenos.
        window=[part]
        for following in parts[i+1:i+4]:
            if STOP_SECTION.match(following):break
            window.append(following)
        detail_values=_values(" ".join(window)[:260])
        if detail_values:break
    if title_values and detail_values and not set(title_values).issubset(set(detail_values)):
        return ""
    return " · ".join(detail_values or title_values)


def extract_races_section(fragments):
    """Gesconchip: distancias de la tabla «CARRERAS» de la ficha del evento.

    Ignora las normativas posteriores, tiempos de salida y «otras carreras».
    Las categorías menores también se conservan si tienen distancia expresa.
    """
    parts=[str(x).strip() for x in fragments]
    # En Gesconchip «PRUEBAS» es también un enlace del menú superior.
    # Usar exclusivamente el encabezado «CARRERAS» de la ficha, para no
    # confundir la navegación con el listado de distancias.
    start=next((i for i,p in enumerate(parts[:180])
                if p.casefold()=="carreras"),None)
    if start is None:return ""
    section=[]
    for p in parts[start+1:start+60]:
        if STOP_SECTION.match(p) or p.upper() in ("ORGANIZA", "NORMATIVA"):
            break
        if len(p)<=125:
            section.append(p)
    # En HTML real la cifra, la unidad y el nombre de la categoría pueden
    # estar repartidos entre spans; reunir solo el bloque CARRERAS del evento.
    return " · ".join(_values(" ".join(section)[:2000]))


def extract_narrative_distance(fragments):
    """Runnink: frase de descripción inicial que menciona carrera y sus kilómetros.

    El llamamiento «Te recomendamos» y los listados externos son frontera
    de seguridad para no contaminar con otra carrera del mismo portal.
    """
    parts=[str(x).strip() for x in fragments][:140]
    end=next((i for i,p in enumerate(parts)
              if re.search(r"^(?:¿?quieres participar|te recomendamos|"
                           r"cierre de inscripciones|comprobar inscripci[oó]n|"
                           r"distribuci[oó]n por sexo|partners tecnol[oó]gicos)",p,re.I)),
             min(len(parts),120))
    useful=[]
    for part in parts[:end]:
        if len(part)>5000:continue
        for sentence in re.split(r"(?<=[.!?])\s+",part):
            if re.search(r"\b(?:carrera|recorrido|prueba|distancia|modalidad|"
                         r"circuito|trazado|itinerario)\b",sentence,re.I) and len(sentence)<=450:
                useful += _values(sentence)
    found=list(dict.fromkeys(useful))
    return " · ".join(found) if len(found)<=MAX_DISTANCES else ""


def extract_booking_distance(fragments):
    """Runnink /book/: solo distancias en las tarjetas de modalidades."""
    parts=[str(x).strip() for x in fragments]
    start=next((i for i,p in enumerate(parts)
                if re.search(r"selecciona la modalidad",p,re.I)),None)
    if start is None:return ""
    found=[]
    for part in parts[start+1:start+90]:
        if re.search(r"^(?:runnink\s*[©®]|pol[ií]tica de cancelaci[oó]n|"
                     r"condiciones de uso)",part,re.I):break
        # Un campo de distancia separado, no marketing, horarios ni precios.
        if len(part)>32 or not UNIT.fullmatch(part.rstrip(". ")):
            continue
        for value in _values(part):
            if value not in found:found.append(value)
    return " · ".join(found) if len(found)<=MAX_DISTANCES else ""


def extract_modalities_distance(fragments):
    """Busca distancias en bloques de modalidades, sin leer el resto de la página.

    Solo se aceptan unidades explícitas y encabezados de carrera. Los
    límites de sección evitan contaminar con publicidad y otros eventos.
    """
    parts=[str(x).strip() for x in fragments][:300]
    found=[]
    headers=re.compile(r"^(?:modalidades?|distancias?|recorridos?|carreras|pruebas disponibles|elige tu distancia)\s*:?\s*$",re.I)
    for i,part in enumerate(parts):
        if not headers.fullmatch(part):continue
        window=[]
        for item in parts[i+1:i+65]:
            if STOP_SECTION.match(item) or re.match(r"^(?:otros eventos|otras carreras|recomendaciones)\b",item,re.I):
                break
            if len(item)>240:break
            window.append(item)
        for value in _values(" ".join(window)[:2500]):
            if value not in found:found.append(value)
        if found:break
    return " · ".join(found) if len(found)<=MAX_DISTANCES else ""
