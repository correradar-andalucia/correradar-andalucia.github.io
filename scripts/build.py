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
        race["km"]=km_parse(item["distancia"])
        applied+=1
    return {"aplicadas":applied,"conflictos_no_sobrescritos":conflicts}


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
              else '<strong>[TITULAR RESPONSABLE: IDENTIDAD PENDIENTE DE COMPLETAR]</strong>')
    address=(esc(LEGAL_ADDRESS) if LEGAL_ADDRESS
             else '[DOMICILIO: PENDIENTE DE DETERMINAR Y PUBLICAR CUANDO SEA EXIGIBLE]')
    unresolved=(not LEGAL_NAME or not CONFIG.get("legal_review_complete",False))
    status=(
        '<p class="notice"><strong>Información legal en revisión antes del lanzamiento.</strong> '
        'Es necesario identificar al titular, resolver los datos exigibles conforme a la LSSI, '
        'verificar contratos y transferencias de proveedores y obtener una revisión jurídica '
        'de este texto y de los derechos de reutilización de las fuentes. '
        'No se afirma que la web esté certificada ni que cuente con autorización de todas las fuentes.</p>'
        if unresolved else ''
    )
    updated=dt.date.today().strftime("%d/%m/%Y")

    legal=f'''{status}
<h2>Identificación del proyecto</h2>
<p>CorreRadar Andalucía es un calendario informativo independiente de carreras populares, montaña y obstáculos en Andalucía. No es el organizador de las pruebas, no presta servicios de cronometraje y no gestiona inscripciones ni pagos.</p>
<p>Titular o responsable del sitio: {identity}<br>Correo de contacto: {email_link}<br>Domicilio: {address}</p>
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
<p>Responsable de las comunicaciones dirigidas al proyecto: {identity}. Contacto para asuntos de privacidad: {email_link}. El dato identificativo del titular aún debe completarse.</p>
<h2>Qué información utilizamos y para qué</h2>
<p>La web pública no solicita registro, no dispone de formularios de usuario, no ofrece suscripciones y no tiene funciones propias de seguimiento del visitante. La búsqueda y los filtros del calendario se realizan localmente en tu navegador con archivos estáticos del sitio; no enviamos a CorreRadar tus términos de búsqueda ni preferencias.</p>
<p>Si escribes voluntariamente al correo indicado, podremos tratar el remitente, dirección, asunto, contenido y datos que aportes para gestionar la consulta, comunicar correcciones de carreras o responder a un organizador. Evita enviar números de documento, datos médicos y otra información innecesaria sobre corredores.</p>
<h2>Base jurídica</h2>
<p>La atención de consultas ordinarias puede basarse, según el caso y previa valoración del responsable, en el interés legítimo de gestionar comunicaciones (artículo 6.1.f RGPD), en medidas precontractuales solicitadas (6.1.b) o en el cumplimiento de obligaciones legales aplicables (6.1.c). No se utiliza el consentimiento a cookies de publicidad como base jurídica porque esos servicios no están incorporados.</p>
<h2>Alojamiento y destinatarios</h2>
<p>La página se publica en <a href="https://docs.github.com/es/pages/getting-started-with-github-pages/what-is-github-pages" rel="noopener noreferrer" referrerpolicy="no-referrer" target="_blank">GitHub Pages</a>. GitHub informa de que registra las direcciones IP de los visitantes para proteger el servicio, incluso sin iniciar sesión. El titular de CorreRadar no recibe directamente esas direcciones desde el código de la web ni instala un programa de analítica propio.</p>
<p>Las comunicaciones enviadas al correo de contacto también son tratadas por el proveedor del servicio de correo utilizado por su titular. GitHub y los servicios de comunicación tienen sus propias condiciones y políticas, que deben comprobarse para determinar roles, transferencias internacionales y garantías aplicables antes del lanzamiento.</p>
<p>Las herramientas internas de Google Alerts y GitHub Actions usadas para descubrir carreras procesan datos de fuentes y avisos editoriales; el navegador del visitante no contacta con esos servicios por el hecho de ver el calendario. El hecho de pulsar un enlace externo sí puede dar lugar a un tratamiento independiente por parte del tercero visitado.</p>
<h2>Conservación y acceso</h2>
<p>Los correos de consulta se conservarán durante el tiempo necesario para atenderlos y, si procede, para cumplir obligaciones legales o gestionar reclamaciones. El responsable deberá definir, documentar y aplicar un plazo operativo de revisión y borrado; la mera publicación de esta política no ejecuta automáticamente esas eliminaciones. No se publican los correos recibidos ni se venden datos personales.</p>
<h2>Derechos y reclamaciones</h2>
<p>Puedes solicitar el acceso, rectificación, supresión, oposición, limitación y, cuando proceda, portabilidad de tus datos escribiendo a {email_link}. Si algún tratamiento se basase en tu consentimiento, podrías retirarlo en cualquier momento, sin efecto retroactivo. También tienes derecho a presentar una reclamación ante la <a href="https://www.aepd.es/" rel="noopener noreferrer" referrerpolicy="no-referrer" target="_blank">Agencia Española de Protección de Datos (AEPD)</a>. Para proteger tus datos, podremos solicitar información razonable para verificar la identidad cuando sea necesario.</p>
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
        entries.append(('Distancia',r['distancia']+' · '+distancia_origen))
    if r.get("distancia_cotejada"):
        entries.append(("Distancia cotejada el",r["distancia_cotejada"]))
    if is_confirmed:
        entries += [('Desnivel',r['desnivel']),
                    ('Precio',r['precio']),('Bolsa del corredor',r['bolsa'])]
    consultado=str(r.get('consultado','') or '')
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}',consultado):
        consultado=consultado[8:10]+'/'+consultado[5:7]+'/'+consultado[:4]
    consulta_label=('Consulta anterior de la fuente' if fecha_origen=='catalogo'
                    else 'Fuente consultada')
    entries += [(consulta_label,consultado if not is_confirmed else ''),
                ('Última revisión editorial',r.get('verificado','') if is_confirmed else '')]
    lines='\n'.join(f'<div class="detail-line"><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>' for k,v in entries if v)
    buttons=''
    provisional=not is_confirmed
    if r['enlace']:buttons+=f'<a href="{esc(r["enlace"])}" rel="noopener noreferrer" target="_blank">{("Comprobar en la fuente ↗" if provisional else "Ver enlace de la carrera ↗")}</a>'
    if r.get('fuente') and r['fuente']!=r.get('enlace'):buttons+=f'<a class="secondary" href="{esc(r["fuente"])}" rel="noopener noreferrer" target="_blank">Fuente de verificación ↗</a>'
    if r.get("distancia") and url_clean(r.get("distancia_fuente","")) and r.get("distancia_fuente") != r.get("enlace"):
        buttons+=f'<a class="secondary" href="{esc(r["distancia_fuente"])}" rel="noopener noreferrer" target="_blank">Ver distancia en la fuente ↗</a>'
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
    auditoria["distancias_cotejadas"]=add_curated_distances(races)
    auditoria["fichas_oficiales_cotejadas"]=len(oficiales)
    provincias=["Almería","Cádiz","Córdoba","Granada","Huelva","Jaén","Málaga","Sevilla"]
    cobertura={
        "actualizado":dt.date.today().isoformat(),
        "total":len(races),
        "con_distancia":sum(bool(r.get("distancia")) for r in races),
        "con_hora":sum(bool(r.get("hora")) for r in races),
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
