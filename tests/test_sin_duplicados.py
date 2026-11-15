"""Pruebas de regresión para impedir carreras duplicadas en el calendario."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from deduplicacion import combine,verify_unique,same_event,conflicting_date
from captacion_extra import runnink,gesconchip
from datetime import date

def race(name="Trail Sierra Alhaurín el Grande Homenaje a Mori",
         day="2026-12-13",city="Alhaurín el Grande",province="Málaga",
         distance="",mode="TRAIL",origin="faa"):
    return {"nombre":name,"fecha":day,"localidad":city,"provincia":province,
            "distancia":distance,"modalidad":mode,"estado":"Por confirmar",
            "fuente":"https://example.org/evento","origen":origin}

def slug(s):
    import re,unicodedata
    s="".join(c for c in unicodedata.normalize("NFD",s.lower())
              if unicodedata.category(c)!="Mn")
    return re.sub(r"[^a-z0-9]+","-",s).strip("-")[:85]

def km(s):
    import re
    m=re.search(r"(\d+(?:[.,]\d+)?)\s*km",s)
    return float(m.group(1).replace(",",".")) if m else 0

class Deduplicacion(unittest.TestCase):
    def test_nombres_diferentes_de_misma_prueba(self):
        a=race()
        b=race("CxM Alhaurín El Grande Homenaje al Mori",origin="fadmes")
        self.assertTrue(same_event(a,b))
        rows,audit=combine([],[a,b],slug,km,with_audit=True)
        self.assertEqual(len(rows),1)
        self.assertEqual(audit["duplicados_fusionados"],1)
        self.assertEqual(set(rows[0]["fuentes_origen"]),{"faa","fadmes"})

    def test_diferentes_distancias_no_se_eliminan(self):
        a=race("XI Holiday World",city="Benalmádena",distance="5 km",mode="RUNNING")
        b=race("XI Holiday World",city="Benalmádena",distance="21,097 km",mode="RUNNING")
        rows=combine([],[a,b],slug,km)
        self.assertEqual(len(rows),2)
        self.assertNotEqual(rows[0]["slug"],rows[1]["slug"])
        self.assertTrue(verify_unique(rows))

    def test_distinta_prueba_mismo_dia_municipio(self):
        a=race("Trail del Valle",distance="12 km")
        b=race("Cross del Ayuntamiento",distance="12 km")
        rows=combine([],[a,b],slug,km)
        self.assertEqual(len(rows),2)

    def test_aprobada_tiene_prioridad(self):
        approved=race("XXV Trail Sierra Alhaurín el Grande Homenaje a Mori")
        approved.update({"estado":"Confirmada","distancia":"24 km","slug":"aprobada"})
        candidate=race("CxM Alhaurín El Grande Homenaje al Mori",origin="fadmes")
        rows=combine([approved],[candidate],slug,km)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["slug"],"aprobada")
        self.assertEqual(rows[0]["distancia"],"24 km")

    def test_no_se_publican_repetidos_de_sheet(self):
        a=race("Trail del Valle",origin=None)
        a.update({"slug":"ficha-1","estado":"Confirmada"})
        b=dict(a,slug="ficha-2")
        rows=combine([a,b],[],slug,km)
        self.assertEqual(len(rows),1)
        self.assertTrue(verify_unique(rows))

    def test_fechas_contradictorias_requieren_revision(self):
        a=race("Trail del Valle",day="2026-11-22")
        b=race("Trail del Valle",day="2026-11-29",origin="fadmes")
        self.assertTrue(conflicting_date(a,b))
        rows,audit=combine([],[a,b],slug,km,with_audit=True)
        self.assertEqual(len(rows),1)
        self.assertEqual(audit["fechas_en_conflicto"],1)

    def test_auditoria_bloquea_duplicados_residuales(self):
        a=race("Cross de Prueba");a["slug"]="u1"
        b=dict(a,slug="u2")
        with self.assertRaisesRegex(ValueError,"BLOQUEADA"):
            verify_unique([a,b])

    def test_urls_repetidas_bloqueadas(self):
        a=race("Carrera A");a["slug"]="igual"
        b=race("Carrera B");b["slug"]="igual"
        with self.assertRaisesRegex(ValueError,"BLOQUEADA"):
            verify_unique([a,b])

class NuevosLectores(unittest.TestCase):
    def test_runnink_carreras_cadiz(self):
        html='''<div>Próximas carreras</div><section><b>Carrera Popular</b>
        <a href="/evento/xxx-carrera-popular-puerto-menesteo/121">XXX Carrera Popular Puerto Menesteo</a>
        <span>📍 El Puerto de Santa María (Cádiz)</span>
        <span>📅 domingo 22 de noviembre de 2026 - 10:00h</span>
        </section><section><b>Duatlón</b>
        <a href="/evento/duatlon-cross/122">Duatlón Cross Jerez</a>
        <span>📍 Jerez de la Frontera (Cádiz)</span>
        <span>📅 sábado 28 de noviembre de 2026</span></section>'''
        rows=runnink(html,date(2026,11,15))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["provincia"],"Cádiz")
        self.assertEqual(rows[0]["fecha"],"2026-11-22")

    def test_gesconchip_entrada(self):
        html='''<a href="/app/prueba/informacion/ii-carrera-fundacion-jose">
        22 Nov 2026 II CARRERA FUNDACIÓN JOSE LUIS MARTÍN LÓPEZ Jaén - Jaén
        </a><a href="/app/prueba/informacion/xxx-triatlon">
        29 Nov 2026 XXX TRIATLÓN San Roque - Cádiz</a>'''
        rows=gesconchip(html,date(2026,11,15))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["localidad"],"Jaén")
        self.assertEqual(rows[0]["modalidad"],"RUNNING")

if __name__=="__main__":
    unittest.main()
