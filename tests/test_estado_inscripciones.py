"""Estados temporales de inscripción: evidencia de la misma edición y filtro real."""
from datetime import date
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from estado_inscripciones import (runnink_label,faa_label,gcc_fields,
                                  apply_current_registrations,observation,valid_observation)
from captacion_extra import runnink
from captacion import parse_gcc_detail,parse_faa

TODAY=date(2026,11,18)
DAY=date(2026,12,29)
URL="https://www.runnink.com/evento/carrera-popular-prueba/123"

def row(**extra):
    base=dict(fecha=DAY.isoformat(),nombre="Carrera Popular Prueba",
              localidad="Chipiona",provincia="Cádiz",modalidad="RUNNING",enlace=URL,fuente=URL)
    base.update(extra)
    return base

class InscripcionesTests(unittest.TestCase):
    def test_runnink_labels(self):
        for text,state in [("Inscripciones ›","abierta"),("Inscripciones cerradas ›","cerrada"),
                           ("Dorsales agotados","agotada"),("Próximamente ›","proximamente")]:
            self.assertEqual(runnink_label(text,URL,DAY,TODAY)["inscripcion_estado"],state)
        self.assertEqual(runnink_label("Apertura el 20 de noviembre ›",URL,DAY,TODAY)["inscripcion_apertura"],"2026-11-20")
        self.assertEqual(runnink_label("Apertura el 1 de noviembre",URL,DAY,TODAY),{})
        self.assertEqual(runnink_label("Consulta inscripciones",URL,DAY,TODAY),{})

    def test_runnink_no_cruzar_tarjetas(self):
        page='''<div>Carrera Popular</div>
          <a href="/evento/primera-carrera/123">Carrera Popular Prueba</a>
          <div>📍 Chipiona (Cádiz)</div><div>📅 martes 29 de diciembre de 2026 - 16:30h</div>
          <a href="/evento/primera-carrera/123">Inscripciones cerradas ›</a>
          <div>Carrera Popular</div>
          <a href="/evento/segunda-carrera/124">Otra Carrera Popular</a>
          <div>📍 Rota (Cádiz)</div><div>📅 miércoles 30 de diciembre de 2026 - 16:30h</div>
          <a href="/evento/segunda-carrera/124">Inscripciones ›</a>'''
        result=runnink(page,TODAY)
        self.assertEqual([x["inscripcion_estado"] for x in result],["cerrada","abierta"])

    def test_runnink_no_estado_por_enlace_generico(self):
        page='''<div>Carrera Popular</div>
          <a href="/evento/primera-carrera/123">Carrera Popular Prueba</a>
          <div>📍 Chipiona (Cádiz)</div><div>📅 martes 29 de diciembre de 2026</div>
          <a href="/inscripciones/">Inscripciones ›</a>'''
        result=runnink(page,TODAY)
        self.assertEqual(len(result),1)
        self.assertNotIn("inscripcion_estado",result[0])

    def test_faa_solo_explicito(self):
        self.assertEqual(faa_label("San Silvestre Aguilarense (dorsales agotados)",URL,TODAY)["inscripcion_estado"],"agotada")
        self.assertEqual(faa_label("San Silvestre Aguilarense",URL,TODAY),{})

    def test_gcc_fields(self):
        fields=["Fecha inicio","12-12-2026 09:00","Cierre inscripción","04-12-2026 23:55",
                "Plazas disponibles","84","Inscripción (Individual)"]
        out=gcc_fields(fields,URL,date(2026,12,12),TODAY)
        self.assertEqual(out["inscripcion_estado"],"abierta")
        self.assertEqual(out["inscripcion_limite"],"2026-12-04")
        self.assertEqual(out["inscripcion_hora_limite"],"23:55")
        self.assertNotIn("plazas",out)
        fields[5]="0"
        self.assertEqual(gcc_fields(fields,URL,date(2026,12,12),TODAY)["inscripcion_estado"],"desconocida")
        self.assertEqual(gcc_fields(["Reglamento","Inscripciones abiertas"],URL,DAY,TODAY),{})

    def test_exact_identity_and_no_stale_or_snapshot(self):
        live=row(**observation("abierta",URL,TODAY))
        races=[row(),row(fecha="2027-12-29"),row(nombre="Otra carrera")]
        result=apply_current_registrations(races,[live],TODAY)
        self.assertEqual(result["por_estado"]["abierta"],1)
        self.assertEqual(result["por_estado"]["desconocida"],2)
        self.assertEqual(apply_current_registrations(races,[],TODAY)["por_estado"]["abierta"],0)
        self.assertFalse(valid_observation(live,date(2026,11,20)))
        protected=row(respaldo_temporal=True)
        apply_current_registrations([protected],[live],TODAY)
        self.assertEqual(protected["inscripcion_estado"],"desconocida")

    def test_conflicting_states_and_ambiguous_editions(self):
        a=row(**observation("abierta",URL,TODAY))
        b=row(**observation("agotada",URL,TODAY))
        races=[row()]
        self.assertEqual(apply_current_registrations(races,[a,b],TODAY)["conflictos"],1)
        self.assertEqual(races[0]["inscripcion_estado"],"desconocida")
        races=[row(),row()]
        self.assertEqual(apply_current_registrations(races,[a],TODAY)["por_estado"]["desconocida"],2)

    def test_faa_suffix_can_match_same_identity(self):
        live=row(nombre="Carrera Popular Prueba (dorsales agotados)",**observation("agotada",URL,TODAY))
        races=[row()]
        apply_current_registrations(races,[live],TODAY)
        self.assertEqual(races[0]["inscripcion_estado"],"agotada")

    @unittest.skipUnless(shutil.which("node"),"Node necesario para probar lógica real de filtrado")
    def test_browser_state_deadline_and_expiration(self):
        source=(ROOT/"assets"/"app.js").read_text(encoding="utf-8")
        logic=source[source.index("const registrationLabels ="):source.index("let races = []")]
        script=logic+"""
const row={fecha:'2026-12-12',inscripcion_estado:'abierta',
           inscripcion_fuente:'https://example.org/evento',
           inscripcion_consultada:'2026-11-18',
           inscripcion_limite:'2026-11-18',inscripcion_hora_limite:'20:00'};
function check(r,iso,expected) {
  if(registrationState(r,new Date(iso))!==expected) throw new Error(iso+' '+expected);
}
check(row,'2026-11-18T18:59:00Z','abierta');
check(row,'2026-11-18T19:00:00Z','desconocida');
check({...row,inscripcion_limite:null},'2026-11-20T12:00:00Z','desconocida');
check({...row,inscripcion_limite:null,inscripcion_estado:'agotada'},'2026-11-18T12:00:00Z','agotada');
check({...row,inscripcion_limite:null,respaldo_temporal:true},'2026-11-18T12:00:00Z','desconocida');
"""
        result=subprocess.run(["node","-e",script],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__=="__main__":unittest.main()
