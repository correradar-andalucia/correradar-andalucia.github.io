'use strict';

/* Calendario con procedencia explícita de fechas y distancias: no ocultar hechos publicados. */
const $ = (id) => document.getElementById(id);
const months = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
const sources = {
  globaltempo:'Global Tempo', dorsalchip:'Dorsalchip', fadmes:'FADMES',
  faa:'FAA', cruzandolameta:'Cruzando la Meta', gcc:'GCC Sport Events',
  dipgra:'Diputación de Granada', diphuelva:'Diputación de Huelva',
  runnink:'Runnink', gesconchip:'Gesconchip', rockthesport:'RockTheSport'
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
  const names = raceOrigins(r).map(x => sources[x] || x);
  return names.slice(0,2).join(' · ') + (names.length > 2 ? ' +' + (names.length-2) : '');
};
const fmt = (s) => { const [y,m,d] = String(s).split('-').map(Number); return new Date(y,m-1,d); };
const safeLink = (url) => {
  try { const u = new URL(url); return u.protocol === 'https:' ? u.href : null; }
  catch { return null; }
};
const confirmed = (r) => r.confirmada === true;
const publishedDate = (r) => confirmed(r) || r.fecha_origen === 'fuente';
const dateLabel = (r) => confirmed(r) ? 'REVISADA'
  : r.fecha_origen === 'fuente' ? 'FECHA EN FUENTE' : 'FECHA COTEJADA';
const distanceLabel = (r) => r.distancia_origen === 'catalogo'
  ? 'Cotejada' : r.distancia_origen === 'fuente' ? 'En fuente' : 'Revisada';
let races = [];
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
  const date = el('div','race-date');
  const d = fmt(r.fecha);
  date.append(el('strong','',String(d.getDate()).padStart(2,'0')),
              el('span','',months[d.getMonth()].slice(0,3).toUpperCase()));

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
  head.append(el('span',confirmed(r) ? 'tag tag-verified' :
    publishedDate(r) ? 'tag tag-sourced' : 'tag tag-pending',dateLabel(r)));
  if (sourceName(r)) head.append(el('span','tag source-tag',sourceName(r)));
  info.append(head,el('p','race-location','⌖  '+[r.localidad,r.provincia].filter(Boolean).join(' · ')));

  const facts = el('div','race-facts');
  if (r.distancia && r.distancia_origen) facts.append(el('span','','↗  '+r.distancia+' · '+distanceLabel(r)));
  else facts.append(el('span','fact-pending','Distancia no disponible'));
  if (confirmed(r)) {
    if (r.desnivel) facts.append(el('span','','⌁  '+r.desnivel));
    if (r.precio) facts.append(el('span','','◈  '+r.precio));
  }
  info.append(facts);
  if (!confirmed(r) && r.consultado) {
    info.append(el('p','source-meta',
      (r.fecha_origen === 'catalogo' ? 'Cotejada el ' : 'Fuente consultada el ')+r.consultado));
  }

  const actions = el('div','race-actions');
  const sourceUrl = safeLink(confirmed(r) ? r.enlace : (r.fuente || r.enlace));
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
function matches(r, search, province, month, source, sourcedOnly, today) {
  if (!r.fecha || fmt(r.fecha) < today) return false;
  if (sourcedOnly && !publishedDate(r)) return false;
  if (search && !normalize([r.nombre,r.localidad,r.provincia,sourceName(r)].join(' ')).includes(search)) return false;
  if (source && !raceOrigins(r).includes(source)) return false;
  if (province && normalize(r.provincia) !== province) return false;
  if (month && r.fecha.slice(0,7) !== month) return false;
  if (currentMode !== 'TODAS' && (r.modalidad_conflicto || r.modalidad !== currentMode)) return false;
  return true;
}
function render() {
  const search = normalize($('search').value.trim());
  const province = normalize($('province').value);
  const month = $('month').value;
  const source = $('source').value;
  const sourcedOnly = $('confirmed-only').checked;
  const today = new Date();
  today.setHours(0,0,0,0);
  const filtered = races.filter(r => matches(r,search,province,month,source,sourcedOnly,today));
  $('result-count').textContent = String(filtered.length);
  const root = $('cards');
  root.replaceChildren();
  if (!filtered.length) {
    root.append(state(
      races.length ? 'No hay carreras con estos filtros' : 'El calendario está preparado',
      races.length ? 'Prueba otra provincia, modalidad o desactiva el filtro de fuentes actuales.'
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
  for (const id of ['search','province','month','source','confirmed-only']) {
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
    for (const id of ['search','province','month','source']) $(id).value='';
    $('confirmed-only').checked=false;
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
    const usedSources=[...new Set(active.flatMap(r=>raceOrigins(r)).filter(x=>sources[x]))]
      .sort((a,b)=>sourceName({origen:a}).localeCompare(sourceName({origen:b}),'es'));
    for (const origin of usedSources) {
      const option=el('option','',sourceName({origen:origin}));
      option.value=origin;
      $('source').append(option);
    }
    $('updated').textContent=result.actualizado?'Generado el '+result.actualizado:'';
    filter();
  } catch (error) {
    console.error(error);
    $('result-count').textContent='0';
    $('more').hidden=true;
    $('cards').replaceChildren(state('No se pudo cargar el calendario',
      'Comprueba la publicación de los archivos y vuelve a intentarlo.','!'));
  }
}
init();
