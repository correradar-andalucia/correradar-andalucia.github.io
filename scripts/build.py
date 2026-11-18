#!/usr/bin/env python3
"""Build static race pages and JSON from a local CSV or Google Sheets published CSV."""
from __future__ import annotations
import csv
import datetime as dt
import hashlib
import html
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
import unicodedata
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '_site'
BASE = 'https://correradar-andalucia.github.io'
CONFIG = json.loads((ROOT/'config'/'site.json').read_text(encoding='utf-8'))
PUBLIC_LAUNCH = bool(CONFIG.get('public_launch', False))
CONTACT = CONFIG.get('contact_email','').strip()
LEGAL_NAME = CONFIG.get('legal_name','').strip()
HOLDER_TYPE = CONFIG.get('holder_type','').strip()
if HOLDER_TYPE not in ('', 'persona_fisica', 'entidad'):
    raise ValueError('holder_type debe ser persona_fisica o entidad')
LEGAL_ADDRESS = CONFIG.get('legal_address','').strip()
if CONFIG.get('site_url',BASE).rstrip('/') != BASE:
    raise ValueError('Esta versión usa el dominio GitHub Pages raíz. Actualiza BASE y enlaces antes de cambiar de dominio.')
if CONTACT and not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+', CONTACT):
    raise ValueError('contact_email no parece una dirección válida')
HEADERS = ['Fecha','Nombre','Localidad','Distancia','Modalidad','Desnivel','Precio','Bolsa','Track','Enlace','Provincia','Estado','Verificado','Fuente','Publicar']
MONTHS = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
MODES = {'ASFALTO':'RUNNING','RUTA':'RUNNING','RUNNING':'RUNNING','TRAIL':'TRAIL','CXM':'TRAIL','MONTANA':'TRAIL','CROSS':'CROSS','CAMPO A TRAVES':'CROSS','ULTRA':'ULTRA','ULTRATRAIL':'ULTRA','RESISTENCIA':'RESISTENCIA','OCR':'OCR','OBSTACULOS':'OCR','HIBRIDA':'HIBRIDA','HYROX':'HIBRIDA','DEKA':'HIBRIDA','ESPECIAL':'ESPECIAL','CIVICO-MILITAR':'ESPECIAL','MIXTA':'MIXTA'}


def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFD',str(s or '')) if unicodedata.category(c) != 'Mn').lower().strip()

def slugify(s):
    s = re.sub('[^a-z0-9]+','-',norm(s)).strip('-')
    return s[:85] or 'carrera'

def date_parse(s):
    s=(s or '').strip()
    for fmt in ('%Y-%m-%d','%d/%m/%Y','%d-%m-%Y','%d.%m.%Y'):
        try:return dt.datetime.strptime(s,fmt).date()
        except ValueError:pass
    raise ValueError(f'Fecha inválida: {s!r}; usa DD/MM/AAAA o AAAA-MM-DD')

def url_clean(s):
    s=(s or '').strip()
    parsed=urlparse(s)
    return s if parsed.scheme in ('https','http') and parsed.netloc else ''

def km_parse(s):
    s=norm(s).replace(',','.')
    m=re.search(r'(?<!\d)(\d+(?:\.\d+)?)\s*(km|kms|kilometros?)\b',s)
    if m:return float(m.group(1))
    m=re.search(r'(?<!\d)(\d+(?:\.\d+)?)\s*m\b',s)
    if m:return round(float(m.group(1))/1000,3)
    if re.fullmatch(r'\d+(?:\.\d+)?',s):return float(s)
    return 0

def load_csv():
    csv_url=os.getenv('SHEET_CSV_URL','').strip()
    if csv_url:
        parsed=urlparse(csv_url)
        if parsed.scheme != 'https' or parsed.hostname not in ('docs.google.com','drive.google.com'):
            raise ValueError('SHEET_CSV_URL debe ser una URL HTTPS de Google Sheets publicada como CSV')
        req=Request(csv_url,headers={'User-Agent':'CorreRadarAndalucia/2.0'})
        with urlopen(req,timeout=30) as resp:
            raw=resp.read(4_000_001)
            if len(raw)>4_000_000:raise ValueError('CSV demasiado grande (>4 MB)')
        data=raw.decode('utf-8-sig')
    else:
        data=(ROOT/'data'/'carreras.csv').read_text(encoding='utf-8-sig')
    rd=csv.DictReader(io.StringIO(data))
    if not rd.fieldnames:raise ValueError('CSV vacío')
    rd.fieldnames=[h.strip() for h in rd.fieldnames]
    missing=[c for c in HEADERS if c not in rd.fieldnames]
    if missing:raise ValueError('Faltan columnas: '+', '.join(missing)+'. Comprueba que el enlace exporta CSV, no HTML.')
    return list(rd)

def transform(rows):
    races=[]; seen=set()
    for rowno,row in enumerate(rows,2):
        if not any((v or '').strip() for v in row.values() if isinstance(v,str)):continue
        if not (row.get('Fecha') or '').strip() and not (row.get('Nombre') or '').strip():continue
        if norm(row.get('Publicar')) not in ('si','yes','true','1'):
            continue  # Publicación por aprobación explícita, nunca por estar en la hoja
        try:
            date=date_parse(row.get('Fecha'))
            name=(row.get('Nombre') or '').strip()
            if not name:raise ValueError('falta el nombre')
            mode=MODES.get(norm(row.get('Modalidad')).upper())
            if not mode:raise ValueError('modalidad desconocida; usa RUNNING, TRAIL, CROSS, ULTRA, RESISTENCIA, OCR, HIBRIDA, ESPECIAL o MIXTA')
            status=norm(row.get('Estado'))
            if status in ('cancelada','cancelado','anulada','anulado'):continue
            if norm(row.get('Estado')) in ('pendiente','sin confirmar','por confirmar','prevista'):
                raise ValueError('no publicar carreras con estado no confirmado')
            if not url_clean(row.get('Fuente')):
                raise ValueError('una carrera publicada debe tener URL de fuente verificable')
            if not (row.get('Verificado') or '').strip():
                raise ValueError('una carrera publicada necesita fecha de verificación')
            base=slugify(f'{name}-{row.get("Localidad","")}-{date.isoformat()}')
            slug=base
            if slug in seen:slug=f'{base}-{hashlib.sha1(str(rowno).encode()).hexdigest()[:6]}'
            seen.add(slug)
            item={'fecha':date.isoformat(),'nombre':name,'localidad':(row.get('Localidad') or '').strip(),
                  'provincia':(row.get('Provincia') or '').strip(),'distancia':(row.get('Distancia') or '').strip(),
                  'km':km_parse(row.get('Distancia')),'modalidad':mode,'desnivel':(row.get('Desnivel') or '').strip(),
                  'precio':(row.get('Precio') or '').strip(),'bolsa':(row.get('Bolsa') or '').strip(),
                  'track':url_clean(row.get('Track')),'enlace':url_clean(row.get('Enlace')),
                  'estado':(row.get('Estado') or '').strip(),'verificado':(row.get('Verificado') or '').strip(), 'fuente':url_clean(row.get('Fuente')),
                  'slug':slug}
            races.append(item)
        except ValueError as exc:
            raise ValueError(f'Fila {rowno}: {exc}') from exc
    return sorted(races,key=lambda r:r['fecha'])

def add_curated_distances(races, catalog=None):
    """Solo rellenar huecos con datos de la misma edición y municipio.

    Los conflictos NO sustituyen lo que diga una fuente consultada en vivo.
    """
    if catalog is None:
        # Cada cotejo conserva su fecha; agregar un archivo no renueva los antiguos.
        entries=[]
        for path in sorted((ROOT/"data").glob("distancias_cotejadas_*.json")):
            document=json.loads(path.read_text(encoding="utf-8"))
            entries.extend(document.get("carreras",[]))
        catalog={"carreras":entries}
    applied=0;conflicts=0
    seen=set()
    by_key={(r["fecha"],norm(r["nombre"]),norm(r["localidad"]),norm(r["provincia"])):r
            for r in races}
    for item in catalog.get("carreras",[]):
        key=(item["fecha"],norm(item["nombre"]),norm(item["localidad"]),norm(item["provincia"]))
        if key in seen:raise ValueError("Distancia cotejada repetida: "+str(key))
        seen.add(key)
        dt.date.fromisoformat(item["fecha"])
        dt.date.fromisoformat(item["cotejada"])
        if not item["fuente"].startswith("https://") or not item["distancia"].strip():
            raise ValueError("Distancia cotejada sin fuente HTTPS ni valor")
        race=by_key.get(key)
        if race is None:continue
        if race.get("distancia"):
            if race["distancia"]!=item["distancia"]:
                conflicts+=1
            continue
        race["distancia"]=item["distancia"]
        race["distancia_origen"]="fuente"
        race["distancia_fuente"]=item["fuente"]
        race["distancia_cotejada"]=item["cotejada"]
        if item.get("aproximada") is True:
            race["distancia_aproximada"]=True
        race["km"]=km_parse(item["distancia"])
        applied+=1
    return {"aplicadas":applied,"conflictos_no_sobrescritos":conflicts}


def add_curated_times(races, catalog=None, today=None):
    """Añadir solo horarios cotejados de la misma edición, sin sustituir datos actuales."""
    from control_calidad import valid_source
    today=today or dt.date.today()
    if catalog is None:
        entries=[]
        for path in sorted((ROOT/"data").glob("horarios_cotejados_*.json")):
            entries.extend(json.loads(path.read_text(encoding="utf-8"))["carreras"])
        catalog={"carreras":entries}
    def key(item):
        return (item["fecha"],norm(item["nombre"]),norm(item["localidad"]),norm(item["provincia"]))
    matches={}
    for race in races:
        matches.setdefault(key(race),[]).append(race)
    seen=set()
    applied=0
    conflicts=0
    for item in catalog["carreras"]:
        identity=key(item)
        hour=item["hora"]
        stamp=dt.date.fromisoformat(item["cotejada"])
        day=dt.date.fromisoformat(item["fecha"])
        if (identity in seen or not isinstance(hour,str)
            or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",hour)
            or not valid_source(item["fuente"]) or stamp>today or stamp>day):
            raise ValueError("Horario cotejado inválido o repetido: "+str(identity))
        seen.add(identity)
        rows=matches.get(identity,[])
        if len(rows)!=1 or day<today:
            continue
        race=rows[0]
        if race.get("hora") and race["hora"]!=hour:
            conflicts+=1
            continue
        if race.get("confirmada") or race.get("hora"):
            continue
        race.update(hora=hour,hora_origen="fuente",hora_fuente=item["fuente"],
                    hora_cotejada=stamp.isoformat(),hora_nota=str(item.get("nota",""))[:240])
        applied+=1
    return {"aplicadas":applied,"conflictos_no_sobrescritos":conflicts}


def add_granada_cross_notes(races):
    """Distancias orientativas 2026/27: nunca tratarlas como kilómetros exactos."""
    rounds={
        "2026-12-13":"Lecrín", "2026-12-19":"La Zubia",
        "2027-01-16":"Baza", "2027-01-24":"Freila", "2027-01-31":"Las Gabias",
        "2027-02-07":"Quéntar", "2027-02-13":"Moraleda de Zafayona",
        "2027-02-27":"Guadix", "2027-03-07":"Alhendín", "2027-03-13":"Íllora",
    }
    count=0
    for race in races:
        city=rounds.get(race.get("fecha"))
        if (city and norm(race.get("localidad",""))==norm(city)
                and race.get("provincia")=="Granada"
                and norm(race.get("nombre","")).startswith("xxx circuito provincial de campo a traves")
                and not race.get("distancia")):
            race["distancia_orientativa"]="Senior/Sub-23: 5,5–8 km; máster: 3,5–5,5 km. Aproximadas según sede; confirmar cada categoría."
            race["distancia_orientativa_fuente"]="https://www.dipgra.es/export/sites/diputaciongranada/servicios/areas/deportes/.galleries/AREAS-Deportes-Documentos/Normativa-Cross-2027.pdf"
            count+=1
    return count


def preserve_previous_distances(races, previous_path=None, today=None):
    """Recuperar un dato de una publicación propia, sin revalidarlo por silencio.

    Solo misma edición y enlace de fuente, con cotejo fechado reciente.
    No se conserva una contradicción ni se crea una carrera desde la caché.
    """
    from control_calidad import valid_source
    from distancias import extract_distance
    from captacion import SOURCES, fuentes_habilitadas
    today=today or dt.date.today()
    previous_path=previous_path or os.environ.get("CORRERADAR_PREVIOUS_CALENDAR")
    if not previous_path:
        return {"recuperadas":0,"estado":"sin respaldo"}
    try:
        path=Path(previous_path)
        if path.stat().st_size>3_000_000:
            raise ValueError("Respaldo demasiado grande")
        old=json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(old,dict) or not isinstance(old.get("carreras"),list):
            raise ValueError("Respaldo inválido")
    except (OSError,ValueError,TypeError):
        return {"recuperadas":0,"estado":"respaldo no disponible"}
    allowed={urlparse(SOURCES[s]).hostname for s in fuentes_habilitadas()}
    # No extrapolar por nombre parecido, no usar fichas de otra edición/municipio.
    def key(r):
        return tuple(str(r.get(k) or "") for k in ("fecha","nombre","localidad","provincia"))
    by_key={}
    for item in old["carreras"]:
        if isinstance(item,dict):
            by_key.setdefault(key(item),[]).append(item)
    recovered=0
    for row in races:
        if row.get("distancia") or row.get("confirmada"):
            continue
        candidates=by_key.get(key(row),[])
        if len(candidates)!=1:
            continue
        item=candidates[0]
        source=item.get("distancia_fuente")
        distance=item.get("distancia")
        if not valid_source(source) or not isinstance(distance,str):
            continue
        if urlparse(source).hostname not in allowed:
            continue
        if source not in (row.get("enlace"),row.get("fuente")):
            continue
        # Sólo valores explícitos normalizados de la propia lectura anterior.
        if extract_distance(distance)!=distance or not distance or len(distance)>140:
            continue
        if item.get("distancia_origen") not in ("fuente","catalogo"):
            continue
        stamp=item.get("distancia_cotejada")
        try:
            checked=dt.date.fromisoformat(stamp)
            event_day=dt.date.fromisoformat(row["fecha"])
        except (TypeError,ValueError):
            continue
        if not (0<=(today-checked).days<=30 and event_day>=today):
            continue
        row.update(distancia=distance,distancia_origen="catalogo",
                   distancia_fuente=source,distancia_cotejada=stamp,
                   km=km_parse(distance))
        if item.get("distancia_aproximada") is True:
            row["distancia_aproximada"]=True
        recovered+=1
    return {"recuperadas":recovered,"estado":"respaldo consultado"}


def esc(s):return html.escape(str(s),quote=True)

def legal_footer():
    return '<footer class="footer"><div class="wrap"><nav class="footer-links" aria-label="Información y contacto"><a href="/">Inicio</a><a href="/contacto/">Contacto</a><a href="/aviso-legal/">Aviso legal</a><a href="/privacidad/">Privacidad</a><a href="/cookies/">Cookies</a></nav><p>Calendario independiente. Confirma siempre los datos en la web del organizador.</p></div></footer>'

def legal_page(title, body, noindex=False):
    # Estas páginas informan sobre el proyecto sin fingir que hay un titular o correo ya configurados.
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><meta name="theme-color" content="#0b1112"><meta name="description" content="{esc(title)} de CorreRadar Andalucía"><link rel="canonical" href="{BASE}/{ {'Aviso legal':'aviso-legal','Privacidad':'privacidad','Cookies':'cookies','Contacto':'contacto'}[title] }/"><link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/styles.css">{('<meta name="robots" content="noindex">' if noindex else '')}<title>{esc(title)} | CorreRadar Andalucía</title></head><body><div class="topline"></div><header class="header wrap"><a class="brand" href="/"><span class="brand-mark">↗</span><span class="brand-type">CORRERADAR <strong>ANDALUCÍA<span class="brand-dot">.</span></strong></span></a><a class="header-cta" href="/">Calendario ↗</a></header><main class="legal-main wrap"><div class="section-kicker">/ INFORMACIÓN DEL PROYECTO</div><h1>{esc(title)}<span class="period">.</span></h1><div class="legal-copy">{body}</div></main>{legal_footer()}</body></html>'''

def legal_pages():
    """Información pública fiel al código y a las dependencias, sin certificaciones ficticias.

    Estos textos identifican los tratamientos reales de la versión en
    preparación. No equivalen a una auditoría de cumplimiento RGPD/LSSI.
    """
    email_link=(f'<a href="mailto:{esc(CONTACT)}">{esc(CONTACT)}</a>' if CONTACT
                else '<strong>[CORREO DE CONTACTO PENDIENTE]</strong>')
    identity=(f'<strong>{esc(LEGAL_NAME)}</strong>' if LEGAL_NAME
              else ('<strong>[NOMBRE Y APELLIDOS DEL TITULAR PENDIENTES]</strong>'
                    if HOLDER_TYPE=='persona_fisica'
                    else '<strong>[TITULAR RESPONSABLE: IDENTIDAD PENDIENTE DE COMPLETAR]</strong>'))
    owner_label=('Persona física responsable, en nombre propio'
                 if HOLDER_TYPE=='persona_fisica'
                 else 'Titular o responsable del sitio')
    owner_privacy=('una persona física que actúa en nombre propio, '
                   'no una sociedad ni una asociación'
                   if HOLDER_TYPE=='persona_fisica' else 'el titular indicado')
    # CorreRadar es el nombre del proyecto, no sustituye a la identidad del
    # responsable del tratamiento exigida por el artículo 13 del RGPD.

    address=(esc(LEGAL_ADDRESS) if LEGAL_ADDRESS
             else '[DOMICILIO: PENDIENTE DE DETERMINAR Y PUBLICAR CUANDO SEA EXIGIBLE]')
    unresolved=(not LEGAL_NAME or not CONFIG.get("legal_review_complete",False))
    status=(
        '<p class="notice"><strong>Información legal en revisión antes del lanzamiento.</strong> '
        + ('Es necesario identificar al titular, ' if not LEGAL_NAME else '')
        + 'Queda pendiente resolver los datos exigibles conforme a la LSSI, '
        'verificar proveedores y posibles transferencias internacionales y documentar '
        'el análisis jurídico de este texto y de los derechos de reutilización de las fuentes. '
        'No se afirma que la web esté certificada ni que cuente con autorización de todas las fuentes.</p>'
        if unresolved else ''
    )
    updated=dt.date.today().strftime("%d/%m/%Y")

    legal=f'''{status}
<h2>Identificación del proyecto</h2>
<p>CorreRadar Andalucía es un calendario informativo independiente de carreras populares, montaña y obstáculos en Andalucía. No es el organizador de las pruebas, no presta servicios de cronometraje y no gestiona inscripciones ni pagos.</p>
<p>{owner_label}: {identity}<br>Correo de contacto: {email_link}<br>Domicilio: {address}</p>
<p>Si el proyecto constituye un servicio de la sociedad de la información sujeto a la Ley 34/2002, se facilitarán los datos adicionales exigibles por su artículo 10 (entre ellos NIF y, según proceda, información registral). La situación legal del titular debe comprobarse antes del lanzamiento público.</p>
<h2>Información deportiva y exactitud</h2>
<p>Las fichas muestran datos básicos de carreras, procedentes de organizaciones, federaciones, administraciones, servicios de cronometraje y revisiones editoriales puntuales. Su publicación no implica una homologación ni aprobación del evento por CorreRadar. Las fechas, horarios, recorridos, disponibilidad o condiciones de inscripción pueden variar. Debes contrastar la información antes de inscribirte o viajar.</p>
<h2>Fuentes, atribución y propiedad intelectual</h2>
<p>El proyecto pretende utilizar únicamente hechos básicos sobre cada prueba y enlaces a sus fuentes: no importa fotografías, vídeos, textos extensos, reglamentos completos, clasificaciones ni datos personales de atletas. Las denominaciones y marcas de terceros pertenecen a sus titulares. El hecho de que una fuente sea pública o permita su acceso mediante robots.txt no equivale a una autorización para reproducir su base de datos.</p>
<p>Algunas fuentes contienen reservas expresas de derechos y otras requieren comprobar condiciones o licencias aplicables. La captación automatizada está sometida a límites técnicos y a una revisión documental pendiente de cerrar antes del lanzamiento. Si eres titular de derechos y observas un problema, escribe a {email_link} indicando la ficha y el motivo para solicitar revisión o retirada.</p>
<h2>Enlaces a inscripciones y otras webs</h2>
<p>Los enlaces externos se abren voluntariamente en la web del tercero, con sus propias condiciones y políticas de privacidad y cookies. No existe afiliación, patrocinio ni relación comercial implícita con estas plataformas. Las páginas de terceros pueden modificar sus contenidos sin intervención de CorreRadar.</p>
<h2>Publicidad</h2>
<p>El código de la versión actual no integra anuncios, enlaces de afiliación, servicios de venta ni perfiles publicitarios. Si esto cambia, se actualizarán el aviso legal, la privacidad y la política de cookies antes de activar esos servicios.</p>
<p><small>Revisión técnica del contenido: {updated}. Su exactitud jurídica definitiva está pendiente de validación por el titular.</small></p>'''

    privacy=f'''{status}
<h2>Responsable del tratamiento</h2>
<p>El responsable del tratamiento es {owner_privacy}: {identity}. «CorreRadar Andalucía» identifica el proyecto, no una persona jurídica distinta. Contacto para asuntos de privacidad y ejercicio de derechos: {email_link}. {'El nombre y apellidos del responsable aún deben completarse antes del lanzamiento.' if not LEGAL_NAME else ''}</p>
<h2>Qué información utilizamos y para qué</h2>
<p>La web pública no solicita registro, no dispone de formularios de usuario, no ofrece suscripciones y no tiene funciones propias de seguimiento del visitante. La búsqueda y los filtros del calendario se realizan localmente en tu navegador con archivos estáticos del sitio; no enviamos a CorreRadar tus términos de búsqueda ni preferencias.</p>
<p>Si escribes voluntariamente al correo de contacto indicado, tratamos la identidad y dirección de correo del remitente, asunto, mensaje y datos que decidas aportar para responder, atender correcciones y gestionar consultas de organizadores. No solicitamos DNI, datos médicos, inscripciones, tiempos ni datos personales de atletas: evita incluirlos en tus mensajes.</p>
<h2>Datos de avisos editoriales y detección de carreras</h2>
<p>La detección de posibles pruebas de Global Tempo utiliza resultados indexados comunicados mediante un feed RSS de Google Alerts, no una consulta automática al calendario de Global Tempo. Los procesos internos de GitHub Actions pueden crear incidencias de revisión en GitHub con el nombre de una prueba, su enlace y la fecha del aviso; esta última no equivale a la fecha de celebración. Antes de publicarse, un responsable debe revisar y aprobar cada enlace. Las incidencias en un repositorio público pueden ser visibles para cualquier persona: no incluyas datos personales de participantes ni información confidencial en propuestas o comentarios. Solo los enlaces aprobados se muestran en una sección diferenciada, sin fecha ni datos de personas participantes.</p>
<p>Otras fuentes deportivas se consultan en tareas programadas del servidor para obtener datos básicos de pruebas. CorreRadar no recopila listas de inscritos, clasificaciones nominales ni perfiles de deportistas. La licitud de la reutilización de calendarios y las condiciones de cada fuente se revisan separadamente de esta política de protección de datos.</p>
<h2>Base jurídica</h2>
<p>Para atender correcciones, sugerencias y comunicaciones voluntarias usamos, como criterio de legitimación, el interés legítimo del responsable en gestionar consultas relacionadas con el proyecto (artículo 6.1.f RGPD), ponderado frente a los derechos de la persona que escribe. Cuando una petición se refiera a medidas precontractuales solicitadas por la persona interesada, podrá resultar aplicable el artículo 6.1.b; si existe una obligación legal, el artículo 6.1.c. Las funciones de búsqueda del calendario no requieren que nos facilites datos personales. No utilizamos publicidad comportamental ni fundamentamos sus tratamientos en un consentimiento ficticio.</p>
<h2>Alojamiento y destinatarios</h2>
<p>La página se publica en <a href="https://docs.github.com/es/pages/getting-started-with-github-pages/what-is-github-pages" rel="noopener noreferrer" referrerpolicy="no-referrer" target="_blank">GitHub Pages</a>. GitHub informa de que registra las direcciones IP de los visitantes para proteger el servicio, incluso sin iniciar sesión. El titular de CorreRadar no recibe directamente esas direcciones desde el código de la web ni instala un programa de analítica propio.</p>
<p>La dirección de contacto utiliza Gmail (Google): el proveedor de correo procesa los datos necesarios para recibir y gestionar mensajes. GitHub aloja el código, las incidencias editoriales, GitHub Actions y GitHub Pages; Google Alerts proporciona avisos de resultados indexados. No hay acceso de estas herramientas internas a tu navegación ni a tus búsquedas en CorreRadar. Al entrar voluntariamente en una plataforma de inscripción, ésta realiza sus propios tratamientos y aplica su propia política de privacidad; CorreRadar no recibe por ese enlace los datos de inscripción ni de pago.</p>
<p>Los proveedores tecnológicos pueden tratar información en otros países, incluidos terceros países fuera del Espacio Económico Europeo, conforme a sus prácticas y garantías aplicables. Antes del lanzamiento queda pendiente comprobar y documentar los roles de Google y GitHub, sus condiciones, mecanismos de transferencia internacional y, cuando proceda, los contratos o garantías correspondientes. No afirmamos disponer de todas esas verificaciones completadas.</p>
<h2>Conservación y acceso</h2>
<p>Los correos de consulta se conservan mientras sea necesario tramitar y responder la comunicación y, después, únicamente si existe una finalidad legítima pendiente, una reclamación o un plazo de conservación legal aplicable. Los avisos editoriales en GitHub se revisan hasta su aprobación o descarte y pueden permanecer en el historial del repositorio, accesible públicamente. No se publican los correos recibidos ni se venden datos personales.</p>
<p>El responsable debe establecer y aplicar una revisión periódica de los correos y de las incidencias, documentar sus criterios de supresión y atender las solicitudes de retirada de datos personales. Esta página informa de los criterios, pero no significa que exista ya un borrado automático configurado.</p>
<h2>Derechos y reclamaciones</h2>
<p>Puedes solicitar el acceso, rectificación, supresión, oposición (incluido frente al interés legítimo), limitación y, cuando proceda, portabilidad de tus datos escribiendo a {email_link}. Si algún tratamiento se basase en tu consentimiento, podrías retirarlo en cualquier momento, sin efecto retroactivo. También tienes derecho a presentar una reclamación ante la <a href="https://www.aepd.es/" rel="noopener noreferrer" referrerpolicy="no-referrer" target="_blank">Agencia Española de Protección de Datos (AEPD)</a>. Para proteger tus datos, podremos solicitar información razonable para verificar la identidad cuando sea necesario, sin pedir más datos de los necesarios.</p>
<h2>Cambios y contacto</h2>
<p>Si se incorporan formularios, cuentas, analítica, newsletters, anuncios o nuevos proveedores se actualizará esta información antes de activarlos. Fecha de revisión del texto: {updated}.</p>'''

    cookies=f'''{status}
<h2>Resumen de cookies de esta versión</h2>
<p>La versión actual de CorreRadar es estática. Su código no crea cookies propias, no llama a Google Analytics, Meta Pixel ni herramientas de marketing, y no utiliza localStorage, sessionStorage ni identificadores de seguimiento. Los filtros funcionan en el navegador sin guardar perfiles. No se incrustan mapas, vídeos ni formularios de terceros que se carguen antes de hacer clic.</p>
<h2>Cookies de infraestructura</h2>
<p>El sitio se aloja en GitHub Pages. La infraestructura de alojamiento podría utilizar medidas técnicas necesarias de seguridad o prestación del servicio que escapan al código de CorreRadar. No afirmamos haber realizado una auditoría completa de las cookies que pueda establecer el proveedor en todos los navegadores. GitHub documenta la recogida de direcciones IP para seguridad, lo que no equivale por sí solo a una cookie.</p>
<h2>¿Por qué no aparece un banner de aceptación?</h2>
<p>Según la versión de código examinada, no utilizamos cookies propias ni tecnologías no esenciales sujetas a consentimiento. Por eso no mostramos un banner de «aceptar»/«rechazar» vacío. Las cookies estrictamente necesarias de infraestructura, si existieran, se rigen por su función técnica. Antes de introducir cookies de analítica, publicidad o personalización no esenciales se implementaría un sistema de consentimiento válido con opciones equivalentes para aceptar y rechazar y posibilidad de retirar el consentimiento.</p>
<h2>Enlaces a otros sitios</h2>
<p>Al abrir una ficha de inscripción, una federación o el sitio de un organizador sales de CorreRadar. Esas webs gestionan sus propias cookies; consulta sus políticas. El sitio no incorpora sus contenidos mediante iframes ni realiza solicitudes a esos dominios desde tu navegador mientras navegas en CorreRadar.</p>
<h2>Comprobación y cambios</h2>
<p>Para examinar las cookies técnicas de un navegador puedes abrir sus herramientas de desarrollo, apartado «Application» o «Storage», y revisar «Cookies» después de cargar esta web. Si cambian las dependencias o la política de GitHub Pages, esta información deberá revisarse. Última revisión del código: {updated}.</p>'''

    contact=f'''{status}
<h2>Escríbenos</h2><p>Para proponer una carrera, avisar de errores, solicitar una rectificación o consultar una colaboración: {email_link}.</p>
<p>Los datos que incluyas en un correo se utilizarán para gestionar la comunicación. Consulta la <a href="/privacidad/">política de privacidad</a> antes de escribirnos.</p>
<h2>Organizadores</h2><p>Indica nombre de la carrera, edición, fecha, municipio y enlace específico al organizador o inscripción para facilitar el cotejo. No envíes datos personales de participantes ni contenido protegido sin autorización.</p>'''
    return {'aviso-legal':('Aviso legal',legal),
            'privacidad':('Privacidad',privacy),
            'cookies':('Cookies',cookies),
            'contacto':('Contacto',contact)}

def detail_page(r):
    date=dt.date.fromisoformat(r['fecha'])
    fmt=f'{date.day} de {MONTHS[date.month-1]} de {date.year}'
    city=', '.join(filter(None,[r['localidad'],r['provincia']]))
    title=f'{r["nombre"]} — {fmt} | CorreRadar Andalucía'
    desc=f'Información de {r["nombre"]} en {city}: fecha y detalles orientativos; confirma en el organizador.'[:155]
    path=f'/carreras/{r["slug"]}/'
    is_confirmed = bool(r.get('confirmada'))
    mode = ('Por confirmar' if r.get('modalidad_conflicto')
            else 'Asfalto' if r['modalidad']=='RUNNING' else r['modalidad'].title())
    fecha_origen=r.get('fecha_origen', 'editorial' if is_confirmed else 'catalogo')
    distancia_origen={'editorial':'revisada por CorreRadar',
                      'fuente':'publicada en la fuente',
                      'catalogo':'cotejada en el catálogo'}.get(r.get('distancia_origen'),'')
    entries=[('Fecha',fmt),
             ('Hora de salida',r.get('hora','')+' h' if r.get('hora') else ''),
             ('Localidad',city),('Modalidad',mode)]
    if r.get('distancia') and distancia_origen:
        entries.append(('Distancia',r['distancia']+(' (aprox.)' if r.get('distancia_aproximada') else '')+' · '+distancia_origen))
    from estado_inscripciones import LABELS
    registration_status=r.get("inscripcion_estado","desconocida")
    if registration_status!="desconocida" and r.get("inscripcion_consultada"):
        entries.append(("Inscripciones en última consulta",LABELS.get(registration_status,"Sin información actual")))
    else:
        entries.append(("Inscripciones","Sin estado actual comprobado"))
    if r.get("inscripcion_apertura"):
        entries.append(("Apertura anunciada",r["inscripcion_apertura"]))
    if r.get("inscripcion_limite"):
        entries.append(("Cierre anunciado",r["inscripcion_limite"]+(" "+r["inscripcion_hora_limite"]+" h" if r.get("inscripcion_hora_limite") else "")))
    if r.get("inscripcion_consultada"):
        entries.append(("Inscripción consultada el",r["inscripcion_consultada"]))
    if r.get("hora_nota"):
        entries.append(("Detalle de salidas",r["hora_nota"]))
    if r.get("hora_cotejada"):
        entries.append(("Horario cotejado el",r["hora_cotejada"]))
    if r.get("distancia_cotejada"):
        entries.append(("Distancia cotejada el",r["distancia_cotejada"]))
    if not r.get("distancia") and r.get("distancia_orientativa"):
        entries.append(("Distancias orientativas",r["distancia_orientativa"]))
    if is_confirmed:
        entries += [('Desnivel',r['desnivel']),
                    ('Precio',r['precio']),('Bolsa del corredor',r['bolsa'])]
    consultado=str(r.get('consultado','') or '')
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}',consultado):
        consultado=consultado[8:10]+'/'+consultado[5:7]+'/'+consultado[:4]
    consulta_label=('Consulta anterior de la fuente' if fecha_origen=='catalogo'
                    else 'Fuente consultada')
    if r.get('respaldo_temporal'):
        entries.append(('Estado de consulta','Fuente temporalmente no disponible. Fecha pendiente de reconfirmar.'))
    entries += [(consulta_label,consultado if not is_confirmed else ''),
                ('Última revisión editorial',r.get('verificado','') if is_confirmed else '')]
    lines='\n'.join(f'<div class="detail-line"><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>' for k,v in entries if v)
    buttons=''
    provisional=not is_confirmed
    if r['enlace']:buttons+=f'<a href="{esc(r["enlace"])}" rel="noopener noreferrer" target="_blank">{("Comprobar en la fuente ↗" if provisional else "Ver enlace de la carrera ↗")}</a>'
    if r.get('fuente') and r['fuente']!=r.get('enlace'):buttons+=f'<a class="secondary" href="{esc(r["fuente"])}" rel="noopener noreferrer" target="_blank">Fuente de verificación ↗</a>'
    if r.get("distancia") and url_clean(r.get("distancia_fuente","")) and r.get("distancia_fuente") != r.get("enlace"):
        buttons+=f'<a class="secondary" href="{esc(r["distancia_fuente"])}" rel="noopener noreferrer" target="_blank">Ver distancia en la fuente ↗</a>'
    if r.get("hora") and url_clean(r.get("hora_fuente","")) and r.get("hora_fuente") not in (r.get("enlace"),r.get("distancia_fuente")):
        buttons+=f'<a class="secondary" href="{esc(r["hora_fuente"])}" rel="noopener noreferrer" target="_blank">Ver horarios en la fuente ↗</a>'
    if r.get("inscripcion_fuente") and url_clean(r["inscripcion_fuente"]) and r["inscripcion_fuente"] not in (r.get("enlace"),r.get("fuente"),r.get("distancia_fuente"),r.get("hora_fuente")):
        buttons+=f'<a class="secondary" href="{esc(r["inscripcion_fuente"])}" rel="noopener noreferrer" target="_blank">Comprobar estado de inscripción ↗</a>'
    if not r.get("distancia") and url_clean(r.get("distancia_orientativa_fuente","")):
        buttons+=f'<a class="secondary" href="{esc(r["distancia_orientativa_fuente"])}" rel="noopener noreferrer" target="_blank">Normativa de distancias orientativas ↗</a>'
    if (r.get("inscripcion_enlace") and url_clean(r["inscripcion_enlace"])
            and r["inscripcion_enlace"]!=r.get("enlace")):
        buttons+=f'<a class="secondary" href="{esc(r["inscripcion_enlace"])}" rel="noopener noreferrer" target="_blank">Inscripción en Global Tempo ↗</a>'
    if is_confirmed and r['track']:buttons+=f'<a class="secondary" href="{esc(r["track"])}" rel="noopener noreferrer" target="_blank">Ver track ↗</a>'
    if not buttons:buttons='<p>Enlaces oficiales pendientes de verificación.</p>'
    ld={'@context':'https://schema.org','@type':'SportsEvent','name':r['nombre'],'startDate':r['fecha'],
        'eventAttendanceMode':'https://schema.org/OfflineEventAttendanceMode','url':BASE+path,
        'location':{'@type':'Place','name':r['localidad'],'address':{'@type':'PostalAddress','addressLocality':r['localidad'],'addressRegion':r['provincia'],'addressCountry':'ES'}}}
    if r['enlace']:ld['sameAs']=r['enlace']
    structured=json.dumps(ld,ensure_ascii=False).replace('<','\\u003c')
    structured_tag = (f'<script type="application/ld+json">{structured}</script>' if is_confirmed else '')
    provisional_robots = '' if is_confirmed else '<meta name="robots" content="noindex,follow">'
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0b1112"><meta name="referrer" content="no-referrer">{provisional_robots}<meta name="description" content="{esc(desc)}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{BASE+path}"><link rel="canonical" href="{BASE+path}"><link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/styles.css">{structured_tag}<title>{esc(title)}</title></head><body><div class="topline"></div><header class="header wrap"><a class="brand" href="/"><span class="brand-mark" aria-hidden="true">↗</span><span class="brand-type">CORRERADAR <strong>ANDALUCÍA<span class="brand-dot">.</span></strong></span></a><a class="header-cta" href="/">Calendario ↗</a></header><main class="detail-main wrap"><a class="detail-back" href="/">← VOLVER AL CALENDARIO</a><div class="section-kicker" style="margin-top:48px">/ FICHA DE CARRERA</div><h1>{esc(r['nombre'])}<span class="period">.</span></h1><p class="detail-lead">{esc(fmt)} · {esc(city)}</p><div class="detail-grid"><dl class="detail-list">{lines}</dl><aside class="detail-side"><h2>PREPARA TU SALIDA.</h2>{buttons}<p class="disclaimer">Los datos pueden variar. Confirma siempre los detalles en la web del organizador.</p></aside></div></main>{legal_footer()}</body></html>'''

def sitemap(races):
    ET.register_namespace('', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    root=ET.Element('{http://www.sitemaps.org/schemas/sitemap/0.9}urlset')
    for path in ['/','/aviso-legal/','/privacidad/','/cookies/','/contacto/']+[f'/carreras/{r["slug"]}/' for r in races if r.get('confirmada')]:
        u=ET.SubElement(root,'{http://www.sitemaps.org/schemas/sitemap/0.9}url')
        ET.SubElement(u,'{http://www.sitemaps.org/schemas/sitemap/0.9}loc').text=BASE+path
    return ET.tostring(root,encoding='unicode',xml_declaration=True)

def main():
    from multifuente import seed_races, backup_runnink
    from oficiales import official_races
    from deduplicacion import combine, verify_unique
    from control_calidad import check_launch_ready, inspect_calendar
    from enlaces_inscripcion import match_registrations
    from alertas_globaltempo import approved_items, publication_candidates
    from captacion import collect
    from persistencia import read_previous, restore_missing, distance_backlog
    from estado_inscripciones import apply_current_registrations
    # Ninguna configuración accidental puede publicar una web sin revisión legal.
    check_launch_ready(CONFIG)
    candidatas_en_vivo, informe_captacion = collect()
    oficiales=official_races()
    races, auditoria = combine(transform(load_csv()), oficiales+seed_races()+backup_runnink()+candidatas_en_vivo,
                               slugify, km_parse, with_audit=True)
    # Las fichas de Global Tempo solo aportan enlaces si una fuente diferente
    # prueba la MISMA edición; el directorio jamás crea carreras.
    auditoria["enlaces_globaltempo"]=match_registrations(
        races, [*candidatas_en_vivo,
                *(r for r in oficiales if r.get("origen") not in ("globaltempo_cotejo",))])
    auditoria["respaldo_carreras"]=restore_missing(races,
        read_previous(os.environ.get("CORRERADAR_PREVIOUS_CALENDAR")),
        informe_captacion,slugify,km_parse)
    auditoria["distancias_cotejadas"]=add_curated_distances(races)
    auditoria["horarios_cotejados"]=add_curated_times(races)
    auditoria["inscripciones"]=apply_current_registrations(races,candidatas_en_vivo)
    auditoria["distancias_conservadas"]=preserve_previous_distances(races)
    auditoria["cross_distancias_orientativas"]=add_granada_cross_notes(races)
    auditoria["fichas_oficiales_cotejadas"]=len(oficiales)
    provincias=["Almería","Cádiz","Córdoba","Granada","Huelva","Jaén","Málaga","Sevilla"]
    cobertura={
        "actualizado":dt.date.today().isoformat(),
        "total":len(races),
        "con_distancia":sum(bool(r.get("distancia")) for r in races),
        "con_hora":sum(bool(r.get("hora")) for r in races),
        "inscripciones":auditoria["inscripciones"],
        "por_provincia":{p:len([r for r in races if r.get("provincia")==p]) for p in provincias},
        "fuentes_oficiales_cotejadas":len(oficiales),
        "fecha_cotejada":sum(r.get("fecha_origen")=="catalogo" for r in races),
        "fecha_fuente":sum(r.get("fecha_origen")=="fuente" for r in races)
    }
    verify_unique(races)
    calidad = inspect_calendar(races, informe_captacion)
    if not calidad["apto_para_desplegar"]:
        raise ValueError("PUBLICACIÓN BLOQUEADA POR CALIDAD: "
                         + " | ".join(calidad["bloqueos"][:12]))
    print("CONTROL DE CALIDAD:", json.dumps(calidad,ensure_ascii=False))
    print("AUDITORÍA DUPLICADOS:",json.dumps(auditoria,ensure_ascii=False))
    print("Captación multifuente:", json.dumps(informe_captacion, ensure_ascii=False))
    if OUT.exists():shutil.rmtree(OUT)
    OUT.mkdir()
    for filename in ['index.html','robots.txt']:
        shutil.copy2(ROOT/filename,OUT/filename)
    shutil.copytree(ROOT/'assets',OUT/'assets')
    (OUT/'.nojekyll').touch()
    (OUT/'data').mkdir()
    (OUT/'data'/'carreras.json').write_text(json.dumps({'actualizado':dt.date.today().strftime('%d/%m/%Y'),'carreras':races},ensure_ascii=False,separators=(',',':')),encoding='utf8')
    (OUT/'data'/'estado_fuentes.json').write_text(json.dumps(informe_captacion,ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'data'/'auditoria_duplicados.json').write_text(json.dumps(auditoria,ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'data'/'cobertura.json').write_text(json.dumps(cobertura,ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'data'/'distancias_pendientes.json').write_text(
        json.dumps(distance_backlog(races),ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'data'/'control_calidad.json').write_text(
        json.dumps(calidad,ensure_ascii=False,indent=2),encoding='utf8')
    # Independiente del calendario fechado: nombre + enlace solo tras
    # aprobación editorial manual en GitHub, nunca a partir de la alerta RSS.
    published_links=publication_candidates(approved_items())
    (OUT/'data'/'globaltempo_enlaces.json').write_text(
        json.dumps({"enlaces":published_links},ensure_ascii=False,indent=2),encoding='utf8')
    catalogo = ROOT/'config'/'catalogo_fuentes_maestra.json'
    if catalogo.exists():
        fuentes = json.loads(catalogo.read_text(encoding='utf-8'))
        ids = [f.get('id') for f in fuentes.get('fuentes',[])]
        if len(ids) != 50 or len(set(ids)) != len(ids):
            raise ValueError('Catálogo de fuentes incompleto o con IDs duplicados')
        (OUT/'data'/'fuentes.json').write_text(
            json.dumps(fuentes,ensure_ascii=False,indent=2),encoding='utf8')
    for race in races:
        folder=OUT/'carreras'/race['slug'];folder.mkdir(parents=True)
        (folder/'index.html').write_text(detail_page(race),encoding='utf8')
    for slug,(title,body) in legal_pages().items():
        folder=OUT/slug;folder.mkdir(parents=True)
        (folder/'index.html').write_text(legal_page(title,body,noindex=(not CONTACT and slug in ('contacto','privacidad','aviso-legal'))),encoding='utf8')
    (OUT/'sitemap.xml').write_text(sitemap(races),encoding='utf8')
    if not PUBLIC_LAUNCH:
        # Protege frente a indexación prematura durante la preparación, incluso en las páginas generadas.
        for page in OUT.rglob('*.html'):
            html_text=page.read_text(encoding='utf8')
            html_text=html_text.replace('<head>', '<head><meta name="robots" content="noindex,nofollow">',1)
            page.write_text(html_text,encoding='utf8')
    if not CONTACT: print('ATENCIÓN: falta configurar el correo de contacto en config/site.json')
    if not LEGAL_NAME: print('ATENCIÓN: comprobar obligaciones legales e identidad del titular antes de publicar')
    print(f'Sitio generado: {len(races)} carreras. Destino: {OUT}')

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('ERROR generando sitio:',exc,file=sys.stderr)
        sys.exit(1)
