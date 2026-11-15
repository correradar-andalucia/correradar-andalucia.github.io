"""Regresiones para el catálogo multifuente de CorreRadar."""
import datetime as dt
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from multifuente import seed_races, combine

class SemillaMultifuente(unittest.TestCase):
    def test_75_registros_de_ocho_fuentes(self):
        rows = seed_races(dt.date(2026, 11, 15))
        self.assertEqual(len(rows), 75)
        self.assertEqual(len({r["origen"] for r in rows}), 8)

    def test_73_eventos_unicos(self):
        rows = seed_races(dt.date(2026, 11, 15))
        result = combine([], rows, lambda x:x.lower().replace(" ","-"), lambda x:0)
        self.assertEqual(len(result), 73)
        self.assertEqual(len({r["provincia"] for r in result}), 8)

    def test_caducidad(self):
        self.assertEqual(seed_races(dt.date(2026, 12, 16)), [])

    def test_prioridad_aprobadas(self):
        candidates = seed_races(dt.date(2026, 11, 15))
        one = candidates[0]
        approved = [dict(one, estado="Publicada", slug="original", distancia="42 km")]
        result = combine(approved, candidates, lambda x:x.lower().replace(" ","-"), lambda x:0)
        found = [r for r in result if r["fecha"] == one["fecha"] and r["nombre"] == one["nombre"]]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["distancia"], "42 km")

if __name__ == "__main__":
    unittest.main()
