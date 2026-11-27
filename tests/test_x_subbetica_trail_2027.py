"""Cotejo puntual X Subbética Trail, cartel 2027 verificado por el titular."""
from datetime import date
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from oficiales import FILES, official_races, _read_catalog
from deduplicacion import combine, same_event, verify_unique
from build import slugify, km_parse

CATALOG=ROOT/"data"/"fichas_oficiales_2026-11-27_subbetica_trail.json"

class SubbeticaLuque2027(unittest.TestCase):
    def test_cartel_edicion_municipio_fecha_y_procedencia(self):
        self.assertIn(CATALOG,FILES)
        doc=json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(doc["revision"],"2026-11-27")
        self.assertIn("#97",doc["criterio"])
        self.assertIn("cartel",doc["criterio"])
        rows=_read_catalog(date(2026,11,27),doc)
        self.assertEqual(len(rows),1)
        race=rows[0]
        self.assertEqual((race["fecha"],race["nombre"],race["localidad"],
                          race["provincia"],race["modalidad"]),
                         ("2027-03-13","X Subbética Trail","Luque","Córdoba","TRAIL"))
        self.assertEqual((race["distancia"],race["hora"]),("",""))
        self.assertEqual(race["fuente"],
            "https://deportime.es/events/x-subbetica-trail/")
        self.assertEqual(race["tipo_fuente"],"cronometraje")
        self.assertFalse(race.get("confirmada",False))
        self.assertFalse(race.get("feed_autorizado",False))
        self.assertNotIn("inscripcion_estado",race)

    def test_no_deduce_2026_ni_acepta_zuheros_como_localidad_de_2027(self):
        candidates=official_races(date(2026,11,27))
        rows=[r for r in candidates if r["nombre"]=="X Subbética Trail"]
        self.assertEqual(len(rows),1)
        race=rows[0]
        self.assertFalse(same_event(race,{**race,
            "fecha":"2026-03-21","nombre":"IX Subbética Trail",
            "localidad":"Zuheros"}))
        self.assertFalse(same_event(race,{**race,
            "localidad":"Zuheros"}))
        self.assertFalse(any(r["nombre"]=="X Subbética Trail"
                             and r["fecha"]!="2027-03-13" for r in candidates))
        self.assertEqual(len([r for r in candidates if r["localidad"]=="Luque"
                         and r["fecha"]=="2027-03-13"
                         and r["nombre"]=="X Subbética Trail"]),1)
        result=combine([],candidates,slugify,km_parse)
        self.assertTrue(verify_unique(result))
        self.assertEqual(sum(r["nombre"]=="X Subbética Trail" for r in result),1)

    def test_caducidad_no_simula_consulta_actual(self):
        race=next(r for r in official_races(date(2026,12,29))
                  if r["nombre"]=="X Subbética Trail")
        self.assertFalse(race["fuente_directa"])
        self.assertEqual(race["cotejada"],"2026-11-27")
        self.assertIn("reconfirmar",race["estado"].lower())

if __name__=="__main__":
    unittest.main()
