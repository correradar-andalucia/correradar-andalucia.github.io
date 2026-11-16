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
        path=ROOT/"data"/"distancias_cotejadas_2026-11-16.json"
        catalog=json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"carreras":[]}
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
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="strict-origin-when-cross-origin"><meta name="theme-color" content="#0b1112"><meta name="description" content="{esc(title)} de CorreRadar Andalucía"><link rel="canonical" href="{BASE}/{ {'Aviso legal':'aviso-legal','Privacidad':'privacidad','Cookies':'cookies','Contacto':'contacto'}[title] }/"><link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/styles.css">{('<meta name="robots" content="noindex">' if noindex else '')}<title>{esc(title)} | CorreRadar Andalucía</title></head><body><div class="topline"></div><header class="header wrap"><a class="brand" href="/"><span class="brand-mark">↗</span><span class="brand-type">CORRERADAR <strong>ANDALUCÍA<span class="brand-dot">.</span></strong></span></a><a class="header-cta" href="/">Calendario ↗</a></header><main class="legal-main wrap"><div class="section-kicker">/ INFORMACIÓN DEL PROYECTO</div><h1>{esc(title)}<span class="period">.</span></h1><div class="legal-copy">{body}</div></main>{legal_footer()}</body></html>'''

def legal_pages():
    email_link=(f'<a href="mailto:{esc(CONTACT)}">{esc(CONTACT)}</a>' if CONTACT else '<strong>[CORREO DE CONTACTO PENDIENTE DE CONFIGURAR]</strong>')
    identity=(f'<strong>{esc(LEGAL_NAME)}</strong>' if LEGAL_NAME else '<strong>[IDENTIDAD DEL TITULAR PENDIENTE DE REVISIÓN]</strong>')
    address=(esc(LEGAL_ADDRESS) if LEGAL_ADDRESS else '[DOMICILIO A FACILITAR SI RESULTA LEGALMENTE EXIGIBLE]')
    status='<p class="notice"><strong>Pendiente antes del lanzamiento:</strong> completar los datos de contacto e identidad cuando correspondan y revisar estos textos según el funcionamiento real del sitio. No constituyen asesoramiento jurídico.</p>' if not (CONTACT and LEGAL_NAME) else ''
    legal=f'''{status}<h2>Proyecto y titularidad</h2><p>CorreRadar Andalucía es un calendario informativo independiente de pruebas deportivas. No es una web oficial de la administración pública, ni organiza ni gestiona inscripciones.</p><p>Responsable o titular: {identity}<br>Contacto: {email_link}<br>Dirección a comunicar cuando proceda: {address}</p><h2>Alcance de la información</h2><p>La información sobre fechas, recorridos, desniveles, precios y disponibilidad puede cambiar. Debes confirmar todos los detalles con el organizador antes de viajar o inscribirte.</p><h2>Enlaces externos y derechos</h2><p>Los enlaces de inscripción y tracks conducen a páginas de terceros con sus propias condiciones y políticas. Los nombres de carreras y marcas corresponden a sus titulares. Si detectas errores o contenido que deba revisarse, utiliza el canal de contacto.</p><h2>Publicidad futura</h2><p>En esta fase no hay anuncios ni patrocinios integrados en el código. Si se introducen, se identificarán de forma clara y se actualizarán las condiciones legales y de privacidad antes de su activación.</p>'''
    privacy=f'''{status}<h2>Responsable y contacto</h2><p>Responsable: {identity}. Para consultas relacionadas con datos personales: {email_link}.</p><h2>Datos tratados y finalidades</h2><p>Esta versión no ofrece cuentas de usuario, formularios ni suscripciones y no incorpora herramientas propias de publicidad o analítica. Si nos escribes por correo electrónico, trataremos la dirección, el contenido y los datos que decidas compartir para responder y gestionar tu consulta. La base jurídica será, según el caso, el interés legítimo en atender solicitudes o las medidas precontractuales solicitadas por la persona interesada.</p><h2>Alojamiento y servicios externos</h2><p>El sitio se aloja en GitHub Pages. El proveedor de alojamiento puede tratar datos técnicos de conexión, como direcciones IP y registros de acceso, según sus propias políticas. Los correos que envíes se procesarán también por el servicio de correo que se configure. Es necesario comprobar sus condiciones y las transferencias internacionales aplicables antes de publicar.</p><h2>Conservación</h2><p>Las consultas recibidas se conservarán únicamente el tiempo necesario para atenderlas y, si corresponde, durante los plazos legalmente exigibles. Antes de activar el correo debe establecerse un procedimiento concreto de eliminación y revisión periódica.</p><h2>Derechos</h2><p>Puedes solicitar acceso, rectificación, supresión, oposición, limitación y, cuando proceda, portabilidad de tus datos mediante {email_link}. También puedes presentar una reclamación ante la <a href="https://www.aepd.es/" rel="noopener noreferrer">Agencia Española de Protección de Datos</a>.</p><h2>Cambios futuros</h2><p>Si se añaden estadísticas, anuncios, newsletters, formularios u otros servicios, esta política se revisará antes de activarlos.</p>'''
    cookies='''<h2>Situación de esta versión</h2><p>El código de CorreRadar Andalucía no instala cookies propias, no utiliza almacenamiento local para seguimiento y no incorpora anuncios, analítica, píxeles comerciales ni reproductores externos. Por ello no se presenta un banner de consentimiento en esta versión.</p><h2>Servicios de infraestructura</h2><p>La entrega de la web la realiza GitHub Pages. Antes de publicar es necesario comprobar si el alojamiento u otros servicios incorporados efectivamente usan cookies o tecnologías similares, y actualizar esta información cuando corresponda.</p><h2>Enlaces externos</h2><p>Al pulsar en los enlaces de inscripciones o tracks saldrás de este sitio. Esas páginas pueden utilizar sus propias cookies.</p><h2>Si incorporamos publicidad o analítica</h2><p>Antes de activar cookies no necesarias, se informará de sus fines y se solicitará consentimiento con opciones equivalentes de aceptar y rechazar, además de un mecanismo para retirarlo.</p>'''
    contact=f'''{status}<h2>Escríbenos</h2><p>Para proponer carreras, avisar de errores, pedir correcciones o consultar una colaboración, escribe a: {email_link}.</p><p>Al escribirnos, facilitas los datos que incluyas voluntariamente en tu correo. Consulta la <a href="/privacidad/">política de privacidad</a> para saber cómo se utilizarán.</p><h2>Organizadores</h2><p>Incluye nombre de la carrera, fecha, localidad y enlace oficial para que podamos verificar la información. No envíes datos personales de corredores ni material protegido sin autorización.</p>'''
    return {'aviso-legal':('Aviso legal',legal),'privacidad':('Privacidad',privacy),'cookies':('Cookies',cookies),'contacto':('Contacto',contact)}

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
    fecha_texto={'editorial':'Fecha revisada por CorreRadar',
                 'fuente':'Fecha publicada en la fuente consultada',
                 'catalogo':'Fecha cotejada anteriormente con la fuente'}.get(fecha_origen,'Fecha de referencia')
    distancia_origen={'editorial':'revisada por CorreRadar',
                      'fuente':'publicada en la fuente',
                      'catalogo':'cotejada en el catálogo'}.get(r.get('distancia_origen'),'')
    entries=[('Fecha',fmt),('Procedencia de fecha',fecha_texto),
             ('Localidad',city),('Modalidad',mode)]
    if r.get('distancia') and distancia_origen:
        entries.append(('Distancia',r['distancia']+' · '+distancia_origen))
    if r.get("distancia_cotejada"):
        entries.append(("Distancia cotejada el",r["distancia_cotejada"]))
    if is_confirmed:
        entries += [('Desnivel',r['desnivel']),
                    ('Precio',r['precio']),('Bolsa del corredor',r['bolsa'])]
    entries += [('Fecha de la consulta o cotejo',r.get('consultado','') if not is_confirmed else ''),
                ('Última revisión editorial',r.get('verificado','') if is_confirmed else '')]
    lines='\n'.join(f'<div class="detail-line"><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>' for k,v in entries if v)
    buttons=''
    provisional=not is_confirmed
    if r['enlace']:buttons+=f'<a href="{esc(r["enlace"])}" rel="noopener noreferrer" target="_blank">{("Comprobar en la fuente ↗" if provisional else "Ver enlace de la carrera ↗")}</a>'
    if r.get('fuente') and r['fuente']!=r.get('enlace'):buttons+=f'<a class="secondary" href="{esc(r["fuente"])}" rel="noopener noreferrer" target="_blank">Fuente de verificación ↗</a>'
    if r.get("distancia") and url_clean(r.get("distancia_fuente","")) and r.get("distancia_fuente") != r.get("enlace"):
        buttons+=f'<a class="secondary" href="{esc(r["distancia_fuente"])}" rel="noopener noreferrer" target="_blank">Ver distancia en la fuente ↗</a>'
    if is_confirmed and r['track']:buttons+=f'<a class="secondary" href="{esc(r["track"])}" rel="noopener noreferrer" target="_blank">Ver track ↗</a>'
    if not buttons:buttons='<p>Enlaces oficiales pendientes de verificación.</p>'
    ld={'@context':'https://schema.org','@type':'SportsEvent','name':r['nombre'],'startDate':r['fecha'],
        'eventAttendanceMode':'https://schema.org/OfflineEventAttendanceMode','url':BASE+path,
        'location':{'@type':'Place','name':r['localidad'],'address':{'@type':'PostalAddress','addressLocality':r['localidad'],'addressRegion':r['provincia'],'addressCountry':'ES'}}}
    if r['enlace']:ld['sameAs']=r['enlace']
    structured=json.dumps(ld,ensure_ascii=False).replace('<','\\u003c')
    structured_tag = (f'<script type="application/ld+json">{structured}</script>' if is_confirmed else '')
    provisional_robots = '' if is_confirmed else '<meta name="robots" content="noindex,follow">'
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0b1112">{provisional_robots}<meta name="description" content="{esc(desc)}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{BASE+path}"><link rel="canonical" href="{BASE+path}"><link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/styles.css">{structured_tag}<title>{esc(title)}</title></head><body><div class="topline"></div><header class="header wrap"><a class="brand" href="/"><span class="brand-mark" aria-hidden="true">↗</span><span class="brand-type">CORRERADAR <strong>ANDALUCÍA<span class="brand-dot">.</span></strong></span></a><a class="header-cta" href="/">Calendario ↗</a></header><main class="detail-main wrap"><a class="detail-back" href="/">← VOLVER AL CALENDARIO</a><div class="section-kicker" style="margin-top:48px">/ FICHA DE CARRERA</div><h1>{esc(r['nombre'])}<span class="period">.</span></h1><p class="detail-lead">{esc(fmt)} · {esc(city)}</p><div class="detail-grid"><dl class="detail-list">{lines}</dl><aside class="detail-side"><h2>PREPARA TU SALIDA.</h2>{buttons}<p class="disclaimer">Los datos pueden variar. Confirma siempre los detalles en la web del organizador.</p></aside></div></main>{legal_footer()}</body></html>'''

def sitemap(races):
    ET.register_namespace('', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    root=ET.Element('{http://www.sitemaps.org/schemas/sitemap/0.9}urlset')
    for path in ['/','/aviso-legal/','/privacidad/','/cookies/','/contacto/']+[f'/carreras/{r["slug"]}/' for r in races if r.get('confirmada')]:
        u=ET.SubElement(root,'{http://www.sitemaps.org/schemas/sitemap/0.9}url')
        ET.SubElement(u,'{http://www.sitemaps.org/schemas/sitemap/0.9}loc').text=BASE+path
    return ET.tostring(root,encoding='unicode',xml_declaration=True)

def main():
    from multifuente import seed_races, backup_runnink
    from deduplicacion import combine, verify_unique
    from captacion import collect
    candidatas_en_vivo, informe_captacion = collect()
    races, auditoria = combine(transform(load_csv()), seed_races()+backup_runnink()+candidatas_en_vivo,
                               slugify, km_parse, with_audit=True)
    auditoria["distancias_cotejadas"]=add_curated_distances(races)
    verify_unique(races)
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
