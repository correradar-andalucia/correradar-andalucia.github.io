"""Cotejo editorial por edición, independiente del lector GT pendiente de autorización."""
from datetime import date
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from oficiales import FILES, official_races, _read_catalog
from deduplicacion import same_event

CATALOG = ROOT / "data" / "fichas_oficiales_2026-11-25_guajares.json"

class Guajares2027(unittest.TestCase):
    def test_catalogo_registrado_y_una_sola_edicion(self):
        self.assertIn(CATALOG, FILES)
        doc = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(doc["revision"], "2026-11-25")
        self.assertEqual(len(doc["carreras"]), 1)
        rows = _read_catalog(date(2026,11,25), doc)
        self.assertEqual(len(rows), 1)
        race=rows[0]
        self.assertEqual((race["fecha"],race["nombre"],race["localidad"],
                          race["provincia"],race["modalidad"]),
                         ("2027-02-07","XVI CxM Valle de los Guájares",
                          "Los Guájares","Granada","TRAIL"))
        self.assertEqual(race["distancia"],"24 km · 12 km")
        self.assertEqual(race["hora"],"09:00")
        self.assertEqual(race["fuente"],
                         "https://www.global-tempo.com/carreras.php?id=3329")
        self.assertFalse(race.get("confirmada",False))
        self.assertNotIn("inscripcion_estado",race)
        self.assertFalse(race.get("feed_autorizado",False))
        self.assertIn("10:00",doc["criterio"])
        self.assertIn("reglamento",doc["criterio"].lower())

    def test_sin_confusion_de_ediciones_ni_otra_localidad(self):
        race = _read_catalog(date(2026,11,25),
            json.loads(CATALOG.read_text(encoding="utf-8")))[0]
        self.assertFalse(same_event(race,{**race,"fecha":"2026-09-06"}))
        self.assertFalse(same_event(race,{**race,"localidad":"Granada"}))
        self.assertFalse(same_event(race,{**race,"distancia":"5 km"}))
        existing=official_races(date(2026,11,25))
        same=[r for r in existing if r["fecha"]=="2027-02-07"
              and r["localidad"]=="Los Guájares"]
        self.assertEqual(len(same),1)

if __name__=="__main__":
    unittest.main()
