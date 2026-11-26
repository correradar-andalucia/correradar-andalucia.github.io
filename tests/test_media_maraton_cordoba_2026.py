"""Regresión de la 40.ª Media Maratón de Córdoba 2026 reprogramada."""
from datetime import date
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from oficiales import FILES, official_races, _read_catalog
from deduplicacion import combine, verify_unique
from build import slugify, km_parse

CATALOG=ROOT/"data"/"fichas_oficiales_2026-11-26_media_cordoba.json"

class MediaCordoba2026(unittest.TestCase):
    def test_fuente_primaria_y_fecha_definitiva(self):
        self.assertIn(CATALOG,FILES)
        record=json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(record["revision"],"2026-11-26")
        self.assertIn("29/11/2026",record["criterio"])
        self.assertIn("13/12/2026",record["criterio"])
        entries=_read_catalog(date(2026,11,26),record)
        self.assertEqual(len(entries),1)
        event=entries[0]
        self.assertEqual((event["nombre"],event["fecha"],event["hora"]),
                         ("40 Media Maratón de Córdoba","2026-12-13","10:00"))
        self.assertEqual((event["localidad"],event["provincia"],event["modalidad"],event["distancia"]),
                         ("Córdoba","Córdoba","RUNNING","21,097 km"))
        self.assertEqual(event["fuente"],"https://mediamaratoncordoba.es/")
        self.assertFalse(event.get("confirmada",False))
        self.assertNotIn("inscripcion_estado",event)
        self.assertNotIn("feed_autorizado",event)

    def test_unica_edicion_y_sin_fecha_anterior(self):
        rows=official_races(date(2026,11,26))
        mm=[e for e in rows if e["nombre"]=="40 Media Maratón de Córdoba"]
        self.assertEqual(len(mm),1)
        self.assertEqual(mm[0]["fecha"],"2026-12-13")
        self.assertFalse(any("Media Maratón de Córdoba" in e["nombre"]
                             and e["fecha"]=="2026-11-29" for e in rows))
        result=combine([],rows,slugify,km_parse)
        self.assertTrue(verify_unique(result))
        self.assertEqual(sum(r["nombre"]=="40 Media Maratón de Córdoba" for r in result),1)
        self.assertEqual(sum(r["nombre"]=="40 Media Maratón de Córdoba" for r in
                             official_races(date(2026,12,14))),0)

if __name__=="__main__":
    unittest.main()
