'use strict';

/* Calendario con procedencia explícita de fechas y distancias: no ocultar hechos publicados. */
const $ = (id) => document.getElementById(id);
const months = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
const sources = {
  globaltempo:'Global Tempo', dorsalchip:'Dorsalchip', fadmes:'FADMES',
  faa:'FAA', cruzandolameta:'Cruzando la Meta', gcc:'GCC Sport Events',
  dipgra:'Diputación de Granada', diphuelva:'Diputación de Huelva',
  circuito_cordoba:'Circuito Cordobés',
  runnink:'Runnink', gesconchip:'Gesconchip', rockthesport:'RockTheSport',
  oficial:'Fuentes cotejadas'
};
const modeLabels = {
  RUNNING:'ASFALTO', TRAIL:'TRAIL', CROSS:'CROSS', ULTRA:'ULTRA',
  RESISTENCIA:'RESISTENCIA', OCR:'OBSTÁCULOS', HIBRIDA:'HÍBRIDAS',
  ESPECIAL:'ESPECIAL', MIXTA:'MIXTA'
};
const PAGE_SIZE = 20;
const normalize = (s) => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const raceOrigins = (r) => [...new Set([...(Array.isArray(r.fuentes_origen) ? r.fuentes_origen : []),r.origen].filter(Boolean))];
const sourceName = (r) => {
  if (r.fuente_nombre) return r.fuente_nombre;
  const names = raceOrigins(r).map(x => sources[x] || x);
  return names.slice(0,2).join(' · ') + (names.length > 2 ? ' +' + (names.length-2) : '');
};
const fmt = (s) => { const [y,m,d] = String(s).split('-').map(Number); return new Date(y,m-1,d); };
const safeLink = (url) => {
  try { const u = new URL(url); return u.protocol === 'https:' ? u.href : null; }
  catch { return null; }
};
const confirmed = (r) => r.confirmada === true;
const readableDate = (iso) => {
  const found = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ''));
  return found ? found[3]+'/'+found[2]+'/'+found[1] : String(iso || '');
};
// Cada distancia anunciada cuenta en su propio rango; aceptar también «25 k / 15 k».
const distanceNumbers = (raw) => [...String(raw || '').matchAll(/(\d{1,5}(?:[.,]\d{1,3})?)\s*(kil[oó]metros?|kms?|k|metros?|m)\b/gi)]
  .map(m => {
    const unit = m[2].toLowerCase();
    const meters = unit === 'm' || unit.startsWith('metro');
    // En fuentes españolas «1.500 m» equivale a 1500 m, no a 1,5 m.
    const value = meters && /^\d{1,3}[.,]\d{3}$/.test(m[1])
      ? Number(m[1].replace(/[.,]/g, ''))
      : Number(m[1].replace(',', '.'));
    return meters ? value / 1000 : value;
  })
  .filter(n => Number.isFinite(n) && n > 0);
function distanceMatches(r, filter) {
  if (!filter) return true;
  const nums = distanceNumbers(r.distancia);
  if (filter === 'unknown') return !nums.length;
  return nums.some(n => filter === 'short' && n <= 10
    || filter === 'medium' && n > 10 && n <= 21.1
    || filter === 'long' && n > 21.1 && n <= 42.2
    || filter === 'ultra' && n > 42.2);
}
let races = [];
const modalityGroup = (r) => {
  if (r.modalidad_conflicto) return 'OTRAS';
  if (r.modalidad === 'TRAIL' || r.modalidad === 'ULTRA') return 'TRAIL';
  if (r.modalidad === 'OCR' || r.modalidad === 'HIBRIDA') return 'OBSTACULOS';
  if (r.modalidad === 'RUNNING' || r.modalidad === 'CROSS') return r.modalidad;
  return 'OTRAS';
};
let currentMode = 'TODAS';
let visibleLimit = PAGE_SIZE;

function el(name, cls, text) {
  const n = document.createElement(name);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
}
function state(title, detail, symbol='↗') {
  const root = el('div','state');
  root.append(el('span','state-icon',symbol),el('h3','',title),el('p','',detail));
  return root;
}
function raceCard(r) {
  const card = el('article','race-card');
  // El año es fundamental cuando las pruebas abarcan distintas temporadas.
  const date = el('time','race-date');
  const d = fmt(r.fecha);
  date.dateTime = r.fecha;
  date.setAttribute('aria-label',d.toLocaleDateString('es-ES',{
    day:'numeric',month:'long',year:'numeric',weekday:'long'
  }));
  date.append(el('strong','',String(d.getDate()).padStart(2,'0')),
              el('span','',months[d.getMonth()].slice(0,3).toUpperCase()),
              el('span','race-year',String(d.getFullYear())));

  const info = el('div','race-info');
  const head = el('div','race-head');
  const title = el('h3','race-title');
  const titleLink = el('a','',r.nombre);
  titleLink.href = '/carreras/' + encodeURIComponent(r.slug) + '/';
  title.append(titleLink);
  head.append(title);
  if (r.modalidad_conflicto) {
    head.append(el('span','tag tag-review','MODALIDAD POR REVISAR'));
  } else {
    head.append(el('span','tag '+String(r.modalidad).toLowerCase(),
                   modeLabels[r.modalidad] || r.modalidad));
  }
  // La fecha ya destaca en su propio bloque: no repetirla con una etiqueta técnica.
  if (sourceName(r)) head.append(el('span','tag source-tag',sourceName(r)));
  info.append(head,el('p','race-location','⌖  '+[r.localidad,r.provincia].filter(Boolean).join(' · ')));

  const facts = el('div','race-facts');
  if (r.distancia && r.distancia_origen) facts.append(el('span','','↗  '+r.distancia));
  // Sin kilómetros comprobados, no llenar cada tarjeta con avisos repetitivos.
  if (r.hora && r.hora_origen) facts.append(el('span','','◷  '+r.hora+' h · según fuente'));
  if (confirmed(r)) {
    if (r.desnivel) facts.append(el('span','','⌁  '+r.desnivel));
    if (r.precio) facts.append(el('span','','◈  '+r.precio));
  }
  info.append(facts);
  if (!confirmed(r) && r.consultado) {
    info.append(el('p','source-meta',
      (r.fecha_origen === 'catalogo' ? 'Consulta anterior: ' : 'Fuente consultada: ')+readableDate(r.consultado)));
  }

  const actions = el('div','race-actions');
  // Priorizar el enlace de la ficha/inscripción, no el calendario genérico.
  // La fuente queda como respaldo cuando no existe enlace individual.
  const sourceUrl = safeLink(r.enlace) || safeLink(r.fuente);
  if (sourceUrl) {
    const link = el('a','register',confirmed(r) ? 'Ver enlace de la carrera ↗' : 'Consultar fuente ↗');
    link.href = sourceUrl;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    actions.append(link);
  }
  const detail = el('a','details','Ver ficha ↗');
  detail.href='/carreras/'+encodeURIComponent(r.slug)+'/';
  actions.append(detail);
  card.append(date,info,actions);
  return card;
}
function matches(r, search, province, month, distance, today) {
  if (!r.fecha || fmt(r.fecha) < today) return false;
  if (search && !normalize([r.nombre,r.localidad,r.provincia,sourceName(r)].join(' ')).includes(search)) return false;
  if (province && normalize(r.provincia) !== province) return false;
  if (month && r.fecha.slice(0,7) !== month) return false;
  if (!distanceMatches(r, distance)) return false;
  if (currentMode !== 'TODAS' && modalityGroup(r) !== currentMode) return false;
  return true;
}
function render() {
  const search = normalize($('search').value.trim());
  const province = normalize($('province').value);
  const month = $('month').value;
  const distance = $('distance').value;
  const today = new Date();
  today.setHours(0,0,0,0);
  const filtered = races.filter(r => matches(r,search,province,month,distance,today));
  $('result-count').textContent = String(filtered.length);
  const root = $('cards');
  root.replaceChildren();
  if (!filtered.length) {
    root.append(state(
      races.length ? 'No hay carreras con estos filtros' : 'El calendario está preparado',
      races.length ? 'Prueba otra provincia, tipo de carrera o distancia. Las carreras sin kilómetros aparecen al elegir «Todas».'
                   : 'Todavía no hay carreras disponibles en el calendario.'
    ));
  } else {
    const fragment = document.createDocumentFragment();
    for (const r of filtered.slice(0,visibleLimit)) fragment.append(raceCard(r));
    root.append(fragment);
  }
  const more = $('more');
  more.hidden = filtered.length <= visibleLimit;
  if (!more.hidden) more.textContent = 'Mostrar más carreras ('+Math.min(PAGE_SIZE,filtered.length-visibleLimit)+') ↓';
  $('shown-count').textContent = filtered.length
    ? 'Mostrando '+Math.min(filtered.length,visibleLimit)+' de '+filtered.length+' carreras'
    : '';
}
function filter() {
  visibleLimit = PAGE_SIZE;
  render();
}
async function init() {
  $('year').textContent = new Date().getFullYear();
  for (const id of ['search','province','month','distance']) {
    $(id).addEventListener(id==='search' ? 'input' : 'change',filter);
  }
  document.querySelectorAll('[data-mode]').forEach(b => b.addEventListener('click',()=>{
    currentMode = b.dataset.mode;
    document.querySelectorAll('[data-mode]').forEach(x=>{
      const active = x===b;
      x.classList.toggle('active',active);
      x.setAttribute('aria-pressed',String(active));
    });
    filter();
  }));
  $('clear').addEventListener('click',()=>{
    for (const id of ['search','province','month','distance']) $(id).value='';
    document.querySelector('[data-mode="TODAS"]').click();
  });
  $('more').addEventListener('click',()=>{visibleLimit+=PAGE_SIZE;render();});
  try {
    const res=await fetch('/data/carreras.json',{cache:'no-cache'});
    if (!res.ok) throw new Error('HTTP '+res.status);
    const result=await res.json();
    races=Array.isArray(result.carreras) ? result.carreras : [];
    races.sort((a,b)=>a.fecha.localeCompare(b.fecha));
    const today=new Date();
    today.setHours(0,0,0,0);
    const active=races.filter(r=>fmt(r.fecha)>=today);
    const validMonths=[...new Set(active.map(r=>r.fecha.slice(0,7)))].sort();
    for (const m of validMonths) {
      const [year,num]=m.split('-');
      const opt=el('option','',months[Number(num)-1]+' '+year);
      opt.value=m;
      $('month').append(opt);
    }
    $('updated').textContent=result.actualizado?'Generado el '+result.actualizado:'';
    const withDistance=active.filter(r=>distanceNumbers(r.distancia).length).length;
    const withTime=active.filter(r=>r.hora && r.hora_origen).length;
    $('coverage').textContent=withDistance+' con distancia · '+withTime+' con horario';
    filter();
  } catch (error) {
    console.error(error);
    $('result-count').textContent='0';
    $('more').hidden=true;
    $('cards').replaceChildren(state('No se pudo cargar el calendario',
      'Comprueba la publicación de los archivos y vuelve a intentarlo.','!'));
  }
}
// Este listado NO forma parte de las carreras fechadas ni altera sus filtros.
async function loadReviewedLinks() {
  try {
    const res=await fetch('/data/globaltempo_enlaces.json',{cache:'no-cache'});
    if (!res.ok) return;
    const data=await res.json();
    const links=Array.isArray(data.enlaces) ? data.enlaces : [];
    const panel=$('inscripciones-revisadas');
    const container=$('reviewed-links');
    const fragment=document.createDocumentFragment();
    const used=new Set();
    for (const item of links) {
      const url=safeLink(item.url);
      const name=String(item.nombre || '').trim();
      if (!url || !/^https:\/\/(?:www\.|gateway\.)?global-tempo\.com\/carreras\.php\?id=[1-9][0-9]{0,7}$/.test(url) ||
          !name || name.length>160 || used.has(url)) continue;
      used.add(url);
      const article=el('article','reviewed-link');
      const title=el('h3','',name);
      const a=el('a','', 'Ver inscripción ↗');
      a.href=url;
      a.target='_blank';
      a.rel='noopener noreferrer';
      article.append(title,a);
      fragment.append(article);
    }
    if (fragment.childNodes.length) {
      container.replaceChildren(fragment);
      panel.hidden=false;
    }
  } catch (error) {
    console.warn('No se pudieron cargar las inscripciones revisadas',error);
  }
}
init();
loadReviewedLinks();
