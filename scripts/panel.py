"""Panel estático de mantenimiento. Solo datos ya publicados y recuentos agregados.

La página es pública como GitHub Pages: no contiene secretos, datos personales,
mensajes de excepciones ni enlaces privados. No realiza peticiones externas.
"""
from collections import Counter
from datetime import datetime
from html import escape
from urllib.parse import quote
from zoneinfo import ZoneInfo
from deduplicacion import same_event, conflicting_date
from persistencia import distance_backlog
from control_calidad import valid_source
from captacion import SOURCES

REPO="https://github.com/correradar-andalucia/correradar-andalucia.github.io"
NAMES={"faa":"Federación Andaluza de Atletismo","fadmes":"FADMES","dorsalchip":"Dorsalchip",
       "runnink":"Runnink","gesconchip":"Gesconchip","gcc":"GCC Sport Events",
       "cruzandolameta":"Cruzando la Meta","dipgra":"Diputación de Granada",
       "diphuelva":"Diputación de Huelva","circuito_cordoba":"Circuito Cordobés"}
REG={"abierta":"Abiertas","cerrada":"Cerradas","agotada":"Agotadas",
     "proximamente":"Próxima apertura","desconocida":"Sin confirmar"}

def e(value):
    return escape(str(value),quote=True)

def count(value):
    return value if isinstance(value,int) and not isinstance(value,bool) and value>=0 else 0

def link(url,label):
    return f'<a href="{e(url)}" rel="noopener noreferrer">{e(label)}</a>' if valid_source(url) else e(label)

def comparison(races,previous):
    """Cambios frente al último JSON publicado, no equivalen a avisos históricos."""
    if not previous or any(not all(r.get(k) for k in ("fecha","nombre","localidad","provincia"))
                           for r in previous):
        return None
    additions=[]
    for r in races:
        if not any(same_event(r,p) or conflicting_date(r,p) for p in previous):
            additions.append(r)
    absent=sum(not any(same_event(p,r) or conflicting_date(p,r) for r in races) for p in previous)
    return {"nuevas":additions,"ausentes":absent,"anterior":len(previous)}

def panel_page(races,capture,audit,quality,previous=None,now=None,run_id=None):
    now=now or datetime.now(ZoneInfo("Europe/Madrid"))
    today=now.date()
    n=len(races)
    distance=sum(bool(r.get("distancia")) for r in races)
    hour=sum(bool(r.get("hora") and r.get("hora_origen")) for r in races)
    statuses=Counter(r.get("inscripcion_estado","desconocida") for r in races)
    known=sum(statuses[k] for k in REG if k!="desconocida")
    permitted=set(capture.get("nombres_fuentes_habilitadas",[]))
    report=capture.get("fuentes",{})
    offline=capture.get("modo")=="Prueba local sin conexión"
    read=sum(report.get(k,{}).get("estado")=="leida" for k in permitted)
    backlog=distance_backlog(races,today)
    recovery=count(audit.get("respaldo_carreras",{}).get("recuperadas"))
    range_only=backlog["orientativas"]
    def metric(label,value,sub=""):
        return f'<article class="metric"><span>{e(label)}</span><strong>{e(value)}</strong><small>{e(sub)}</small></article>'
    def progress(label,num):
        pct=round(100*num/n,1) if n else 0
        return f'<div class="progress"><span>{e(label)}</span><b>{num}/{n} · {pct:g}%</b><progress max="{max(1,n)}" value="{num}">{pct:g}%</progress></div>'
    source_rows=[]
    for key in SOURCES:
        item=report.get(key,{})
        status=item.get("estado")
        if offline:
            label,cls="Sin consulta (prueba local)","neutral"
        elif key not in permitted:
            label,cls="Pausada / no habilitada","neutral"
        elif item.get("lectura_anomala"):
            label,cls="Lectura anómala / revisar","warn"
        elif status=="leida":
            label,cls="Leída","ok"
        elif item.get("fallo_temporal") is True:
            label,cls="Fallo temporal","warn"
        else:
            label,cls="No disponible / revisar","warn"
        details=report.get(key+"_detalle",{})
        # No incluir motivos de excepción ni texto arbitrario del informe.
        errors=max(count(details.get("incidencias")),count(item.get("incidencias_detalle")))
        candidates=str(count(item.get("candidatas"))) if status=="leida" else "—"
        detail=f'{errors} incidencias de detalle' if errors else "—"
        if item.get("lectura_anomala"):
            detail=f'{count(item.get("ausentes_frente_anterior"))} carreras ausentes antes del respaldo · {detail}'
        source_rows.append(f'<tr><th scope="row">{e(NAMES[key])}</th><td><span class="status {cls}">{e(label)}</span></td><td>{candidates}</td><td>{e(detail)}</td></tr>')
    gt="Feed autorizado: "+("leído" if report.get("globaltempo",{}).get("estado")=="leida" else "no disponible") if capture.get("globaltempo_autorizado") else "Google Alerts y revisión manual; sin lectura directa"
    findings=[]
    if not offline and read<len(permitted):
        findings.append(f'{len(permitted)-read} fuentes habilitadas no leídas en esta generación.')
    if recovery:
        findings.append(f'{recovery} carreras conservadas temporalmente; verificar de nuevo la fuente.')
    if quality.get("avisos"):
        findings.append(f'{len(quality["avisos"])} advertencias en el control de calidad.')
    if offline:
        findings.append("Datos de una prueba local sin conexión; no representan la salud de las fuentes.")
    changes=comparison(races,previous)
    if changes is None:
        change_html='<p>Sin una publicación anterior comparable. No se consideran nuevas todas las carreras.</p>'
    else:
        additions=changes["nuevas"]
        change_html=f'<p><strong>{len(additions)}</strong> incorporaciones frente al calendario previo ({changes["anterior"]} carreras). <strong>{changes["ausentes"]}</strong> fichas anteriores que ya no figuran: pueden haber transcurrido, cambiado o dejado de aparecer; no implica cancelación.</p>'
        if additions:
            change_html+='<ul>'+''.join(f'<li>{e(r["fecha"])} · <a href="/carreras/{quote(r["slug"],safe="")}/">{e(r["nombre"])}</a> · {e(r["localidad"])}</li>' for r in additions)+'</ul>'
        change_html+='<p class="note">Comparación de publicaciones, no histórico de avisos ni confirmación de envío de correo.</p>'
    pending_rows=[]
    for r in backlog["pendientes"]:
        missing=["Distancia orientativa" if r["estado"]=="orientativa" else "Distancia pendiente"]
        pending_rows.append(f'<tr data-priority="{e(r["prioridad"])}"><td>{e(r["fecha"])}</td><th scope="row"><a href="/carreras/{quote(r["slug"],safe="")}/">{e(r["nombre"])}</a><small>{e(r["localidad"])} · {e(r["provincia"])}</small></th><td>{e(missing[0])}</td><td>{e(r["prioridad"].capitalize())}</td><td>{link(r.get("fuente"),"Consultar fuente")}</td></tr>')
    by_province=Counter(r["provincia"] for r in races)
    province_rows=''.join(f'<tr><th scope="row">{e(p)}</th><td>{by_province[p]}</td><td>{sum(bool(r.get("distancia")) for r in races if r["provincia"]==p)}</td><td>{sum(bool(r.get("hora") and r.get("hora_origen")) for r in races if r["provincia"]==p)}</td></tr>' for p in ("Almería","Cádiz","Córdoba","Granada","Huelva","Jaén","Málaga","Sevilla"))
    run_link=REPO+"/actions/runs/"+str(run_id) if str(run_id or "").isdigit() else REPO+"/actions"
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><meta name="referrer" content="no-referrer"><title>Panel de mantenimiento · CorreRadar Andalucía</title><link rel="stylesheet" href="/assets/panel.css"></head><body><main>
<header><a class="brand" href="/">CORRERADAR ANDALUCÍA ↗</a><span> / MANTENIMIENTO</span><h1>Estado del calendario</h1><p>Generación: {e(now.strftime("%d/%m/%Y · %H:%M"))} (hora peninsular). Datos de la última publicación, no monitorización en directo.</p><nav><a href="/">Ver calendario</a><a href="{e(run_link)}">Ejecución de GitHub</a><a href="{REPO}/actions">Historial de ejecuciones</a><a href="{REPO}/issues">Avisos e incidencias</a></nav><p class="note">Panel público no indexado; no requiere iniciar sesión y no contiene datos privados. Si falla una publicación, seguirá visible el último panel correcto; consulta GitHub para ver el fallo.</p></header>
<section aria-label="Indicadores" class="metrics">{metric("Carreras",n)}{metric("Con distancia",distance,f"{n-distance} sin distancia numérica")}{metric("Con horario",hour)}{metric("Inscripción conocida",known,f"{n-known} sin confirmar")}{metric("Fuentes leídas",f"{read}/{len(permitted)}" if not offline else "Sin red")}{metric("Respaldo temporal",recovery,"Carreras conservadas")}</section>
<section class="panel"><h2>Prioridades y calidad</h2>{progress("Distancias",distance)}{progress("Horarios",hour)}{progress("Estado de inscripción en la generación",known)}<p>{range_only} carreras con distancias únicamente orientativas; no se cuentan como kilómetros exactos.</p><p>Control de calidad: {"correcto" if quality.get("apto_para_desplegar") else "revisar"} · {count(audit.get("duplicados_fusionados"))} candidatas fusionadas · {count(audit.get("fechas_en_conflicto"))} conflictos de fecha · {count(audit.get("distancias_en_conflicto"))} conflictos de distancia.</p><p>{e(" ".join(findings) or "Sin incidencias generales registradas en esta generación.")}</p></section>
<section class="panel"><h2>Salud de las fuentes</h2><p>«Leída» indica acceso al listado, no que todas sus fichas estén completas. Candidatas antes de deduplicar.</p><div class="table-wrap"><table><thead><tr><th>Fuente</th><th>Estado</th><th>Candidatas</th><th>Detalle</th></tr></thead><tbody>{"".join(source_rows)}</tbody></table></div><p>Global Tempo: {e(gt)}.</p></section>
<div class="cols"><section class="panel"><h2>Inscripciones</h2><p>Estados según la consulta de esta generación; pueden caducar.</p><dl>{"".join(f'<div><dt>{e(v)}</dt><dd>{statuses[k]}</dd></div>' for k,v in REG.items())}</dl></section><section class="panel"><h2>Cambios de calendario</h2>{change_html}</section></div>
<section class="panel"><h2>Cobertura por provincia</h2><div class="table-wrap"><table><thead><tr><th>Provincia</th><th>Carreras</th><th>Distancia</th><th>Horario</th></tr></thead><tbody>{province_rows}</tbody></table></div></section>
<section class="panel"><h2>Cola de distancias: {backlog["total"]} pendientes</h2><p>Ordenadas por fecha. Prioridad alta hasta 30 días; media hasta 90; baja después. Comprueba la edición antes de añadir datos.</p><p><a href="/data/distancias_pendientes.json">Ver inventario JSON ↗</a></p><div class="table-wrap"><table><thead><tr><th>Fecha</th><th>Carrera y municipio</th><th>Estado</th><th>Prioridad</th><th>Fuente</th></tr></thead><tbody>{"".join(pending_rows) or '<tr><td colspan="5">No hay pendientes.</td></tr>'}</tbody></table></div></section>
<footer><a href="/">Volver al calendario</a> · <a href="{REPO}/actions">GitHub Actions</a></footer></main></body></html>'''
