"""Regresión de la III San Silvestre Cañonera 2026 cotejada por edición."""
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

CATALOG=ROOT/"data"/"fichas_oficiales_2026-11-28_san_silvestre_lanjaron.json"


class SanSilvestreCanonera2026(unittest.TestCase):
    def test_fuente_evento_y_categoria_adulta(self):
        self.assertIn(CATALOG,FILES)
        doc=json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(doc["revision"],"2026-11-28")
        race=_read_catalog(date(2026,11,28),doc)[0]
        self.assertEqual(len(doc["carreras"]),1)
        self.assertEqual((race["nombre"],race["fecha"],race["localidad"],
                         race["provincia"],race["modalidad"]),
                         ("III San Silvestre Cañonera","2026-12-27",
                          "Lanjarón","Granada","RUNNING"))
        self.assertEqual((race["distancia"],race["hora"]),("1,4 km","12:00"))
        self.assertEqual(race["fuente"],
            "https://www.cruzandolameta.es/pruebas/iii-san-silvestre-canonera/")
        self.assertEqual(race["tipo_fuente"],"cronometraje")
        self.assertIn("11:30",doc["criterio"])
        self.assertIn("infantil",doc["criterio"].lower())
        self.assertIn("sin distancia verificable",doc["criterio"])
        self.assertNotIn("inscripcion_estado",race)
        self.assertFalse(race.get("confirmada",False))

    def test_sin_duplicar_ediciones_ni_confundir_lanjaron(self):
        rows=official_races(date(2026,11,28))
        matches=[r for r in rows if r["nombre"]=="III San Silvestre Cañonera"]
        self.assertEqual(len(matches),1)
        race=matches[0]
        self.assertFalse(same_event(race,{**race,"fecha":"2025-12-27",
                                          "nombre":"II San Silvestre Cañonera"}))
        self.assertFalse(same_event(race,{**race,"localidad":"Granada"}))
        self.assertFalse(same_event(race,{**race,"modalidad":"OCR",
                                          "fecha":"2027-05-01"}))
        merged=combine([],rows,slugify,km_parse)
        self.assertTrue(verify_unique(merged))
        self.assertEqual(sum(r["nombre"]=="III San Silvestre Cañonera" 
                             for r in merged),1)

    def test_fecha_de_cotejo_no_renovada_automaticamente(self):
        rows=official_races(date(2027,1,1))
        self.assertFalse(any("III San Silvestre Cañonera"==r["nombre"]
                             for r in rows))

if __name__=="__main__":
    unittest.main()
